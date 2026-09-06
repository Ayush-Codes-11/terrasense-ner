"""
prototype_scorer.py — Transparent weighted prototype risk scorer.

══════════════════════════════════════════════════════════════════════
⚠  NOT A CALIBRATED LANDSLIDE-PROBABILITY MODEL.
   Intended for UI/API testing and algorithm demonstration only.
   "prototype_risk_score = 0.84" means the zone scores 0.84 on
   this relative heuristic scale — it does NOT mean an 84% chance
   of a landslide.
══════════════════════════════════════════════════════════════════════

Inputs:  terrain + rainfall + soil wetness features
Outputs: RiskResult with score, category, per-component contributions

Design goals:
  • Fully transparent — every component is individually inspectable
  • Monotone — increasing any hazard input never decreases the score
  • No pre-computed risk_score values from GeoJSON are used as inputs
  • A future model (XGBoost/trained) replaces this module without
    changing the backend API or frontend components
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ml.scorer_config import (
    COMPONENT_LABELS,
    COMPUTED_BY,
    FEATURE_REFS,
    IS_CALIBRATED,
    IS_PROBABILITY,
    SCORE_TYPE,
    THRESHOLDS,
    WEIGHTS,
)


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class Contributor:
    """Per-component contribution to the final prototype score."""
    component: str           # internal key, e.g. "terrain"
    feature: str             # human-readable input name, e.g. "slope (deg)"
    display_name: str        # label shown in UI, from COMPONENT_LABELS
    normalized_input: float  # raw_value / reference, capped [0, 1]
    weight: float            # from WEIGHTS
    contribution: float      # weight × normalized_input  (also [0, 1])


@dataclass
class RiskResult:
    """Full output of the prototype scorer for one zone."""
    score: float              # prototype_risk_score ∈ [0, 1]
    risk_category: str        # LOW | MODERATE | HIGH | VERY_HIGH
    score_type: str
    is_probability: bool
    is_calibrated: bool
    computed_by: str

    # Transparent component breakdown
    terrain_component: float
    recent_rainfall_component: float
    antecedent_rainfall_component: float
    soil_wetness_component: float

    # Sorted by absolute contribution descending (for WhyNow card)
    contributors: list[Contributor] = field(default_factory=list)

    # Optional metadata passed through (not used in scoring)
    elevation_m: Optional[float] = None
    rain_7d_mm: Optional[float] = None


# ── Private helpers ────────────────────────────────────────────────────────────

def _normalize(value: float, reference: float) -> float:
    """Divide value by reference, clamp to [0, 1].  reference > 0 assumed."""
    if reference <= 0:
        raise ValueError(f"reference must be > 0, got {reference}")
    return min(max(value / reference, 0.0), 1.0)


def _categorise(score: float) -> str:
    """Map score to risk category using THRESHOLDS from config."""
    for category, (low, high) in THRESHOLDS.items():
        if low <= score < high:
            return category
    # Safety net: should not be reached given THRESHOLDS covers [0, >1)
    return "VERY_HIGH"


# ── Public API ────────────────────────────────────────────────────────────────

def score_zone(
    slope_deg: float,
    rain_24h_mm: float,
    rain_3d_mm: float,
    soil_moisture: float,
    rain_7d_mm: Optional[float] = None,
    elevation_m: Optional[float] = None,
) -> RiskResult:
    """
    Compute prototype risk score for a single zone.

    Parameters
    ----------
    slope_deg       : Terrain slope in degrees.
    rain_24h_mm     : Observed/sample rainfall in past 24 hours (mm).
    rain_3d_mm      : Observed/sample 3-day accumulated rainfall (mm).
    soil_moisture   : Soil wetness index [0, 1].  Any value outside [0, 1]
                      is clamped silently.
    rain_7d_mm      : Optional 7-day rainfall (mm).  Passed through as
                      metadata; not used in this version of the formula.
    elevation_m     : Optional elevation (m).  NOT used as a risk factor —
                      elevation is not a simple monotonic risk predictor.
                      Passed through as metadata only.

    Returns
    -------
    RiskResult with score, category, component breakdown, and contributions.

    Raises
    ------
    ValueError      : If any required numeric input is NaN or non-finite.
    """
    import math

    # ── Input validation ──────────────────────────────────────────────────────
    inputs = {
        "slope_deg": slope_deg,
        "rain_24h_mm": rain_24h_mm,
        "rain_3d_mm": rain_3d_mm,
        "soil_moisture": soil_moisture,
    }
    for name, val in inputs.items():
        if not math.isfinite(val):
            raise ValueError(
                f"Invalid input '{name}' = {val!r}. "
                "All required inputs must be finite numbers."
            )

    # ── Normalise each feature to [0, 1] ─────────────────────────────────────
    terrain_norm   = _normalize(slope_deg,   FEATURE_REFS["slope_deg"])
    recent_norm    = _normalize(rain_24h_mm, FEATURE_REFS["rain_24h_mm"])
    antecedent_norm = _normalize(rain_3d_mm, FEATURE_REFS["rain_3d_mm"])
    soil_norm      = _normalize(soil_moisture, FEATURE_REFS["soil_moisture"])

    # ── Weighted sum ──────────────────────────────────────────────────────────
    # score = Σ (weight_i × normalised_input_i)
    # Monotone property: every normalised input ≥ 0 and weight > 0, so
    # increasing any input strictly increases its component's contribution.
    terrain_contribution   = WEIGHTS["terrain"]             * terrain_norm
    recent_contribution    = WEIGHTS["recent_rainfall"]     * recent_norm
    antecedent_contribution = WEIGHTS["antecedent_rainfall"] * antecedent_norm
    soil_contribution      = WEIGHTS["soil_wetness"]        * soil_norm

    score = (
        terrain_contribution
        + recent_contribution
        + antecedent_contribution
        + soil_contribution
    )
    # Clamp to [0, 1] — should already be in range given weights sum to 1.0
    score = min(max(score, 0.0), 1.0)

    contributors = sorted(
        [
            Contributor(
                component="terrain",
                feature=f"slope ({slope_deg}°)",
                display_name=COMPONENT_LABELS["terrain"],
                normalized_input=round(terrain_norm, 4),
                weight=WEIGHTS["terrain"],
                contribution=round(terrain_contribution, 4),
            ),
            Contributor(
                component="recent_rainfall",
                feature=f"rain_24h ({rain_24h_mm} mm)",
                display_name=COMPONENT_LABELS["recent_rainfall"],
                normalized_input=round(recent_norm, 4),
                weight=WEIGHTS["recent_rainfall"],
                contribution=round(recent_contribution, 4),
            ),
            Contributor(
                component="antecedent_rainfall",
                feature=f"rain_3d ({rain_3d_mm} mm)",
                display_name=COMPONENT_LABELS["antecedent_rainfall"],
                normalized_input=round(antecedent_norm, 4),
                weight=WEIGHTS["antecedent_rainfall"],
                contribution=round(antecedent_contribution, 4),
            ),
            Contributor(
                component="soil_wetness",
                feature=f"soil_moisture ({soil_moisture:.2f})",
                display_name=COMPONENT_LABELS["soil_wetness"],
                normalized_input=round(soil_norm, 4),
                weight=WEIGHTS["soil_wetness"],
                contribution=round(soil_contribution, 4),
            ),
        ],
        key=lambda c: c.contribution,
        reverse=True,
    )

    return RiskResult(
        score=round(score, 4),
        risk_category=_categorise(score),
        score_type=SCORE_TYPE,
        is_probability=IS_PROBABILITY,
        is_calibrated=IS_CALIBRATED,
        computed_by=COMPUTED_BY,
        terrain_component=round(terrain_norm, 4),
        recent_rainfall_component=round(recent_norm, 4),
        antecedent_rainfall_component=round(antecedent_norm, 4),
        soil_wetness_component=round(soil_norm, 4),
        contributors=contributors,
        elevation_m=elevation_m,
        rain_7d_mm=rain_7d_mm,
    )
