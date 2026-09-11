"""
GET /zones — full GeoJSON pass-through from canonical data/sample/
GET /health — backend status
"""
from __future__ import annotations

from fastapi import APIRouter
from models.schemas import DataMeta, HealthResponse, ZonesResponse, SAMPLE_META
from services.data_loader import load_grid_risk, get_all_zone_props

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    from services.terrain_loader import get_terrain_provenance_status
    from services.gpm_loader import get_gpm_provenance_status
    from services.forecast_loader import get_forecast_provenance_status
    from services.soil_loader import get_soil_provenance_status

    terrain_prov = get_terrain_provenance_status().get("status", "SAMPLE_MOCK")
    gpm_prov = get_gpm_provenance_status().get("status", "SAMPLE_MOCK")
    fcst_prov = get_forecast_provenance_status().get("status", "SAMPLE_MOCK")
    soil_prov = get_soil_provenance_status().get("status", "SAMPLE_MOCK")

    return HealthResponse(
        status="ok",
        risk_engine="prototype_scorer_active",
        data_mode="PER_SOURCE_PROVENANCE",
        phase="real_data_ingestion_complete",
        disclaimer=(
            "Prototype relative-risk scorer. Data provenance is reported per feature; "
            "not for operational disaster-management use."
        ),
        data_sources={
            "terrain": terrain_prov,
            "observed_rainfall": gpm_prov,
            "forecast_rainfall": fcst_prov,
            "soil_wetness": soil_prov
        },
        endpoints=[
            "GET /health",
            "GET /zones",
            "GET /risk/current",
            "GET /risk/current/{zone_id}",
            "GET /risk/forecast/{zone_id}",
            "GET /weather/{zone_id}",
            "GET /geodata/osm/status",
            "GET /geodata/osm/roads",
            "GET /geodata/osm/settlements",
            "GET /geodata/osm/critical-facilities",
            "GET /exposure/{zone_id}",
            "GET /priority/{zone_id}",
            "GET /docs",
        ],
    )


@router.get("/zones", response_model=ZonesResponse)
def get_zones():
    """
    Returns the full risk-grid GeoJSON with API metadata.
    Source: data/sample/grid-risk.geojson (canonical copy).
    Frontend public/ copy is used for map tile rendering; this endpoint
    serves the same data with data_meta attached.
    """
    fc = load_grid_risk()
    features = fc.get("features", [])
    return ZonesResponse(
        feature_count=len(features),
        data_meta=SAMPLE_META,
        features=features,
    )
