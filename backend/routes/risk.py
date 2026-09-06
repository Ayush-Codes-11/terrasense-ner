"""
Risk routes:
  GET /risk/current            — all zones current risk (computed by prototype scorer)
  GET /risk/current/{zone_id}  — one zone current risk + contributors
  GET /risk/forecast/{zone_id} — NOW (computed) + 24/48/72h (SAMPLE_MOCK)

Phase 4: Current risk is computed dynamically by backend/services/risk_engine.py
         (ml/prototype_scorer.py). Precomputed risk_score from GeoJSON is never used.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from models.schemas import (
    AllZonesRiskResponse,
    ContributorSchema,
    DataMeta,
    ForecastWindow,
    NormalizedFeatures,
    NowWindow,
    ZoneForecastResponse,
    ZoneRisk,
    SAMPLE_META,
)
from services.data_loader import get_all_zone_props, get_zone_props
from services.risk_engine import compute_zone_risk

router = APIRouter(prefix="/risk")

_FORECAST_NOTE = (
    "Current risk (NOW) is computed dynamically by prototype_scorer. "
    "Future forecast windows (+24h/+48h/+72h) are SAMPLE_MOCK scenario values "
    "until Phase 5 connects dynamic accumulation and rainfall forecasts."
)


def _props_to_zone_risk(p: dict) -> ZoneRisk:
    # Dynamically compute risk from raw physical features
    res = compute_zone_risk(p)

    contributors = [
        ContributorSchema(
            feature=c.display_name,
            contribution=round(c.contribution, 4),
            component=c.component,
            display_name=c.display_name,
            normalized_input=round(c.normalized_input, 4),
            weight=c.weight,
        )
        for c in res.contributors
    ]

    normalized_features = NormalizedFeatures(
        terrain=res.normalized_features.terrain,
        recent_rainfall=res.normalized_features.recent_rainfall,
        antecedent_rainfall=res.normalized_features.antecedent_rainfall,
        soil_wetness=res.normalized_features.soil_wetness,
    )

    sw_val = float(p.get("soil_wetness_index") if "soil_wetness_index" in p else p.get("soil_moisture", 0.0))

    return ZoneRisk(
        zone_id=p["zone_id"],
        risk_category=res.risk_category,
        risk_score=res.score,
        score=res.score,
        score_type=res.score_type,
        is_probability=res.is_probability,
        is_calibrated=res.is_calibrated,
        computed_by=res.computed_by,
        slope=float(p.get("slope", 0.0)),
        elevation=float(p.get("elevation", 0.0)),
        soil_moisture=sw_val,
        soil_wetness_index=sw_val,
        rain_24h=float(p.get("rain_24h", 0.0)),
        rain_3d=float(p.get("rain_3d", 0.0)),
        rain_7d=float(p.get("rain_7d", 0.0)) if "rain_7d" in p else None,
        normalized_features=normalized_features,
        contributors=contributors,
        data_meta=DataMeta(
            data_type="SAMPLE_MOCK",
            source="TerraSense Prototype Scorer (SAMPLE_MOCK inputs)",
            is_live=False,
            note="Score computed by ml.prototype_scorer using sample input features.",
        ),
    )


def _props_to_forecast(p: dict) -> ZoneForecastResponse:
    # Compute current risk dynamically
    res = compute_zone_risk(p)

    now_win = NowWindow(
        risk=res.risk_category,
        risk_score=res.score,
        mode="PROTOTYPE_COMPUTED",
        score_type=res.score_type,
        is_probability=res.is_probability,
        is_calibrated=res.is_calibrated,
        computed_by=res.computed_by,
    )

    return ZoneForecastResponse(
        zone_id=p["zone_id"],
        current=res.risk_category,
        current_score=res.score,
        now=now_win,
        forecast={
            "24h": ForecastWindow(
                risk=p["forecast_risk_24h"],
                risk_score=p["forecast_score_24h"],
                antecedent_rain_mm=p["antecedent_24h"],
                mode="SAMPLE_MOCK",
                phase="Phase 5 pending",
            ),
            "48h": ForecastWindow(
                risk=p["forecast_risk_48h"],
                risk_score=p["forecast_score_48h"],
                antecedent_rain_mm=p["antecedent_48h"],
                mode="SAMPLE_MOCK",
                phase="Phase 5 pending",
            ),
            "72h": ForecastWindow(
                risk=p["forecast_risk_72h"],
                risk_score=p["forecast_score_72h"],
                antecedent_rain_mm=p["antecedent_72h"],
                mode="SAMPLE_MOCK",
                phase="Phase 5 pending",
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
    """Returns current risk for all 25 sample zones computed by prototype scorer."""
    all_props = get_all_zone_props()
    zones = [_props_to_zone_risk(p) for p in all_props]
    return AllZonesRiskResponse(
        zones=zones,
        total=len(zones),
        data_meta=DataMeta(
            data_type="SAMPLE_MOCK",
            source="TerraSense Prototype Scorer (SAMPLE_MOCK inputs)",
            is_live=False,
            note="All zone scores computed dynamically using ml.prototype_scorer.",
        ),
    )


# ── GET /risk/current/{zone_id} ──────────────────────────────────────────────

@router.get("/current/{zone_id}", response_model=ZoneRisk)
def get_zone_current_risk(zone_id: str):
    """Returns current risk for a single zone with feature contributors. 404 if not found."""
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
    Returns NOW (computed by prototype scorer) + 24h / 48h / 72h (SAMPLE_MOCK)
    forecast windows for one zone.
    """
    props = get_zone_props(zone_id)
    if props is None:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zone_id.upper()}' not found. Valid IDs are A01–E05.",
        )
    return _props_to_forecast(props)
