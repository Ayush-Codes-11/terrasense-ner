"""
risk_forecast.py — 4-horizon weather-linked landslide-risk outlook engine.

═══════════════════════════════════════════════════════════════════════════════
SCIENTIFIC & ARCHITECTURAL DISCIPLINE:
1. TerraSense does NOT predict rainfall itself.
   Input: Observed rainfall (SAMPLE_MOCK) + Forecast rainfall (SAMPLE_MOCK)
          + Static terrain slope contribution + Soil wetness index.
   Output: Weather-linked landslide-risk outlook (NOW, +24h, +48h, +72h).

2. ALL 4 HORIZONS ARE COMPUTED USING THE SAME PROTOTYPE SCORER:
   There are NO separate or fabricated formulas for future horizons.
   Every horizon passes its specific rolling 24h & 3-day rainfall into
   ml.prototype_scorer.score_zone(...).

3. STATIC SOIL WETNESS IN PHASE 5:
   Soil wetness index remains constant across horizons in Phase 5:
   "SAMPLE_MOCK static soil-wetness input for forecast horizons".
   No unverified soil-moisture forecasting model is fabricated.

4. DETERMINISTIC EXPLANATION:
   Risk changes are explained deterministically based on rainfall shifts
   and component contribution deltas, not hallucinated by an LLM.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
for _p in (str(_REPO_ROOT), str(_BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ml.prototype_scorer import score_zone, RiskResult, Contributor
try:
    from services.rainfall import get_rainfall_series, RainfallSeries
    from services.rainfall_accumulator import (
        compute_zone_rolling_rainfall,
        HorizonRainfall,
        RollingAccumulationResult,
    )
    from services.terrain_loader import get_zone_terrain
except ImportError:
    from services.rainfall import get_rainfall_series, RainfallSeries
    from services.rainfall_accumulator import (
        compute_zone_rolling_rainfall,
        HorizonRainfall,
        RollingAccumulationResult,
    )
    from services.terrain_loader import get_zone_terrain


@dataclass
class ForecastHorizonResult:
    horizon: str                       # "now", "24h", "48h", "72h"
    risk_category: str                 # "LOW", "MODERATE", "HIGH", "VERY_HIGH"
    risk_score: float                  # prototype relative risk score [0, 1]
    mode: str                          # "PROTOTYPE_COMPUTED"
    input_data_type: str               # "SAMPLE_MOCK"
    score_type: str                    # "prototype_relative_risk_score"
    is_probability: bool               # False
    is_calibrated: bool                # False
    computed_by: str                   # "prototype_scorer_v1"

    # Rainfall context responsible for this horizon's outcome
    recent_24h_rain_mm: float
    antecedent_3d_rain_mm: float
    forecast_interval_rain_mm: Optional[float]

    # Components & contributors from prototype scorer
    normalized_features: Dict[str, float]
    contributors: List[Dict[str, Any]]


@dataclass
class RiskOutlookResult:
    zone_id: str
    slope_deg: float
    elevation_m: Optional[float]
    soil_wetness_index: float
    soil_wetness_note: str

    now: ForecastHorizonResult
    h24: ForecastHorizonResult
    h48: ForecastHorizonResult
    h72: ForecastHorizonResult

    # Deterministic transition explanation
    risk_change_summary: str
    transition_details: List[str]

    # Feature provenance (Phase 7)
    feature_provenance: Dict[str, str] = field(default_factory=lambda: {
        "slope": "SAMPLE_MOCK",
        "elevation": "SAMPLE_MOCK",
        "rainfall": "SAMPLE_MOCK",
        "soil_wetness": "SAMPLE_MOCK",
    })


def _build_deterministic_explanation(
    now: ForecastHorizonResult,
    h24: ForecastHorizonResult,
    h48: ForecastHorizonResult,
    h72: ForecastHorizonResult,
) -> tuple[str, List[str]]:
    """
    Generates deterministic explanation of risk transitions across horizons
    based on rolling rainfall shifts and contributor deltas.
    """
    details = []

    # 1. NOW to +24h transition
    rain_diff_24 = h24.recent_24h_rain_mm - now.recent_24h_rain_mm
    accum_diff_24 = h24.antecedent_3d_rain_mm - now.antecedent_3d_rain_mm
    f1 = h24.forecast_interval_rain_mm or 0.0

    if now.risk_category != h24.risk_category:
        direction = "escalates" if h24.risk_score > now.risk_score else "eases"
        msg_24 = (
            f"At +24h, risk {direction} from {now.risk_category} ({now.risk_score:.4f}) "
            f"to {h24.risk_category} ({h24.risk_score:.4f}). "
            f"Forecast rainfall of {f1:.1f} mm in the [0–24h] window shifts 3-day rolling accumulation "
            f"from {now.antecedent_3d_rain_mm:.1f} mm to {h24.antecedent_3d_rain_mm:.1f} mm."
        )
    else:
        msg_24 = (
            f"At +24h, risk category remains {now.risk_category} (score: {now.risk_score:.4f} → {h24.risk_score:.4f}) "
            f"with {f1:.1f} mm forecast in the [0–24h] interval."
        )
    details.append(msg_24)

    # 2. +24h to +48h transition
    f2 = h48.forecast_interval_rain_mm or 0.0
    if h24.risk_category != h48.risk_category:
        direction = "further escalates" if h48.risk_score > h24.risk_score else "eases"
        msg_48 = (
            f"At +48h, risk {direction} to {h48.risk_category} ({h48.risk_score:.4f}) "
            f"with {f2:.1f} mm forecast, bringing 3-day accumulation to {h48.antecedent_3d_rain_mm:.1f} mm."
        )
    else:
        msg_48 = (
            f"At +48h, risk category persists at {h24.risk_category} ({h48.risk_score:.4f}) "
            f"as sustained precipitation ({f2:.1f} mm) maintains rolling 3-day accumulation at {h48.antecedent_3d_rain_mm:.1f} mm."
        )
    details.append(msg_48)

    # 3. +48h to +72h transition
    f3 = h72.forecast_interval_rain_mm or 0.0
    if h48.risk_category != h72.risk_category:
        direction = "escalates" if h72.risk_score > h48.risk_score else "moderates"
        msg_72 = (
            f"At +72h, risk {direction} to {h72.risk_category} ({h72.risk_score:.4f}) "
            f"as forecast rainfall reduces to {f3:.1f} mm, allowing older heavy rainfall to roll out of the 3-day window."
        )
    else:
        msg_72 = (
            f"At +72h, risk category remains {h48.risk_category} ({h72.risk_score:.4f}) "
            f"with {f3:.1f} mm forecast and 3-day antecedent total of {h72.antecedent_3d_rain_mm:.1f} mm."
        )
    details.append(msg_72)

    # Summary sentence
    peak_score = max(now.risk_score, h24.risk_score, h48.risk_score, h72.risk_score)
    peak_horizon = (
        "NOW" if peak_score == now.risk_score else
        "+24h" if peak_score == h24.risk_score else
        "+48h" if peak_score == h48.risk_score else "+72h"
    )
    summary = (
        f"Peak relative risk outlook occurs at {peak_horizon} (score {peak_score:.4f}), "
        f"driven by rolling antecedent rainfall accumulation and terrain slope contribution."
    )

    return summary, details


def compute_zone_risk_outlook(
    zone_props: Dict[str, Any],
    rainfall_series: Optional[RainfallSeries] = None,
) -> RiskOutlookResult:
    """
    Computes a complete 4-horizon weather-linked landslide-risk outlook.

    Phase 7: slope and elevation are read from the Copernicus GLO-30 REAL_DEM
    terrain_loader. GeoJSON zone_props are used only as fallback.

    Parameters
    ----------
    zone_props       : Static zone properties (soil moisture, rainfall).
    rainfall_series  : Optional pre-loaded RainfallSeries. If omitted, loaded from canonical service.

    Returns
    -------
    RiskOutlookResult with NOW, +24h, +48h, +72h all computed by prototype scorer.
    """
    zid = str(zone_props["zone_id"]).upper()

    # ── Terrain: prefer REAL_DEM, fall back to GeoJSON props ──
    terrain = get_zone_terrain(zid)
    if terrain:
        slope = float(terrain["mean_slope_deg"])
        elevation = float(terrain["mean_elevation_m"])
        slope_provenance = "REAL_DEM"
        elev_provenance = "REAL_DEM"
    else:
        slope = float(zone_props.get("slope", 0.0))
        elevation = float(zone_props.get("elevation", 0.0)) if "elevation" in zone_props else None
        slope_provenance = "SAMPLE_MOCK"
        elev_provenance = "SAMPLE_MOCK"

    # Soil wetness index: constant across horizons (SAMPLE_MOCK, not SMAP)
    sw = (
        zone_props.get("soil_wetness_index")
        if "soil_wetness_index" in zone_props
        else zone_props.get("soil_moisture", 0.3)
    )
    soil_wetness = float(sw)

    # Obtain canonical rainfall series
    if rainfall_series is None:
        rainfall_series = get_rainfall_series(zid)

    # Compute rolling 3-day accumulation
    rolling = compute_zone_rolling_rainfall(rainfall_series)

    # Score each horizon through the transparent prototype scorer
    horizons_data: list[tuple[str, HorizonRainfall]] = [
        ("now", rolling.now),
        ("24h", rolling.h24),
        ("48h", rolling.h48),
        ("72h", rolling.h72),
    ]

    scored_horizons: list[ForecastHorizonResult] = []
    for h_name, h_rain in horizons_data:
        res: RiskResult = score_zone(
            slope_deg=slope,
            rain_24h_mm=h_rain.recent_24h_mm,
            rain_3d_mm=h_rain.antecedent_3d_mm,
            soil_wetness_index=soil_wetness,
            elevation_m=elevation,
        )

        contribs = [
            {
                "feature": c.display_name,
                "component": c.component,
                "display_name": c.display_name,
                "normalized_input": c.normalized_input,
                "weight": c.weight,
                "contribution": c.contribution,
            }
            for c in res.contributors
        ]

        norm_feat = {
            "terrain": res.normalized_features.terrain,
            "recent_rainfall": res.normalized_features.recent_rainfall,
            "antecedent_rainfall": res.normalized_features.antecedent_rainfall,
            "soil_wetness": res.normalized_features.soil_wetness,
        }

        # Differentiate observed horizon (REAL_GPM or SAMPLE_MOCK) from future mixed horizons
        obs_prov = getattr(rainfall_series, "observed_provenance", "SAMPLE_MOCK")
        horizon_input_type = obs_prov if h_name == "now" else ("MIXED_PROTOTYPE" if obs_prov == "REAL_GPM" else "SAMPLE_MOCK")

        scored_horizons.append(
            ForecastHorizonResult(
                horizon=h_name,
                risk_category=res.risk_category,
                risk_score=res.score,
                mode="PROTOTYPE_COMPUTED",
                input_data_type=horizon_input_type,
                score_type=res.score_type,
                is_probability=res.is_probability,
                is_calibrated=res.is_calibrated,
                computed_by=res.computed_by,
                recent_24h_rain_mm=h_rain.recent_24h_mm,
                antecedent_3d_rain_mm=h_rain.antecedent_3d_mm,
                forecast_interval_rain_mm=h_rain.forecast_interval_rain_mm,
                normalized_features=norm_feat,
                contributors=contribs,
            )
        )

    now_res, h24_res, h48_res, h72_res = scored_horizons
    summary, details = _build_deterministic_explanation(now_res, h24_res, h48_res, h72_res)

    obs_rain_prov = getattr(rainfall_series, "observed_provenance", "SAMPLE_MOCK")
    fcst_rain_prov = getattr(rainfall_series, "forecast_provenance", "SAMPLE_MOCK")

    return RiskOutlookResult(
        zone_id=zid,
        slope_deg=slope,
        elevation_m=elevation,
        soil_wetness_index=soil_wetness,
        soil_wetness_note="SAMPLE_MOCK static soil-wetness input for forecast horizons (not SMAP observation)",
        now=now_res,
        h24=h24_res,
        h48=h48_res,
        h72=h72_res,
        risk_change_summary=summary,
        transition_details=details,
        feature_provenance={
            "slope": slope_provenance,
            "elevation": elev_provenance,
            "observed_rainfall": obs_rain_prov,
            "forecast_rainfall": fcst_rain_prov,
            "soil_wetness": "SAMPLE_MOCK",
            "rainfall": obs_rain_prov,
        },
    )
