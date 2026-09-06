"""
terrain_processor.py — Spatially valid metric terrain derivative and zonal statistics calculation.

Critical Requirement:
Slope and aspect MUST be calculated in metric space (meters), NOT in geographic degrees.
Reprojects DEM to UTM Zone 46N (EPSG:32646) where cell units are meters (~30m x 30m).
Calculates slope via Horn 8-neighbor gradient filter.
Calculates circular mean aspect using vector sine/cosine averaging (not arithmetic mean).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform
import pyproj

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TERRAIN_DIR = _REPO_ROOT / "data" / "real" / "terrain"
_SAMPLE_DIR = _REPO_ROOT / "data" / "sample"

# Projected metric CRS for Mizoram / Aizawl: UTM Zone 46N (WGS 84)
UTM_CRS = "EPSG:32646"


def reproject_dem_to_utm(
    src_path: Path,
    dst_path: Path,
    dst_crs: str = UTM_CRS,
    target_res: float = 30.0,
) -> Dict[str, Any]:
    """
    Reprojects input DEM (EPSG:4326) to UTM Zone 46N (EPSG:32646) with metric resolution (~30m).
    Uses bilinear resampling for continuous elevation surfaces.
    """
    with rasterio.open(src_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs,
            dst_crs,
            src.width,
            src.height,
            *src.bounds,
            resolution=(target_res, target_res),
        )
        kwargs = src.meta.copy()
        kwargs.update({
            "crs": dst_crs,
            "transform": transform,
            "width": width,
            "height": height,
            "resampling": Resampling.bilinear,
        })

        with rasterio.open(dst_path, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.bilinear,
                )

    return {
        "crs": dst_crs,
        "width": width,
        "height": height,
        "resolution_m": target_res,
        "file_path": str(dst_path),
    }


def compute_metric_slope_and_aspect(
    elev: np.ndarray,
    dx: float = 30.0,
    dy: float = 30.0,
    nodata: Optional[float] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes slope (in degrees) and aspect (in compass degrees [0, 360))
    using Horn's (1981) standard 8-neighbor gradient kernel.
    Input elevation raster grid units must be in meters.

    Returns
    -------
    slope_deg : 2D float array of slope in degrees [0, 90)
    aspect_deg: 2D float array of compass aspect in degrees [0, 360)
    valid_mask: 2D boolean array of valid non-nodata pixels
    """
    h, w = elev.shape
    slope_deg = np.full((h, w), np.nan, dtype=np.float32)
    aspect_deg = np.full((h, w), np.nan, dtype=np.float32)

    # Valid mask
    if nodata is not None:
        valid_mask = (elev != nodata) & ~np.isnan(elev) & (elev > -500.0)
    else:
        valid_mask = ~np.isnan(elev) & (elev > -500.0)

    # Horn 3x3 window slices
    # Center: [1:-1, 1:-1]
    z_nw = elev[0:-2, 0:-2]
    z_n  = elev[0:-2, 1:-1]
    z_ne = elev[0:-2, 2:  ]

    z_w  = elev[1:-1, 0:-2]
    z_c  = elev[1:-1, 1:-1]
    z_e  = elev[1:-1, 2:  ]

    z_sw = elev[2:  , 0:-2]
    z_s  = elev[2:  , 1:-1]
    z_se = elev[2:  , 2:  ]

    # Valid mask for all 9 neighbors
    all_valid = (
        valid_mask[0:-2, 0:-2] & valid_mask[0:-2, 1:-1] & valid_mask[0:-2, 2:  ] &
        valid_mask[1:-1, 0:-2] & valid_mask[1:-1, 1:-1] & valid_mask[1:-1, 2:  ] &
        valid_mask[2:  , 0:-2] & valid_mask[2:  , 1:-1] & valid_mask[2:  , 2:  ]
    )

    # Partial derivatives in metric space (rise / run in m/m)
    # dx is horizontal, dy is vertical
    dz_dx = ((z_ne + 2.0 * z_e + z_se) - (z_nw + 2.0 * z_w + z_sw)) / (8.0 * dx)
    dz_dy = ((z_nw + 2.0 * z_n + z_ne) - (z_sw + 2.0 * z_s + z_se)) / (8.0 * dy)

    # Slope
    rise_run = np.sqrt(dz_dx**2 + dz_dy**2)
    slopes = np.degrees(np.arctan(rise_run))

    # Aspect: compass degrees clockwise from North (0° = North, 90° = East, etc.)
    # In GIS convention: atan2(-dz/dy, dz/dx) converted to compass
    aspects = (90.0 - np.degrees(np.arctan2(dz_dy, -dz_dx))) % 360.0

    # Assign to interior cells where all neighbors are valid
    slope_interior = np.full_like(slopes, np.nan)
    aspect_interior = np.full_like(aspects, np.nan)

    slope_interior[all_valid] = slopes[all_valid]
    aspect_interior[all_valid] = aspects[all_valid]

    slope_deg[1:-1, 1:-1] = slope_interior
    aspect_deg[1:-1, 1:-1] = aspect_interior

    return slope_deg, aspect_deg, valid_mask


