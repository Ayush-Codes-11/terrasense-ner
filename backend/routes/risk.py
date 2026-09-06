"""
Risk routes:
  GET /risk/current            — all zones current risk (computed by prototype scorer)
  GET /risk/current/{zone_id}  — one zone current risk + contributors
  GET /risk/forecast/{zone_id} — weather-linked landslide-risk outlook:
                                 NOW, +24h, +48h, +72h ALL computed by prototype scorer
                                 using canonical non-overlapping rolling rainfall.

Phase 5: Replaced all legacy mock forecast fields with dynamically computed
         risk outlooks across all 4 horizons.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from models.schemas import (
    AllZonesRiskResponse,
    ContributorSchema,
    DataMeta,
    HorizonWindowSchema,
    NormalizedFeatures,
    ZoneForecastResponse,
    ZoneRisk,
    SAMPLE_META,
)
from services.data_loader import get_all_zone_props, get_zone_props
from services.rainfall import get_rainfall_series
from services.risk_engine import compute_zone_risk
from services.risk_forecast import compute_zone_risk_outlook, ForecastHorizonResult

router = APIRouter(prefix="/risk")

_OUTLOOK_NOTE = (
    "Weather-linked landslide-risk outlook. "
    "NOW, +24h, +48h, and +72h risk scores are ALL computed by the prototype scorer "
    "using rolling 3-day antecedent rainfall accumulation. "
    "Input rainfall observations and forecast intervals are SAMPLE_MOCK."
)


def _props_to_zone_risk(p: dict) -> ZoneRisk:
    zid = str(p["zone_id"]).upper()

    # Load canonical rainfall for this zone
    try:
        series = get_rainfall_series(zid)
        rain_24h = series.observed_daily_mm.d0
        rain_3d = (
            series.observed_daily_mm.d_minus_2
            + series.observed_daily_mm.d_minus_1
            + series.observed_daily_mm.d0
        )
        obs_rain_prov = getattr(series, "observed_provenance", "SAMPLE_MOCK")
    except Exception:
        # Fallback to properties if series not available
        rain_24h = float(p.get("rain_24h", 0.0))
        rain_3d = float(p.get("rain_3d", 0.0))
        obs_rain_prov = "SAMPLE_MOCK"

    sw_val = float(p.get("soil_wetness_index") if "soil_wetness_index" in p else p.get("soil_moisture", 0.3))

    # Phase 7: terrain from REAL_DEM via terrain_loader
    from services.terrain_loader import get_zone_terrain
    terrain = get_zone_terrain(zid)
    if terrain:
        slope = float(terrain["mean_slope_deg"])
        elevation = float(terrain["mean_elevation_m"])
    else:
        slope = float(p.get("slope", 0.0))
        elevation = float(p.get("elevation", 0.0)) if "elevation" in p else None

    scoring_props = {
        "zone_id": zid,
        "slope": slope,
        "elevation": elevation,
        "rain_24h": rain_24h,
        "rain_3d": rain_3d,
        "soil_wetness_index": sw_val,
        "observed_rainfall_provenance": obs_rain_prov,
        "forecast_rainfall_provenance": "SAMPLE_MOCK",
    }

    res = compute_zone_risk(scoring_props)

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

    # Retrieve provenance attached by compute_zone_risk
    provenance = getattr(res, "feature_provenance", None) or {
        "slope": "REAL_DEM" if terrain else "SAMPLE_MOCK",
        "elevation": "REAL_DEM" if terrain else "SAMPLE_MOCK",
        "rainfall": "SAMPLE_MOCK",
        "soil_wetness": "SAMPLE_MOCK",
    }
    used_slope = getattr(res, "used_slope_deg", slope)
    used_elev = getattr(res, "used_elevation_m", elevation)

    return ZoneRisk(
        zone_id=zid,
        risk_category=res.risk_category,
        risk_score=res.score,
        score=res.score,
        score_type=res.score_type,
        is_probability=res.is_probability,
        is_calibrated=res.is_calibrated,
        computed_by=res.computed_by,
        slope=used_slope,
        elevation=used_elev if used_elev is not None else 0.0,
        soil_moisture=sw_val,
        soil_wetness_index=sw_val,
        rain_24h=rain_24h,
        rain_3d=rain_3d,
        rain_7d=float(p.get("rain_7d", 0.0)) if "rain_7d" in p else None,
        normalized_features=normalized_features,
        contributors=contributors,
        feature_provenance=provenance,
        data_meta=DataMeta(
            data_type="SAMPLE_MOCK",
            source="TerraSense Prototype Scorer — terrain: Copernicus GLO-30 REAL_DEM; rainfall: SAMPLE_MOCK",
            is_live=False,
            note="Slope and elevation from real 30 m DEM. Rainfall and soil wetness remain SAMPLE_MOCK.",
        ),
    )


def _props_to_forecast(p: dict) -> ZoneForecastResponse:
    # Compute 4-horizon risk outlook dynamically
    outlook = compute_zone_risk_outlook(p)

    def _horizon_to_schema(h: ForecastHorizonResult) -> HorizonWindowSchema:
        contribs = [
            ContributorSchema(
                feature=c["display_name"],
                contribution=round(c["contribution"], 4),
                component=c.get("component"),
                display_name=c.get("display_name"),
                normalized_input=round(c["normalized_input"], 4) if "normalized_input" in c else None,
                weight=c.get("weight"),
            )
            for c in h.contributors
        ]
        return HorizonWindowSchema(
            horizon=h.horizon,
            risk_category=h.risk_category,
            risk=h.risk_category,
            risk_score=round(h.risk_score, 4),
            score=round(h.risk_score, 4),
            mode=h.mode,
            input_data_type=h.input_data_type,
            score_type=h.score_type,
            is_probability=h.is_probability,
            is_calibrated=h.is_calibrated,
            computed_by=h.computed_by,
            recent_24h_rain_mm=h.recent_24h_rain_mm,
            antecedent_3d_rain_mm=h.antecedent_3d_rain_mm,
            antecedent_rain_mm=h.antecedent_3d_rain_mm,
            forecast_interval_rain_mm=h.forecast_interval_rain_mm,
            normalized_features=h.normalized_features,
            contributors=contribs,
        )

    now_win = _horizon_to_schema(outlook.now)
    h24_win = _horizon_to_schema(outlook.h24)
    h48_win = _horizon_to_schema(outlook.h48)
    h72_win = _horizon_to_schema(outlook.h72)

    windows = {
        "now": now_win,
        "24h": h24_win,
        "48h": h48_win,
        "72h": h72_win,
    }

    forecast = {
        "24h": h24_win,
        "48h": h48_win,
        "72h": h72_win,
    }

    return ZoneForecastResponse(
        zone_id=outlook.zone_id,
        current=outlook.now.risk_category,
        current_score=round(outlook.now.risk_score, 4),
        windows=windows,
        now=now_win,
        forecast=forecast,
        risk_change_summary=outlook.risk_change_summary,
        transition_details=outlook.transition_details,
        data_meta=DataMeta(
            data_type="SAMPLE_MOCK",
            source="TerraSense Prototype Scorer — terrain: Copernicus GLO-30 REAL_DEM; rainfall: SAMPLE_MOCK",
            is_live=False,
            note=_OUTLOOK_NOTE,
        ),
        feature_provenance=outlook.feature_provenance,
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
            source="TerraSense Prototype Scorer (Canonical SAMPLE_MOCK inputs)",
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
    Returns weather-linked landslide-risk outlook:
    NOW, +24h, +48h, and +72h are ALL computed dynamically by prototype scorer
    using rolling antecedent rainfall accumulation.
    """
    props = get_zone_props(zone_id)
    if props is None:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zone_id.upper()}' not found. Valid IDs are A01–E05.",
        )
    return _props_to_forecast(props)
