"""
Risk routes:
  GET /risk/current          — all zones current risk
  GET /risk/current/{zone_id} — one zone current risk
  GET /risk/forecast/{zone_id} — NOW + 24/48/72h forecast windows

Phase 3: all values served directly from data/sample/grid-risk.geojson.
         No calculations performed — that is Phase 4 (prototype_scorer.py).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from models.schemas import (
    AllZonesRiskResponse,
    DataMeta,
    ForecastWindow,
    ZoneForecastResponse,
    ZoneRisk,
    SAMPLE_META,
)
from services.data_loader import get_all_zone_props, get_zone_props

router = APIRouter(prefix="/risk")

_FORECAST_NOTE = (
    "Forecast windows and antecedent rainfall totals are pre-computed in the "
    "SAMPLE_MOCK dataset. Phase 4 calculates antecedent totals dynamically "
    "from the rainfall accumulator."
)


def _props_to_zone_risk(p: dict) -> ZoneRisk:
    return ZoneRisk(
        zone_id=p["zone_id"],
        risk_category=p["risk_category"],
        risk_score=p["risk_score"],
        slope=p["slope"],
        elevation=p["elevation"],
        soil_moisture=p["soil_moisture"],
        rain_24h=p["rain_24h"],
        rain_3d=p["rain_3d"],
        rain_7d=p["rain_7d"],
        data_meta=SAMPLE_META,
    )


def _props_to_forecast(p: dict) -> ZoneForecastResponse:
    return ZoneForecastResponse(
        zone_id=p["zone_id"],
        current=p["risk_category"],
        current_score=p["risk_score"],
        forecast={
            "24h": ForecastWindow(
                risk=p["forecast_risk_24h"],
                risk_score=p["forecast_score_24h"],
                antecedent_rain_mm=p["antecedent_24h"],
            ),
            "48h": ForecastWindow(
                risk=p["forecast_risk_48h"],
                risk_score=p["forecast_score_48h"],
                antecedent_rain_mm=p["antecedent_48h"],
            ),
            "72h": ForecastWindow(
                risk=p["forecast_risk_72h"],
                risk_score=p["forecast_score_72h"],
                antecedent_rain_mm=p["antecedent_72h"],
            ),
        },
        data_meta=DataMeta(
            data_type="SAMPLE_MOCK",
            source="TerraSense demo dataset v0.1",
            is_live=False,
            note=_FORECAST_NOTE,
        ),
    )


# ── GET /risk/current ────────────────────────────────────────────────────────

@router.get("/current", response_model=AllZonesRiskResponse)
def get_all_current_risk():
    """Returns current risk for all 25 sample zones."""
    all_props = get_all_zone_props()
    zones = [_props_to_zone_risk(p) for p in all_props]
    return AllZonesRiskResponse(
        zones=zones,
        total=len(zones),
        data_meta=SAMPLE_META,
    )


# ── GET /risk/current/{zone_id} ──────────────────────────────────────────────

@router.get("/current/{zone_id}", response_model=ZoneRisk)
def get_zone_current_risk(zone_id: str):
    """Returns current risk for a single zone. 404 if zone_id not found."""
    props = get_zone_props(zone_id)
    if props is None:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zone_id.upper()}' not found. Valid IDs are A01–E05.",
        )
    return _props_to_zone_risk(props)


# ── GET /risk/forecast/{zone_id} ────────────────────────────────────────────

@router.get("/forecast/{zone_id}", response_model=ZoneForecastResponse)
def get_zone_forecast(zone_id: str):
    """
    Returns NOW + 24h / 48h / 72h forecast windows for one zone.
    antecedent_rain_mm values reflect accumulated rainfall
    (observed_24h + cumulative forecast windows).
    """
    props = get_zone_props(zone_id)
    if props is None:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zone_id.upper()}' not found. Valid IDs are A01–E05.",
        )
    return _props_to_forecast(props)
