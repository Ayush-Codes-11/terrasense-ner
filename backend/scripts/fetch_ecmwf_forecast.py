import os
import sys
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import math
from typing import Dict, Any, List

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DATA_DIR = _REPO_ROOT / "data" if (_REPO_ROOT / "data").exists() else _BACKEND_DIR / "data"
_WEATHER_OUT_DIR = _DATA_DIR / "real" / "weather"
_GRID_RISK_PATH = _DATA_DIR / "sample" / "grid-risk.geojson"

ECMWF_FORECAST_FILE = _WEATHER_OUT_DIR / "ecmwf_forecast.json"
GPM_METADATA_FILE = _WEATHER_OUT_DIR / "metadata.json"


def _get_zone_centroids() -> Dict[str, tuple]:
    import shapely.geometry
    import pyproj
    from shapely.ops import transform

    wgs84 = pyproj.CRS('EPSG:4326')
    utm46n = pyproj.CRS('EPSG:32646')
    project_to_utm = pyproj.Transformer.from_crs(wgs84, utm46n, always_xy=True).transform
    project_to_wgs84 = pyproj.Transformer.from_crs(utm46n, wgs84, always_xy=True).transform

    data = json.loads(_GRID_RISK_PATH.read_text(encoding="utf-8"))
    centroids = {}
    for f in data.get("features", []):
        zid = f.get("properties", {}).get("zone_id")
        if zid:
            coords = f["geometry"]["coordinates"][0]
            poly_wgs = shapely.geometry.Polygon(coords)
            poly_utm = transform(project_to_utm, poly_wgs)
            cent_utm = poly_utm.centroid
            cent_lon, cent_lat = project_to_wgs84(cent_utm.x, cent_utm.y)
            centroids[zid] = (cent_lat, cent_lon)
    return centroids