def calculate_circular_mean_aspect(aspects: np.ndarray) -> Tuple[Optional[float], Optional[str]]:
    """
    Computes circular mean aspect using sine and cosine vector decomposition.
    Prevents false arithmetic cancellation (e.g. mean of 359° and 1° is 0° / 360°, not 180°).
    """
    valid = aspects[~np.isnan(aspects)]
    if len(valid) == 0:
        return None, None

    rads = np.radians(valid)
    sin_mean = np.mean(np.sin(rads))
    cos_mean = np.mean(np.cos(rads))

    # Magnitude of resultant vector
    r_mag = np.sqrt(sin_mean**2 + cos_mean**2)
    if r_mag < 0.01:  # Flat / completely dispersed aspect
        return None, "Variable / Flat"

    circ_mean_rad = np.arctan2(sin_mean, cos_mean)
    circ_mean_deg = float(np.degrees(circ_mean_rad) % 360.0)

    cardinal = aspect_to_cardinal(circ_mean_deg)
    return round(circ_mean_deg, 1), cardinal


def aspect_to_cardinal(deg: float) -> str:
    """Maps compass aspect degrees to 8-point cardinal direction."""
    if deg is None:
        return "N/A"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"]
    idx = int((deg + 22.5) // 45)
    return directions[idx % 8]


def process_pilot_zonal_terrain(
    dem_tif: Optional[Path] = None,
    grid_geojson: Optional[Path] = None,
    out_zonal_json: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    End-to-end processing:
    1. Reprojects cropped DEM to metric UTM Zone 46N
    2. Calculates metric slope and aspect
    3. Overlays each of the 25 pilot grid zones
    4. Computes zonal statistics and saves to zonal_terrain.json
    """
    if dem_tif is None:
        dem_tif = _TERRAIN_DIR / "copernicus_glo30_aizawl.tif"
    if grid_geojson is None:
        grid_geojson = _SAMPLE_DIR / "grid-risk.geojson"
    if out_zonal_json is None:
        out_zonal_json = _TERRAIN_DIR / "zonal_terrain.json"

    if not dem_tif.exists():
        raise FileNotFoundError(f"DEM file not found: {dem_tif}")

    utm_tif = _TERRAIN_DIR / "copernicus_glo30_utm46n.tif"
    print(f"Reprojecting DEM to UTM Zone 46N: {utm_tif}...")
    reproject_dem_to_utm(dem_tif, utm_tif, dst_crs=UTM_CRS, target_res=30.0)

    with rasterio.open(utm_tif) as src:
        elev_arr = src.read(1)
        nodata_val = src.nodata
        dx, dy = src.res
        utm_crs = src.crs

        print(f"Computing metric slope and aspect on {src.width}x{src.height} grid (dx={dx:.1f}m, dy={dy:.1f}m)...")
        slope_arr, aspect_arr, full_valid_mask = compute_metric_slope_and_aspect(
            elev_arr, dx=dx, dy=dy, nodata=nodata_val
        )

        # Coordinate transformer from EPSG:4326 to UTM 46N
        proj_to_utm = pyproj.Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True).transform

        # Load grid features
        with open(grid_geojson, encoding="utf-8") as f:
            grid_fc = json.load(f)

        zones_terrain: Dict[str, Any] = {}

        for feat in grid_fc.get("features", []):
            props = feat.get("properties", {})
            zid = str(props.get("zone_id")).upper()
            poly_wgs84 = shape(feat["geometry"])
            poly_utm = shapely_transform(proj_to_utm, poly_wgs84)

            # Mask raster with zone polygon
            try:
                masked_elev, masked_transform = mask(src, [poly_utm], crop=True, nodata=nodata_val)
                masked_elev_2d = masked_elev[0]

                # Distinguish true zone interior from crop bounding box exterior
                masked_elev_ma, _ = mask(src, [poly_utm], crop=True, filled=False)
                inside_zone_mask = ~masked_elev_ma[0].mask
                zone_pixel_count = int(inside_zone_mask.sum())

                # Compute slope on cropped zone with padding
                z_slope, z_aspect, z_valid = compute_metric_slope_and_aspect(
                    masked_elev_2d, dx=dx, dy=dy, nodata=nodata_val
                )

                # True valid elevation pixels strictly inside the zone
                valid_elev_mask = inside_zone_mask & (masked_elev_2d != nodata_val) & ~np.isnan(masked_elev_2d) & (masked_elev_2d > -500.0)
                valid_elev = masked_elev_2d[valid_elev_mask]

                source_nodata_count = zone_pixel_count - int(valid_elev_mask.sum())
                source_nodata_frac = round(source_nodata_count / zone_pixel_count, 4) if zone_pixel_count > 0 else 0.0

                # Valid slope pixels where Horn 8-neighbor gradient was successfully evaluated
                valid_slope = z_slope[~np.isnan(z_slope)]
                valid_aspect = z_aspect[~np.isnan(z_aspect)]

                total_crop_cells = int(masked_elev_2d.size)
                valid_count = int(len(valid_slope))
                proc_mask_frac = round((total_crop_cells - valid_count) / total_crop_cells, 4) if total_crop_cells > 0 else 0.0

                if len(valid_elev) > 0:
                    elev_mean = round(float(np.mean(valid_elev)), 1)
                    elev_min = round(float(np.min(valid_elev)), 1)
                    elev_max = round(float(np.max(valid_elev)), 1)
                else:
                    elev_mean = elev_min = elev_max = 0.0

                if valid_count > 0:
                    slope_mean = round(float(np.mean(valid_slope)), 2)
                    slope_median = round(float(np.median(valid_slope)), 2)
                    slope_p90 = round(float(np.percentile(valid_slope, 90)), 2)
                    slope_max = round(float(np.max(valid_slope)), 2)
                    slope_min = round(float(np.min(valid_slope)), 2)

                    circ_aspect, cardinal = calculate_circular_mean_aspect(valid_aspect)
                else:
                    slope_mean = slope_median = slope_p90 = slope_max = slope_min = 0.0
                    circ_aspect = None
                    cardinal = "N/A"

                zones_terrain[zid] = {
                    "zone_id": zid,
                    "mean_elevation_m": elev_mean,
                    "min_elevation_m": elev_min,
                    "max_elevation_m": elev_max,
                    "elevation_range_m": round(elev_max - elev_min, 1) if len(valid_elev) > 0 else 0.0,
                    "mean_slope_deg": slope_mean,
                    "median_slope_deg": slope_median,
                    "p90_slope_deg": slope_p90,
                    "max_slope_deg": slope_max,
                    "min_slope_deg": slope_min,
                    "circular_mean_aspect_deg": circ_aspect,
                    "dominant_aspect_cardinal": cardinal,
                    "valid_pixel_count": valid_count,
                    "zone_pixel_count": zone_pixel_count,
                    "source_nodata_fraction_within_zone": source_nodata_frac,
                    "processing_window_mask_fraction": proc_mask_frac,
                    "nodata_fraction": source_nodata_frac,
                    "data_type": "REAL_DEM",
                    "source": "Copernicus DEM GLO-30 Public — distributed via AWS Open Data/Sinergise",
                    "processing_crs": UTM_CRS,
                    "grid_resolution_m": 30.0,
                    "slope_derivation_method": "Horn 8-neighbor gradient in UTM 46N metric coordinates",
                }

            except Exception as e:
                print(f"Error processing zone {zid}: {e}")
                zones_terrain[zid] = {
                    "zone_id": zid,
                    "error": str(e),
                    "data_type": "REAL_DEM",
                }

    # Save to zonal_terrain.json
    output_data = {
        "dataset": "Aizawl Pilot 25-Zone Zonal Terrain Statistics",
        "data_type": "REAL_DEM",
        "source": "Copernicus DEM GLO-30 Public — distributed via AWS Open Data/Sinergise",
        "product": "Copernicus GLO-30 DSM",
        "resolution": "30m",
        "processing_crs": UTM_CRS,
        "derivation_notes": (
            "Slopes computed strictly in metric space (UTM 46N) via Horn 8-neighbor method. "
            "Aspects computed using circular sine/cosine vector averaging. "
            "mean_slope_deg serves as the primary terrain hazard input to the prototype scorer."
        ),
        "total_zones": len(zones_terrain),
        "zones": zones_terrain,
    }

    with open(out_zonal_json, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"Successfully generated zonal terrain statistics for {len(zones_terrain)} zones -> {out_zonal_json}")
    return output_data


if __name__ == "__main__":
    process_pilot_zonal_terrain()
