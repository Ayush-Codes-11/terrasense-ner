#!/usr/bin/env python3
"""
fetch_smap_soil.py - Phase 1C: NASA SMAP L4 Soil Moisture ingestion script.
Discovers the newest authoritative CMR granule for SPL4SMGP V8, downloads it securely,
projects EPSG:4326 centroids to EPSG:6933, maps zones using nearest neighbor on actual
SMAP cell lat/lon, and writes transaction-safe canonical JSON.
"""

import os
import sys
import json
import tempfile
import re
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
import requests
import math

try:
    import earthaccess
    import h5py
    import numpy as np
except ImportError:
    print("[ERROR] Missing required packages. Ensure earthaccess, h5py, and numpy are installed.")
    sys.exit(1)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_GEOJSON_PATH = _REPO_ROOT / "backend" / "data" / "sample" / "grid-risk.geojson"
_CANONICAL_JSON = _REPO_ROOT / "data" / "real" / "weather" / "smap_soil_moisture.json"
_BACKEND_JSON = _REPO_ROOT / "backend" / "data" / "real" / "weather" / "smap_soil_moisture.json"

def main():
    token = os.environ.get("EARTHDATA_TOKEN", "").strip()
    if not token:
        print("[ERROR] EARTHDATA_TOKEN environment variable not set. Missing secure auth token.")
        sys.exit(1)

    print("Authenticating with earthaccess (environment strategy)...")
    try:
        auth = earthaccess.login(strategy="environment", persist=False)
        if not auth.authenticated:
            print("[ERROR] earthaccess login failed.")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] earthaccess login exception: {e}")
        sys.exit(1)

    now_utc = datetime.now(timezone.utc)
    start_utc = now_utc - timedelta(days=10)
    temporal_str = f"{start_utc.strftime('%Y-%m-%dT%H:%M:%SZ')},{now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}"

    print("Querying CMR JSON API directly with newest-first sorting...")
    cmr_url = "https://cmr.earthdata.nasa.gov/search/granules.json"
    params = {
        "concept_id": "C3480440870-NSIDC_CPRD",
        "sort_key": "-start_date",
        "page_size": 10,
        "temporal": temporal_str
    }

    resp = requests.get(cmr_url, params=params)
    if resp.status_code != 200:
        print(f"[ERROR] CMR query failed: {resp.status_code} {resp.text}")
        sys.exit(1)

    data = resp.json()
    entries = data.get("feed", {}).get("entry", [])

    if not entries:
        # Progressively widen the window
        print("No granules found in 10 days. Trying 30 days...")
        start_utc = now_utc - timedelta(days=30)
        params["temporal"] = f"{start_utc.strftime('%Y-%m-%dT%H:%M:%SZ')},{now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        resp = requests.get(cmr_url, params=params)
        data = resp.json()
        entries = data.get("feed", {}).get("entry", [])

        if not entries:
            print("[ERROR] No granules found even after widening window.")
            sys.exit(1)

    latest = entries[0]
    cmr_start = latest.get("time_start")
    cmr_end = latest.get("time_end")
    granule_concept_id = latest.get("id")
    links = latest.get("links", [])
    https_link = next((l["href"] for l in links if l.get("href", "").startswith("https://") and l.get("href", "").endswith(".h5")), None)

    if not https_link:
        print("[ERROR] No HTTPS link found for the newest granule.")
        sys.exit(1)

    filename = https_link.split("/")[-1]

    match = re.search(r"SMAP_L4_SM_gph_(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})_", filename)
    if match:
        file_ts_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}T{match.group(4)}:{match.group(5)}:{match.group(6)}Z"
    else:
        file_ts_str = cmr_start

    representative_time_utc = file_ts_str
    rep_dt = datetime.fromisoformat(representative_time_utc.replace("Z", "+00:00"))
    if rep_dt < start_utc:
        print("[ERROR] Granule representative time falls outside recent window. FAILING CLOSED.")
        sys.exit(1)

    age_hours = (now_utc - rep_dt).total_seconds() / 3600.0

    print(f"Downloading selected granule: {filename}")
    session = earthaccess.get_requests_https_session()
    dl_resp = session.get(https_link, stream=True, allow_redirects=True)

    if dl_resp.status_code != 200 or 'text/html' in dl_resp.headers.get('Content-Type', ''):
        print(f"[ERROR] Download failed. Status: {dl_resp.status_code}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "temp_granule.h5"
        with open(tmp_path, "wb") as f:
            for chunk in dl_resp.iter_content(chunk_size=8192):
                f.write(chunk)

        print("Validating downloaded HDF5 structure...")
        with h5py.File(tmp_path, "r") as h5:
            if "Geophysical_Data" not in h5:
                print("[ERROR] Missing /Geophysical_Data")
                sys.exit(1)
            geo = h5["Geophysical_Data"]
            if "sm_rootzone_wetness" not in geo:
                print("[ERROR] Missing sm_rootzone_wetness")
                sys.exit(1)

            v = geo["sm_rootzone_wetness"]
            if v.shape != (1624, 3856):
                print(f"[ERROR] Unexpected shape {v.shape}. Expected (1624, 3856)")
                sys.exit(1)

            units = v.attrs.get("units", b"").decode("utf-8")
            if units != "dimensionless":
                print(f"[ERROR] Unexpected units {units}. Expected dimensionless")
                sys.exit(1)

            fill_val = float(v.attrs.get("_FillValue", -9999.0))
            valid_min = float(v.attrs.get("valid_min", 0.0))
            valid_max = float(v.attrs.get("valid_max", 1.0))

            wetness_data = v[:]
            lat_data = h5["cell_lat"][:]
            lon_data = h5["cell_lon"][:]
            row_data = h5["cell_row"][:]
            col_data = h5["cell_column"][:]
            x_data = h5["x"][:]
            y_data = h5["y"][:]

            print("Mapping zones to nearest SMAP cells using EPSG:6933...")
            import pyproj
            transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)

            with open(_GEOJSON_PATH, encoding="utf-8") as gf:
                geojson_data = json.load(gf)

            mapped_cells = {}
            zone_outputs = {}

            for f in geojson_data.get("features", []):
                zid = f.get("properties", {}).get("zone_id")
                coords = f["geometry"]["coordinates"][0]
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                c_lon = sum(lons) / len(lons)
                c_lat = sum(lats) / len(lats)

                # Transform WGS84 centroid to EPSG:6933 (EASE-Grid 2.0 Global)
                cx, cy = transformer.transform(c_lon, c_lat)

                # Nearest neighbor on 1D x/y axes
                c = int(np.argmin(np.abs(x_data - cx)))
                r = int(np.argmin(np.abs(y_data - cy)))

                # Extract cross-check arrays
                actual_row = int(row_data[r, c] if getattr(row_data, 'ndim', 2) == 2 else row_data[r])
                actual_col = int(col_data[r, c] if getattr(col_data, 'ndim', 2) == 2 else col_data[c])
                cell_id = f"ROW_{actual_row}_COL_{actual_col}"

                wetness_val = float(wetness_data[r, c] if getattr(wetness_data, 'ndim', 2) == 2 else wetness_data[r])

                if wetness_val == fill_val or math.isnan(wetness_val) or math.isinf(wetness_val) or wetness_val < valid_min or wetness_val > valid_max:
                    is_valid = False
                else:
                    is_valid = True

                if cell_id not in mapped_cells:
                    mapped_cells[cell_id] = {
                        "cell_id": cell_id,
                        "row": actual_row,
                        "column": actual_col,
                        "center_lat": float(lat_data[r, c] if getattr(lat_data, 'ndim', 2) == 2 else lat_data[r]),
                        "center_lon": float(lon_data[r, c] if getattr(lon_data, 'ndim', 2) == 2 else lon_data[c]),
                        "sm_rootzone_wetness": wetness_val,
                        "valid": is_valid
                    }

                zone_outputs[zid] = {
                    "zone_id": zid,
                    "native_cell_id": cell_id,
                    "soil_wetness": wetness_val,
                    "provenance": "REAL_SOIL_MOISTURE" if is_valid else "INVALID"
                }

    canonical_data = {
        "metadata": {
            "data_type": "REAL_SOIL_MOISTURE",
            "source_data_origin": "NASA_NSIDC_SMAP",
            "provider": "NASA",
            "daac": "NSIDC_DAAC",
            "dataset": "SPL4SMGP",
            "version": "8",
            "collection_concept_id": "C3480440870-NSIDC_CPRD",
            "granule_concept_id": granule_concept_id,
            "source_filename": filename,
            "variable": "sm_rootzone_wetness",
            "depth_cm": "0-100",
            "units": "dimensionless",
            "spatial_resolution": "~9 km",
            "grid": "EASE_GRID_2_0",
            "crs": "EPSG:6933",
            "temporal_resolution": "3-hourly",
            "temporal_semantics": "3-hour time average",
            "product_nature": "DATA_ASSIMILATION",
            "product_start_utc": cmr_start,
            "product_end_utc": cmr_end,
            "representative_time_utc": representative_time_utc,
            "retrieved_at_utc": now_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "product_age_hours": age_hours,
            "source_availability_status": "LATEST_AVAILABLE_AT_RETRIEVAL",
            "is_real": True,
            "is_live": False
        },
        "native_cells": mapped_cells,
        "zones": zone_outputs
    }

    os.makedirs(_CANONICAL_JSON.parent, exist_ok=True)
    os.makedirs(_BACKEND_JSON.parent, exist_ok=True)

    tmp_path = _CANONICAL_JSON.with_suffix(".json.tmp")
    bak_path = _CANONICAL_JSON.with_suffix(".json.bak")

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(canonical_data, f, indent=2)

    try:
        with open(tmp_path, encoding="utf-8") as f:
            json.load(f)
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        print(f"[ERROR] JSON validation failed on temporary outputs: {e}")
        sys.exit(1)

    if _CANONICAL_JSON.exists():
        shutil.copy2(_CANONICAL_JSON, bak_path)

    try:
        os.replace(tmp_path, _CANONICAL_JSON)
    except Exception as e:
        print(f"[ERROR] Replacement failed: {e}. Restoring backups.")
        if bak_path.exists():
            os.replace(bak_path, _CANONICAL_JSON)
        sys.exit(1)

    if bak_path.exists():
        bak_path.unlink()

    shutil.copy2(_CANONICAL_JSON, _BACKEND_JSON)

    print(f"Successfully processed {len(mapped_cells)} native cells for {len(zone_outputs)} zones.")
    print(f"Canonical data updated: {_CANONICAL_JSON}")

if __name__ == "__main__":
    main()
