"""
GET /weather/{zone_id} — sample rainfall inputs for a zone.

Phase 3: served from data/sample/grid-risk.geojson (rainfall fields).
Phase 5: replace with real IMD/GPM observations via adapter.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from models.schemas import DataMeta, WeatherResponse
from services.data_loader import get_zone_props

router = APIRouter(prefix="/weather")

_WEATHER_NOTE = (
    "All rainfall values are SAMPLE_MOCK — not real IMD/GPM observations. "
    "Phase 5 connects real weather data sources."
)


@router.get("/{zone_id}", response_model=WeatherResponse)
def get_zone_weather(zone_id: str):
    """
    Returns rainfall observations and forecast inputs for a zone.
    All values SAMPLE_MOCK in Phase 3.
    """
    props = get_zone_props(zone_id)
    if props is None:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zone_id.upper()}' not found. Valid IDs are A01–E05.",
        )
    return WeatherResponse(
        zone_id=props["zone_id"],
        rain_24h_mm=props["rain_24h"],
        rain_3d_mm=props["rain_3d"],
        rain_7d_mm=props["rain_7d"],
        forecast_24h_mm=props["forecast_24h"],
        forecast_48h_mm=props["forecast_48h"],
        forecast_72h_mm=props["forecast_72h"],
        antecedent_24h_mm=props["antecedent_24h"],
        antecedent_48h_mm=props["antecedent_48h"],
        antecedent_72h_mm=props["antecedent_72h"],
        data_meta=DataMeta(
            data_type="SAMPLE_MOCK",
            source="TerraSense demo dataset v0.1",
            is_live=False,
            note=_WEATHER_NOTE,
        ),
    )
