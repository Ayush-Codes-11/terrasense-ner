"""
fetch_or_prepare_dem.py — Downloads and crops Copernicus GLO-30 DEM for the Aizawl pilot area.

Attribution & Provenance:
Source: Copernicus DEM GLO-30 Public — distributed via AWS Open Data/Sinergise
Product: Copernicus GLO-30 DSM (~30m / 1 arc-second)
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

import rasterio
from rasterio.windows import from_bounds

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TERRAIN_DIR = _REPO_ROOT / "data" / "real" / "terrain"

# Tile covering Aizawl (23°N, 92°E)
TILE_NAME = "Copernicus_DSM_COG_10_N23_00_E092_00_DEM"
DEM_URL = (
    f"https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/{TILE_NAME}/{TILE_NAME}.tif"
)

# Pilot area envelope
PILOT_BBOX = {
    "south": 23.6896,
    "west": 92.6801,
    "north": 23.7646,
    "east": 92.7551,
}
MARGIN = 0.01  # ~1 km buffer for gradient boundary calculation
CROP_BOUNDS = (
    PILOT_BBOX["west"] - MARGIN,
    PILOT_BBOX["south"] - MARGIN,
    PILOT_BBOX["east"] + MARGIN,
    PILOT_BBOX["north"] + MARGIN,
)


def download_file(url: str, dest_path: Path):
    print(f"Connecting to {url}...")
    req = urllib.request.Request(url, headers={"User-Agent": "TerraSense-DEM-Fetcher/1.0"})
    with urllib.request.urlopen(req) as resp:
        total_size = int(resp.headers.get("Content-Length", 0))
        print(f"Total size: {total_size / (1024*1024):.2f} MB")

        downloaded = 0
        chunk_size = 1024 * 1024  # 1 MB chunks
        t0 = time.time()
        last_log = t0

        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                now = time.time()
                if now - last_log > 5.0 or downloaded == total_size:
                    pct = (downloaded / total_size * 100) if total_size else 0
                    mb = downloaded / (1024 * 1024)
                    speed = mb / (now - t0) if (now - t0) > 0 else 0
                    print(f"Downloaded: {mb:.1f} MB ({pct:.1f}%) at {speed:.2f} MB/s")
                    last_log = now

    print(f"Download complete in {time.time() - t0:.1f}s.")


def crop_dem():
    _TERRAIN_DIR.mkdir(parents=True, exist_ok=True)
    cropped_tif = _TERRAIN_DIR / "copernicus_glo30_aizawl.tif"
    meta_json = _TERRAIN_DIR / "metadata.json"
    temp_tif = _TERRAIN_DIR / f"{TILE_NAME}_full.tif"

    if not cropped_tif.exists():
        if not temp_tif.exists():
            download_file(DEM_URL, temp_tif)

        print(f"Cropping full tile to bounds: {CROP_BOUNDS}...")
        with rasterio.open(temp_tif) as src:
            nodata_val = src.nodata if src.nodata is not None else -999999.0

            win = from_bounds(*CROP_BOUNDS, transform=src.transform)
            win = win.round_offsets().round_lengths()
            win_transform = src.window_transform(win)

            cropped_arr = src.read(1, window=win)
            h, w = cropped_arr.shape

            out_meta = src.meta.copy()
            out_meta.update({
                "height": h,
                "width": w,
                "transform": win_transform,
                "nodata": nodata_val,
            })

            with rasterio.open(cropped_tif, "w", **out_meta) as dst:
                dst.write(cropped_arr, 1)

            print(f"Saved cropped DEM: {cropped_tif} ({w}x{h} px, size: {cropped_tif.stat().st_size} bytes)")

        # Clean up temporary full tile
        if temp_tif.exists():
            try:
                temp_tif.unlink()
                print("Cleaned up temporary full tile.")
            except Exception as e:
                print(f"Note: Could not delete temp file: {e}")
    else:
        print(f"Cropped DEM already exists: {cropped_tif}")

    # Inspect cropped raster
    with rasterio.open(cropped_tif) as src:
        arr = src.read(1)
        w, h = src.width, src.height
        nodata_val = src.nodata
        valid_mask = (arr != nodata_val)
        valid_pixels = int(valid_mask.sum())
        total_pixels = int(w * h)
        nodata_pct = round((total_pixels - valid_pixels) / total_pixels * 100, 2)
        elev_min = float(arr[valid_mask].min()) if valid_pixels > 0 else None
        elev_max = float(arr[valid_mask].max()) if valid_pixels > 0 else None
        elev_mean = round(float(arr[valid_mask].mean()), 2) if valid_pixels > 0 else None

    # Write metadata
    metadata = {
        "source": "Copernicus DEM GLO-30 Public — distributed via AWS Open Data/Sinergise",
        "product": "Copernicus GLO-30 DSM",
        "data_type": "REAL_DEM",
        "spatial_resolution": "30m (approx. 1 arc-second)",
        "crs": str(src.crs),
        "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "tile_name": TILE_NAME,
        "original_tile_bounds": [92.0, 23.0, 93.0, 24.0],
        "processing_bounds": list(CROP_BOUNDS),
        "pilot_grid_bounds": [PILOT_BBOX["west"], PILOT_BBOX["south"], PILOT_BBOX["east"], PILOT_BBOX["north"]],
        "dimensions": [h, w],
        "file_size_bytes": cropped_tif.stat().st_size,
        "nodata_value": nodata_val,
        "nodata_percentage": nodata_pct,
        "elevation_summary": {
            "min_m": elev_min,
            "max_m": elev_max,
            "mean_m": elev_mean,
        },
        "attribution": "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved. Distributed via AWS Open Data/Sinergise.",
    }

    with open(meta_json, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to {meta_json}")


if __name__ == "__main__":
    crop_dem()
