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
    return HealthResponse(
        status="ok",
        data_mode="SAMPLE_MOCK",
        version="0.1.0-phase3",
        disclaimer=(
            "All risk data is SAMPLE_MOCK for UI/API testing. "
            "Not for operational disaster-management use. "
            "Phase 4+ connects the prototype risk engine."
        ),
        endpoints=[
            "GET /health",
            "GET /zones",
            "GET /risk/current",
            "GET /risk/current/{zone_id}",
            "GET /risk/forecast/{zone_id}",
            "GET /weather/{zone_id}",
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