def process_ecmwf_response(res: List[Dict[str, Any]], sorted_zids: List[str], centroids: Dict[str, tuple], f1_date: datetime, run_str: str) -> tuple[Dict[str, Any], int]:
    if len(res) != len(sorted_zids) or len(res) != 25:
        raise ValueError(f"Expected 25 responses, got {len(res)} vs {len(sorted_zids)}")

    output_data = {
        "metadata": {
            "data_type": "REAL_FORECAST",
            "source_data_origin": "ECMWF_OPEN_METEO",
            "meteorological_provider": "ECMWF",
            "model": "IFS_HRES",
            "model_identifier": "ecmwf_ifs",
            "model_resolution": "9 km",
            "model_grid": "O1280",
            "access_provider": "OPEN_METEO",
            "model_run_initialisation_utc": run_str + ":00Z",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "timezone": "UTC",
            "precipitation_unit": "mm",
            "cell_selection": "nearest",
            "elevation_downscaling": "disabled",
            "days": {
                "f1": f1_date.strftime("%Y-%m-%d"),
                "f2": (f1_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                "f3": (f1_date + timedelta(days=2)).strftime("%Y-%m-%d"),
            }
        },
        "zones": {}
    }

    unique_cells = set()

    for i, zid in enumerate(sorted_zids):
        c_data = res[i]

        if "latitude" not in c_data or "longitude" not in c_data:
            raise ValueError(f"Missing latitude/longitude for zone {zid}")

        hourly = c_data.get("hourly", {})
        if "precipitation" not in hourly or "time" not in hourly:
            raise ValueError(f"Missing hourly data or time for zone {zid}")

        ret_lat = c_data["latitude"]
        ret_lon = c_data["longitude"]
        unique_cells.add((ret_lat, ret_lon))

        hourly_precip = hourly["precipitation"]
        hourly_time = hourly["time"]

        if c_data.get("hourly_units", {}).get("precipitation") != "mm":
            raise ValueError(f"Unexpected precipitation unit for zone {zid}")

        if len(hourly_precip) < 73:
            raise ValueError(f"Insufficient hourly data for zone {zid}: {len(hourly_precip)} hours.")

        for h_idx in range(1, 73):
            val = hourly_precip[h_idx]
            if val is None or not math.isfinite(val) or val < 0:
                raise ValueError(f"Invalid precipitation value {val} at index {h_idx} for zone {zid}")

        for h_idx in range(1, 73):
            expected_dt = f1_date + timedelta(hours=h_idx)
            expected_str = expected_dt.strftime("%Y-%m-%dT%H:%M")
            if hourly_time[h_idx] != expected_str:
                raise ValueError(f"Timestamp mismatch at index {h_idx}: expected {expected_str}, got {hourly_time[h_idx]}")

        f1_vals = hourly_precip[1:25]
        f2_vals = hourly_precip[25:49]
        f3_vals = hourly_precip[49:73]

        f1_sum = round(sum(f1_vals), 2)
        f2_sum = round(sum(f2_vals), 2)
        f3_sum = round(sum(f3_vals), 2)

        output_data["zones"][zid] = {
            "requested_centroid": {"lat": centroids[zid][0], "lon": centroids[zid][1]},
            "returned_model_grid": {"lat": ret_lat, "lon": ret_lon},
            "grid_cell_id": f"ECMWF_{ret_lat:.5f}_{ret_lon:.5f}",
            "forecast_interval_mm": {
                "0_24h": f1_sum,
                "24_48h": f2_sum,
                "48_72h": f3_sum
            },
            "hourly_24h_mm": f1_vals,
            "hourly_48h_mm": f2_vals,
            "hourly_72h_mm": f3_vals
        }

    return output_data, len(unique_cells)


def fetch_ecmwf(run_live: bool = True):
    _WEATHER_OUT_DIR.mkdir(parents=True, exist_ok=True)

    tmp_file = ECMWF_FORECAST_FILE.with_suffix(".tmp")
    bak_file = ECMWF_FORECAST_FILE.with_suffix(".bak")

    # Startup recovery
    if bak_file.exists():
        if not ECMWF_FORECAST_FILE.exists():
            os.replace(bak_file, ECMWF_FORECAST_FILE)
        else:
            bak_file.unlink()

    if not run_live:
        return

    if not GPM_METADATA_FILE.exists():
        print("ERROR: GPM metadata.json not found. Cannot anchor forecast.")
        sys.exit(1)

    gpm_meta = json.loads(GPM_METADATA_FILE.read_text(encoding="utf-8"))
    d0_str = gpm_meta.get("days", {}).get("d0")
    if not d0_str:
        print("ERROR: GPM metadata missing days.d0")
        sys.exit(1)

    d0_date = datetime.strptime(d0_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    f1_date = d0_date + timedelta(days=1)

    run_str = f1_date.strftime("%Y-%m-%dT00:00")
    print(f"Targeting ECMWF run: {run_str}")

    centroids = _get_zone_centroids()
    sorted_zids = sorted(centroids.keys())
    lats_str = ",".join(str(round(centroids[z][0], 4)) for z in sorted_zids)
    lons_str = ",".join(str(round(centroids[z][1], 4)) for z in sorted_zids)
    elevs_str = ",".join("nan" for _ in sorted_zids)

    url = (
        f"https://single-runs-api.open-meteo.com/v1/forecast"
        f"?latitude={lats_str}&longitude={lons_str}&elevation={elevs_str}"
        f"&hourly=precipitation&precipitation_unit=mm&models=ecmwf_ifs&timezone=UTC"
        f"&cell_selection=nearest&run={run_str}"
    )

    print("Fetching from Open-Meteo Single Runs API...")
    req = urllib.request.Request(url, headers={"User-Agent": "TerraSense/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()}")
        print(f"Run {run_str} might not be available yet.")
        sys.exit(1)
    except Exception as e:
        print(f"Fetch failed: {e}")
        sys.exit(1)

    if isinstance(res, dict):
        res = [res]

    output_data, unique_cells_count = process_ecmwf_response(res, sorted_zids, centroids, f1_date, run_str)

    print(f"Successfully processed {len(centroids)} zones.")
    print(f"Unique ECMWF HRES cells mapped: {unique_cells_count}")

    # 1. Write to tmp
    tmp_file.write_text(json.dumps(output_data, indent=2), encoding="utf-8")

    # 2. Parse back and validate
    try:
        parsed = json.loads(tmp_file.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict) or "zones" not in parsed:
            raise ValueError("Invalid JSON structure")
    except Exception as e:
        tmp_file.unlink()
        print(f"Validation of temporary file failed: {e}")
        sys.exit(1)

    # 3. Transactional replace
    try:
        if ECMWF_FORECAST_FILE.exists():
            os.replace(ECMWF_FORECAST_FILE, bak_file)
        os.replace(tmp_file, ECMWF_FORECAST_FILE)
    except Exception as e:
        if bak_file.exists():
            os.replace(bak_file, ECMWF_FORECAST_FILE)
        print(f"Transaction failed: {e}")
        sys.exit(1)
    finally:
        if bak_file.exists() and ECMWF_FORECAST_FILE.exists():
            try:
                bak_file.unlink()
            except OSError:
                pass
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except OSError:
                pass

    print(f"Saved to {ECMWF_FORECAST_FILE}")


if __name__ == "__main__":
    fetch_ecmwf()
