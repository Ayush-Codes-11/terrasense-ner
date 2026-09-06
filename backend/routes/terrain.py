"""
terrain.py — Terrain/DEM API routes for TerraSense NER backend.

GET /terrain/status  — DEM source metadata and provenance status.
GET /terrain/{zone_id} — Zonal terrain statistics for a specific zone.

Phase 7: All terrain data is sourced from Copernicus GLO-30 (REAL_DEM).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any, Dict

from services.terrain_loader import (
    get_zone_terrain,
    get_all_zones_terrain,
    get_terrain_provenance_status,
    load_terrain_metadata,
)

router = APIRouter(prefix="/terrain", tags=["Terrain"])


@router.get("/status", response_model=Dict[str, Any])
def get_terrain_status():
    """
    Returns DEM metadata and provenance status.

    Reports:
    - Source/product (Copernicus GLO-30 DSM)
    - Original tile URL / source bucket
    - CRS, resolution, dimensions, nodata fraction
    - Processing CRS (UTM Zone 46N / EPSG:32646)
    - Retrieval timestamp
    - Attribution

    Phase 7: status should be 'REAL_DEM' once copernicus_glo30_aizawl.tif is on disk.
    """
    prov = get_terrain_provenance_status()
    meta = load_terrain_metadata()

    response: Dict[str, Any] = {
        "status": prov["status"],
        "is_real": prov["is_real"],
        "source": prov["source"],
        "product": prov["product"],
        "data_type": "REAL_DEM" if prov["is_real"] else "SAMPLE_MOCK",
        "spatial_resolution": prov.get("resolution", "unknown"),
        "crs": prov.get("crs", "EPSG:4326"),
        "processing_crs": prov.get("processing_crs", "None"),
        "total_zones_with_terrain": prov.get("total_zones", 0),
        "attribution": prov.get("attribution"),
        "notes": prov.get("notes"),
    }

    if meta:
        response["original_tile_url"] = (
            "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/"
            "Copernicus_DSM_COG_10_N23_00_E092_00_DEM/"
            "Copernicus_DSM_COG_10_N23_00_E092_00_DEM.tif"
        )
        response["tile_name"] = meta.get("tile_name")
        response["original_tile_bounds"] = meta.get("original_tile_bounds")
        response["cropped_bounds"] = meta.get("processing_bounds")
        response["pilot_grid_bounds"] = meta.get("pilot_grid_bounds")
        response["dimensions_px"] = meta.get("dimensions")
        response["file_size_bytes"] = meta.get("file_size_bytes")
        response["nodata_value"] = meta.get("nodata_value")
        response["nodata_percentage"] = meta.get("nodata_percentage")
        response["retrieved_at"] = meta.get("retrieved_at")
        response["elevation_summary"] = meta.get("elevation_summary")
        response["full_attribution"] = meta.get("attribution")

    return response


@router.get("/{zone_id}", response_model=Dict[str, Any])
def get_zone_terrain_stats(zone_id: str):
    """
    Returns zonal terrain statistics for a specific zone.

    Statistics include:
    - mean/min/max elevation (metres, from real DEM)
    - mean/median/P90/max/min slope (degrees, computed in UTM 46N metric CRS)
    - circular mean aspect (degrees, using vector sine/cosine averaging)
    - valid pixel count and nodata fraction
    - data provenance fields

    Returns 404 if zone_id is not in the pilot grid (A01–E05).
    """
    zone_data = get_zone_terrain(zone_id)
    if zone_data is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Zone '{zone_id.upper()}' not found in terrain dataset. "
                "Valid zone IDs are A01–E05 (25 zones in the Aizawl pilot grid). "
                "Ensure DEM processing has been run (backend/scripts/fetch_or_prepare_dem.py)."
            ),
        )
    return zone_data
