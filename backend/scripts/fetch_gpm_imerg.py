"""
fetch_gpm_imerg.py — NASA GPM IMERG real precipitation acquisition and zonal mapping.

Fetches the 3 latest completed daily precipitation granules (D-2, D-1, D0)
from NASA GES DISC for GPM_3IMERGDL, extracts the 0.1° native cells
covering the Aizawl pilot district, computes area-weighted zonal precipitation
using the actual zone geometries, and saves canonical files atomically.

Scientific & Provenance Guardrails:
1. GPM IMERG is an OBSERVED recent precipitation estimate, NOT a weather forecast.
2. Native resolution is ~0.1° (~10 km). Multiple zones legitimately share coarse cells.
3. No artificial 30m interpolation is performed.
4. Source variable is `precipitation` in `mm/day` over 1 complete UTC day.
5. All requests use official NASA CMR and GES DISC OPeNDAP/HTTPS APIs.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import tempfile
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from shapely.geometry import box, shape
import numpy as np

try:
    import netCDF4
except ImportError:
    pass  # We catch this later if the offline fixture is not used

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DATA_DIR = _REPO_ROOT / "data" if (_REPO_ROOT / "data").exists() else _BACKEND_DIR / "data"
_WEATHER_OUT_DIR = _DATA_DIR / "real" / "weather"
_GRID_RISK_PATH = _DATA_DIR / "sample" / "grid-risk.geojson"

# Try loading .env if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
    load_dotenv(Path.home() / ".env")
except ImportError:
    pass


CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
COLLECTION_SHORTNAME = "GPM_3IMERGDL"
COLLECTION_CONCEPT_ID = "C2723754859-GES_DISC"
COLLECTION_VERSION = "07"
ALGORITHM_GENERATION = "V07"

PILOT_BBOX = (92.6801, 23.6896, 92.7551, 23.7646)  # (min_lon, min_lat, max_lon, max_lat)


def _build_auth_headers(token: str) -> dict:
    """Returns Authorization headers. Token is never printed or stored."""
    return {
        "Authorization": f"Bearer {token}",
        "User-Agent": "TerraSense-NER-Client/1.0",
    }


def _select_three_consecutive_granules(page_size: int = 7) -> List[Dict[str, Any]]:
    """
    Queries recent CMR granules, validates completeness, and returns the newest
    trio of consecutive complete UTC daily granules. Returns oldest to newest (D-2, D-1, D0).
    """
    url = f"{CMR_GRANULES_URL}?concept_id={COLLECTION_CONCEPT_ID}&sort_key=-start_date&page_size={page_size}"
    req = urllib.request.Request(url, headers={"User-Agent": "TerraSense-NER-Client/1.0"})

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    entries = data.get("feed", {}).get("entry", [])

    valid_candidates = []
    for e in entries:
        title = e.get("title", "UNKNOWN")

        col_id = e.get("collection_concept_id", "")
        if col_id != COLLECTION_CONCEPT_ID:
            continue

        t_start = e.get("time_start")
        t_end = e.get("time_end")
        if not t_start or not t_end:
            continue

        try:
            dt_start = datetime.fromisoformat(t_start.replace("Z", "+00:00"))
            dt_end = datetime.fromisoformat(t_end.replace("Z", "+00:00"))
            duration_s = (dt_end - dt_start).total_seconds()
        except ValueError:
            continue

        if abs(duration_s - 86400) > 60:
            continue

        if not (dt_start.hour == 0 and dt_start.minute <= 5):
            continue
        if not (dt_end.hour == 23 and dt_end.minute >= 54):
            continue

        has_nc4 = any(
            l.get("href", "").startswith("https://") and l.get("href", "").endswith(".nc4")
            for l in e.get("links", [])
        )
        if not has_nc4:
            continue

        valid_candidates.append({
            "entry": e,
            "dt_start": dt_start,
            "dt_end": dt_end,
            "title": title
        })

    valid_candidates.sort(key=lambda x: x["dt_start"], reverse=True) # Newest first

    for i in range(len(valid_candidates) - 2):
        c0, c1, c2 = valid_candidates[i], valid_candidates[i+1], valid_candidates[i+2]

        d0_date = c0["dt_start"].date()
        d1_date = c1["dt_start"].date()
        d2_date = c2["dt_start"].date()

        if (d0_date - d1_date).days == 1 and (d1_date - d2_date).days == 1:
            return [c2["entry"], c1["entry"], c0["entry"]]

    print("[ERROR] Could not find 3 consecutive valid GPM_3IMERGDL granules.")
    print("Candidate summary:")
    for vc in valid_candidates:
        print(f"  {vc['title']} - OK")
    print("Suggestion: Wait for Late Run processing to complete, then retry.")
    sys.exit(1)


def _download_and_extract_granule(
    entry: dict,
    native_cells: dict,
    headers: dict,
    tmp_dir: Path,
    label: str
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Downloads granule and extracts precipitation and valid count using netCDF4.
    """
    https_url = next(
        (l["href"] for l in entry.get("links", [])
         if l.get("href", "").startswith("https://") and l.get("href", "").endswith(".nc4")),
        None
    )
    if not https_url:
        raise RuntimeError(f"[{label}] No HTTPS .nc4 link found.")

    filename = https_url.split("/")[-1]
    dest = tmp_dir / filename

    print(f"  [{label}] Downloading {filename}...")
    req = urllib.request.Request(https_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            dest.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError(f"[{label}] GES DISC returned 401. Token absent, expired, or GES DISC not authorized in Earthdata profile.")
        raise RuntimeError(f"[{label}] HTTP {e.code}: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"[{label}] Download failed: {e}")

    title = entry.get("title", "")
    if ".V" not in title:
        raise RuntimeError(f"[{label}] Cannot determine processing version from title '{title}'.")
    gpv = f"V{title.split('.V')[-1].replace('.nc4', '')}"

    granule_meta = {
        "window_start_utc": entry.get("time_start", "").replace(".000Z", "Z"),
        "window_end_utc": entry.get("time_end", "").replace(".999Z", "Z"),
        "granule_title": title,
        "granule_url": https_url,
        "granule_processing_version": gpv,
        "cell_quality": {}
    }

    cell_values = {}

    with netCDF4.Dataset(dest, "r") as ds:
        required_vars = {"lat", "lon", "precipitation"}
        if required_vars.issubset(ds.variables.keys()):
            container = ds
            container_name = "root"
        elif "Grid" in ds.groups and required_vars.issubset(ds.groups["Grid"].variables.keys()):
            container = ds.groups["Grid"]
            container_name = "Grid"
        else:
            raise RuntimeError(
                f"[{label}] Unexpected GPM NetCDF structure. "
                f"root variables={list(ds.variables.keys())}, "
                f"groups={list(ds.groups.keys())}"
            )

        print(f"  [{label}] Detected container: {container_name}")
        print(f"  [{label}] Root groups: {list(ds.groups.keys())}")
        print(f"  [{label}] Container variables: {list(container.variables.keys())}")

        lats = container["lat"][:]
        lons = container["lon"][:]
        precip_var = container["precipitation"]

        print(f"  [{label}] lat shape: {lats.shape}, lon shape: {lons.shape}")
        print(f"  [{label}] precipitation shape: {precip_var.shape}")
        print(f"  [{label}] precipitation dimensions: {precip_var.dimensions}")

        units = getattr(precip_var, 'units', 'unknown')
        print(f"  [{label}] precipitation units: {units}")
        if 'mm' not in units.lower() or 'day' not in units.lower():
            raise RuntimeError(f"[{label}] Incompatible precipitation units: {units}. Expected mm/day.")

        fill_value = float(getattr(precip_var, "_FillValue", -9999.9))
        print(f"  [{label}] precipitation _FillValue: {fill_value}")

        dims = precip_var.dimensions
        if "lat" not in dims or "lon" not in dims:
            raise RuntimeError(f"[{label}] precipitation missing lat or lon dimension.")

        t_ax = dims.index("time") if "time" in dims else None
        if t_ax is not None and precip_var.shape[t_ax] != 1:
            raise RuntimeError(f"[{label}] Expected daily file to have time dimension of 1.")

        lat_ax, lon_ax = dims.index("lat"), dims.index("lon")

        has_cnt = "precipitation_cnt" in container.variables
        print(f"  [{label}] precipitation_cnt exists: {has_cnt}")
        if not has_cnt:
            raise RuntimeError(f"[{label}] Required variable 'precipitation_cnt' is missing from NetCDF.")

        cnt_var = container["precipitation_cnt"]
        cnt_fill = int(getattr(cnt_var, "_FillValue", -9999))
        cnt_dims = cnt_var.dimensions
        print(f"  [{label}] precipitation_cnt dimensions: {cnt_dims}")
        cnt_t_ax = cnt_dims.index("time") if "time" in cnt_dims else None
        cnt_lat_ax = cnt_dims.index("lat")
        cnt_lon_ax = cnt_dims.index("lon")

        for cid, cinfo in native_cells.items():
            target_lat = cinfo["lat_center"]
            target_lon = cinfo["lon_center"]

            i_lat = int(np.argmin(np.abs(lats - target_lat)))
            i_lon = int(np.argmin(np.abs(lons - target_lon)))

            actual_lat, actual_lon = float(lats[i_lat]), float(lons[i_lon])
            if abs(actual_lat - target_lat) > 0.06 or abs(actual_lon - target_lon) > 0.06:
                raise RuntimeError(
                    f"[{label}] Coordinate mismatch for {cid}: "
                    f"expected ({target_lat}, {target_lon}), nearest ({actual_lat:.4f}, {actual_lon:.4f})"
                )

            idx = [slice(None)] * len(dims)
            if t_ax is not None:
                idx[t_ax] = 0
            idx[lat_ax] = i_lat
            idx[lon_ax] = i_lon

            raw_element = precip_var[tuple(idx)]

            # Mask check
            if np.ma.is_masked(raw_element):
                raise RuntimeError(f"[{label}] Cell {cid}: masked/missing data.")

            raw_val = float(raw_element)

            # Numeric Fill Check
            if not math.isfinite(raw_val) or np.isclose(raw_val, fill_value, rtol=0, atol=abs(fill_value)*0.01):
                raise RuntimeError(f"[{label}] Cell {cid}: precipitation equals fill value.")

            if raw_val < 0.0:
                raise RuntimeError(f"[{label}] Cell {cid}: negative precipitation {raw_val:.4f}.")
            if raw_val > 1500.0:
                raise RuntimeError(f"[{label}] Cell {cid}: physically implausible {raw_val:.2f}.")

            cell_values[cid] = round(raw_val, 2)

            # Count Check
            cnt_idx = [slice(None)] * len(cnt_dims)
            if cnt_t_ax is not None:
                cnt_idx[cnt_t_ax] = 0
            cnt_idx[cnt_lat_ax] = i_lat
            cnt_idx[cnt_lon_ax] = i_lon

            cnt_raw = cnt_var[tuple(cnt_idx)]
            cnt_masked = np.ma.is_masked(cnt_raw)
            cnt_int = None if cnt_masked else int(cnt_raw)

            if cnt_masked or cnt_int == cnt_fill or cnt_int is None:
                raise RuntimeError(f"[{label}] Cell {cid}: precipitation_cnt is fill/missing.")
            if not (1 <= cnt_int <= 48):
                raise RuntimeError(f"[{label}] Cell {cid}: precipitation_cnt ({cnt_int}) is outside valid range [1, 48].")

            granule_meta["cell_quality"][cid] = {
                "precipitation_cnt": cnt_int,
                "quality_fraction": round(cnt_int / 48.0, 4),
                "cnt_valid": True
            }

    return cell_values, granule_meta


def get_native_cell_box(lat_center: float, lon_center: float, res_deg: float = 0.1) -> box:
    """Returns shapely Box polygon for a 0.1 deg IMERG cell centered at (lat_center, lon_center)."""
    half = res_deg / 2.0
    return box(
        lon_center - half,
        lat_center - half,
        lon_center + half,
        lat_center + half,
    )


def derive_intersecting_imerg_cells(
    pilot_bbox: Tuple[float, float, float, float],
    res_deg: float = 0.1
) -> Dict[str, Dict[str, Any]]:
    """Programmatically derives all 0.1 deg IMERG cells intersecting the pilot bbox."""
    min_lon, min_lat, max_lon, max_lat = pilot_bbox
    i_min = math.floor((min_lat + 89.95) / res_deg)
    i_max = math.ceil((max_lat + 89.95) / res_deg)
    j_min = math.floor((min_lon + 179.95) / res_deg)
    j_max = math.ceil((max_lon + 179.95) / res_deg)

    cells = {}
    for i in range(i_min, i_max + 1):
        lat_c = round(-89.95 + i * res_deg, 4)
        for j in range(j_min, j_max + 1):
            lon_c = round(-179.95 + j * res_deg, 4)
            poly = get_native_cell_box(lat_c, lon_c, res_deg)
            if poly.intersects(box(*pilot_bbox)):
                cell_id = f"CELL_LAT{lat_c:.2f}_LON{lon_c:.2f}"
                cells[cell_id] = {
                    "cell_id": cell_id,
                    "lat_center": lat_c,
                    "lon_center": lon_c,
                    "poly": poly,
                    "lat_index": i,
                    "lon_index": j,
                }
    return cells


def compute_zone_overlap_weights(
    grid_geojson_path: Path,
    native_cells: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, float]]:
    """Computes exact area-weighted overlap fractions for each zone using actual geometry."""
    with open(grid_geojson_path, encoding="utf-8") as f:
        fc = json.load(f)

    zone_weights: Dict[str, Dict[str, float]] = {}
    for feat in fc["features"]:
        zid = feat["properties"]["zone_id"]
        geom = shape(feat["geometry"])
        total_area = geom.area
        weights = {}
        for cid, cinfo in native_cells.items():
            inter = geom.intersection(cinfo["poly"])
            if not inter.is_empty:
                w = inter.area / total_area
                if w > 0.0001:
                    weights[cid] = round(w, 4)
        sum_w = sum(weights.values())
        if sum_w > 0:
            weights = {k: round(v / sum_w, 4) for k, v in weights.items()}
        zone_weights[zid] = weights

    return zone_weights


def process_granule_data(
    granules_data: List[Dict[str, Any]],
    zone_weights: Dict[str, Dict[str, float]],
    native_cells: Dict[str, Dict[str, Any]],
    meta_extra: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Combines 3 consecutive granules (D-2, D-1, D0) with area-weighted zone overlaps.
    Returns (gpm_observed_dataset, metadata_dataset).
    """
    day_keys = ["d_minus_2", "d_minus_1", "d0"]
    if len(granules_data) < 3:
        raise ValueError(f"Need 3 consecutive granules, got {len(granules_data)}")

    source_origin = meta_extra.get("source_data_origin")
    if source_origin not in ("NASA_GES_DISC", "OFFLINE_TEST_FIXTURE"):
        raise ValueError(f"source_data_origin must be explicitly 'NASA_GES_DISC' or 'OFFLINE_TEST_FIXTURE', got: {source_origin}")

    gpv_global = meta_extra.get("granule_processing_version")
    if not gpv_global:
        raise ValueError("granule_processing_version must be explicitly provided in meta_extra.")

    sorted_granules = sorted(granules_data, key=lambda g: g["window_start_utc"])

    granules_by_day = {
        day_keys[i]: sorted_granules[i] for i in range(3)
    }

    cell_values: Dict[str, Dict[str, float]] = {}
    for d_key, gran in granules_by_day.items():
        for c in gran["cells"]:
            cid = f"CELL_LAT{float(c['lat_center']):.2f}_LON{float(c['lon_center']):.2f}"
            if cid not in cell_values:
                cell_values[cid] = {}
            val = float(c["precipitation_mm_day"])
            if not math.isfinite(val) or val < 0.0:
                raise ValueError(f"Invalid precipitation {val} in cell {cid} for day {d_key}")
            cell_values[cid][d_key] = round(val, 2)

    zones_output: Dict[str, Any] = {}
    for zid, weights in zone_weights.items():
        obs_buckets: Dict[str, float] = {}
        for d_key in day_keys:
            bucket_val = sum(
                cell_values[cid][d_key] * w
                for cid, w in weights.items()
                if cid in cell_values and d_key in cell_values[cid]
            )
            obs_buckets[d_key] = round(bucket_val, 2)

        d0_val = obs_buckets["d0"]
        d1_val = obs_buckets["d_minus_1"]
        d2_val = obs_buckets["d_minus_2"]
        antecedent_3d = round(d2_val + d1_val + d0_val, 2)

        dominant_cell = max(weights.items(), key=lambda x: x[1])[0]

        zones_output[zid] = {
            "zone_id": zid,
            "data_type": "REAL_GPM" if source_origin == "NASA_GES_DISC" else "SAMPLE_GPM_COMPATIBLE",
            "is_live": False,
            "observed_daily_mm": {
                "d_minus_2": d2_val,
                "d_minus_1": d1_val,
                "d0": d0_val,
            },
            "recent_24h_mm": d0_val,
            "antecedent_3d_mm": antecedent_3d,
            "observed_buckets": {
                dk: {
                    "window_start_utc": granules_by_day[dk]["window_start_utc"],
                    "window_end_utc": granules_by_day[dk]["window_end_utc"],
                    "precipitation_mm": obs_buckets[dk],
                    "source_variable": "precipitation",
                    "source_unit": "mm/day",
                    "observation_duration": "1 complete UTC day",
                    "granule_title": granules_by_day[dk].get("granule_title"),
                    "granule_url": granules_by_day[dk].get("granule_url"),
                    "granule_processing_version": granules_by_day[dk].get("granule_processing_version"),
                    "cell_quality": granules_by_day[dk].get("cell_quality", {}),
                } for dk in day_keys
            },
            "native_cell_weights": weights,
            "dominant_native_cell": dominant_cell,
        }

    latest_granule = granules_by_day["d0"]
    retrieval_utc = datetime.now(timezone.utc).isoformat()

    metadata: Dict[str, Any] = {
        "collection": COLLECTION_SHORTNAME,
        "collection_version": COLLECTION_VERSION,
        "algorithm_generation": ALGORITHM_GENERATION,
        "granule_processing_version": gpv_global,
        "collection_concept_id": COLLECTION_CONCEPT_ID,
        "source_data_origin": source_origin,
        "source": "NASA Global Precipitation Measurement (GPM) IMERG Late Run",
        "product": f"NASA GPM IMERG Late Precipitation L3 1 day 0.1° V{COLLECTION_VERSION} ({COLLECTION_SHORTNAME})",
        "source_variable": "precipitation",
        "source_unit": "mm/day",
        "observation_duration": "1 complete UTC day per bucket",
        "native_spatial_resolution_deg": 0.1,
        "temporal_resolution": "1 day (daily accumulation)",
        "reference_timestamp_utc": latest_granule["window_end_utc"],
        "retrieved_at_utc": retrieval_utc,
        "pilot_district": "Aizawl District, Mizoram, India",
        "total_zones": len(zones_output),
        "unique_native_cells_count": len(native_cells),
        "native_cells": {
            cid: {"lat_center": c["lat_center"], "lon_center": c["lon_center"]}
            for cid, c in native_cells.items()
        },
        "days": {
            "d_minus_2": granules_by_day["d_minus_2"]["window_start_utc"][:10],
            "d_minus_1": granules_by_day["d_minus_1"]["window_start_utc"][:10],
            "d0": granules_by_day["d0"]["window_start_utc"][:10],
        },
        "is_live": False,
        "attribution": (
            "NASA Global Precipitation Measurement (GPM) Integrated Multi-satellitE "
            "Retrievals for GPM (IMERG), archived and distributed by NASA GES DISC."
        ),
        "notes": (
            "GPM IMERG estimates are satellite-derived precipitation measurements at ~0.1 deg (~10 km) native grid. "
            "Values represent recent observed precipitation triggers; future rainfall windows remain scenario-based."
        ),
    }

    return {"metadata": metadata, "zones": zones_output}, metadata


def _recover_interrupted_run(out_gpm: Path, out_meta: Path):
    """Restores files from backups if a previous run was interrupted."""
    bak_gpm = out_gpm.with_suffix(".json.bak")
    bak_meta = out_meta.with_suffix(".json.bak")

    if bak_gpm.exists() or bak_meta.exists():
        print("[RECOVERY] Found backup files from a previous interrupted run.")
        needs_restore = False
        if not out_gpm.exists() or not out_meta.exists():
            needs_restore = True
        else:
            try:
                with open(out_gpm, encoding="utf-8") as f: dg = json.load(f)
                with open(out_meta, encoding="utf-8") as f: dm = json.load(f)

                embedded_meta = dg.get("metadata")
                if embedded_meta is None or embedded_meta != dm:
                    needs_restore = True
            except Exception:
                needs_restore = True

        if needs_restore:
            print("  -> Canonical files missing or inconsistent. Restoring from backups.")
            if bak_gpm.exists():
                os.replace(bak_gpm, out_gpm)
            if bak_meta.exists():
                os.replace(bak_meta, out_meta)
        else:
            print("  -> Canonical files are consistent. Removing stale backups.")
            if bak_gpm.exists(): bak_gpm.unlink()
            if bak_meta.exists(): bak_meta.unlink()


def main():
    parser = argparse.ArgumentParser(description="Fetch and process NASA GPM IMERG precipitation.")
    parser.add_argument("--offline-fixture", type=Path, help="Path to offline JSON test fixture")
    args = parser.parse_args()

    print("TerraSense NER — NASA GPM IMERG Precipitation Pipeline")
    print(f"Pilot BBox: {PILOT_BBOX}")

    native_cells = derive_intersecting_imerg_cells(PILOT_BBOX, res_deg=0.1)
    zone_weights = compute_zone_overlap_weights(_GRID_RISK_PATH, native_cells)

    _WEATHER_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_gpm = _WEATHER_OUT_DIR / "gpm_imerg_observed.json"
    out_meta = _WEATHER_OUT_DIR / "metadata.json"

    # Startup recovery check
    _recover_interrupted_run(out_gpm, out_meta)

    if args.offline_fixture:
        print(f"Loading offline fixture: {args.offline_fixture}...")
        with open(args.offline_fixture, encoding="utf-8") as f:
            fixture_data = json.load(f)
        granules = fixture_data["granules"]

        # Exact offline fixture provenance handling
        meta_extra = {
            "granule_processing_version": fixture_data.get("metadata", {}).get("granule_processing_version", "OFFLINE_FIXTURE_V07C"),
            "source_data_origin": "OFFLINE_TEST_FIXTURE"
        }
        gpm_dataset, metadata = process_granule_data(granules, zone_weights, native_cells, meta_extra)

        with open(out_gpm, "w", encoding="utf-8") as f:
            json.dump(gpm_dataset, f, indent=2)
        with open(out_meta, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        print("Fixture loaded and canonical files written.")
        sys.exit(0)

    # LIVE FETCH PATH
    token = os.environ.get("EARTHDATA_TOKEN", "").strip()
    if not token:
        print("[ERROR] EARTHDATA_TOKEN not set. Cannot fetch real NASA GPM data.")
        sys.exit(1)

    if "netCDF4" not in sys.modules:
        print("[ERROR] netCDF4 module is required for live fetch.")
        sys.exit(1)

    headers = _build_auth_headers(token)
    del token

    print("Querying CMR for latest granules...")
    trio_entries = _select_three_consecutive_granules(page_size=7)

    day_keys = ["d_minus_2", "d_minus_1", "d0"]
    granules_data = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for dk, entry in zip(day_keys, trio_entries):
            cell_vals, gran_meta = _download_and_extract_granule(
                entry, native_cells, headers, tmp_dir, dk
            )
            granules_data.append({
                "window_start_utc": gran_meta["window_start_utc"],
                "window_end_utc": gran_meta["window_end_utc"],
                "cells": [
                    {
                        "lat_center": native_cells[cid]["lat_center"],
                        "lon_center": native_cells[cid]["lon_center"],
                        "precipitation_mm_day": v
                    } for cid, v in cell_vals.items()
                ],
                "granule_title": gran_meta["granule_title"],
                "granule_url": gran_meta["granule_url"],
                "granule_processing_version": gran_meta["granule_processing_version"],
                "cell_quality": gran_meta["cell_quality"]
            })

    latest_title = trio_entries[-1].get("title", "")
    if ".V" not in latest_title:
        print(f"[ERROR] Cannot determine global processing version from '{latest_title}'.")
        sys.exit(1)

    gpv = f"V{latest_title.split('.V')[-1].replace('.nc4', '')}"
    meta_extra = {
        "granule_processing_version": gpv,
        "source_data_origin": "NASA_GES_DISC"
    }

    gpm_dataset, metadata = process_granule_data(granules_data, zone_weights, native_cells, meta_extra)

    # TRANSACTION-SAFE REPLACEMENT
    tmp_gpm = out_gpm.with_suffix(".json.tmp")
    tmp_meta = out_meta.with_suffix(".json.tmp")
    bak_gpm = out_gpm.with_suffix(".json.bak")
    bak_meta = out_meta.with_suffix(".json.bak")

    with open(tmp_gpm, "w", encoding="utf-8") as f: json.dump(gpm_dataset, f, indent=2)
    with open(tmp_meta, "w", encoding="utf-8") as f: json.dump(metadata, f, indent=2)

    try:
        with open(tmp_gpm, encoding="utf-8") as f: json.load(f)
        with open(tmp_meta, encoding="utf-8") as f: json.load(f)
    except Exception as e:
        tmp_gpm.unlink(missing_ok=True)
        tmp_meta.unlink(missing_ok=True)
        print(f"[ERROR] JSON validation failed on temporary outputs: {e}")
        sys.exit(1)

    if out_gpm.exists(): shutil.copy2(out_gpm, bak_gpm)
    if out_meta.exists(): shutil.copy2(out_meta, bak_meta)

    try:
        os.replace(tmp_gpm, out_gpm)
        os.replace(tmp_meta, out_meta)
    except Exception as e:
        print(f"[ERROR] Replacement failed: {e}. Restoring backups.")
        if bak_gpm.exists(): os.replace(bak_gpm, out_gpm)
        if bak_meta.exists(): os.replace(bak_meta, out_meta)
        sys.exit(1)

    if bak_gpm.exists(): bak_gpm.unlink()
    if bak_meta.exists(): bak_meta.unlink()

    print(f"\nCanonical datasets successfully generated:")
    print(f"  -> {out_gpm}")
    print(f"  -> {out_meta}")
    print(f"Total zones with REAL_GPM: {len(gpm_dataset['zones'])}")


if __name__ == "__main__":
    main()
