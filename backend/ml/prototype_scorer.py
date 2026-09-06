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
Outputs: RiskResult with score, category, per-component contributions,
         and nested normalized_features.

Design goals:
  • Fully transparent — every component is individually inspectable
  • Monotone — increasing any valid hazard input never decreases the score
  • Validated inputs — physically invalid values (negative rain, negative slope,
    soil wetness outside [0, 1]) are strictly rejected with ValueError,
    never silently clamped.
  • No pre-computed risk_score values from GeoJSON are used as inputs
  • A future model (XGBoost/trained) replaces this module without
    changing the backend API or frontend components
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from ml.scorer_config import (
    COMPONENT_LABELS,
    COMPUTED_BY,
    IS_CALIBRATED,
    IS_PROBABILITY,
    PROTOTYPE_NORMALIZATION_REFS,
    SCORE_TYPE,
    THRESHOLDS,
    WEIGHTS,
)


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class NormalizedFeatures:
    """
    Normalized feature inputs in range [0.0, 1.0].
    These represent scaled physical inputs (value / reference, capped at 1.0),
    NOT the final weighted contributions.
    """
    terrain: float
    recent_rainfall: float
    antecedent_rainfall: float
    soil_wetness: float


@dataclass
class Contributor:
    """Per-component contribution to the final prototype score."""
    component: str           # internal key, e.g. "terrain"
    feature: str             # human-readable input name, e.g. "slope (42.0°)"
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

    # Nested normalized inputs (not weighted contributions)
    normalized_features: NormalizedFeatures

    # Sorted by absolute contribution descending (for WhyNow card)
    contributors: list[Contributor] = field(default_factory=list)

    # Optional metadata passed through (not used in scoring)
    elevation_m: Optional[float] = None
    rain_7d_mm: Optional[float] = None

    # Backward compatibility properties
    @property
    def terrain_component(self) -> float:
        return self.normalized_features.terrain

    @property
    def recent_rainfall_component(self) -> float:
        return self.normalized_features.recent_rainfall

    @property
    def antecedent_rainfall_component(self) -> float:
        return self.normalized_features.antecedent_rainfall

    @property
    def soil_wetness_component(self) -> float:
        return self.normalized_features.soil_wetness


# ── Private helpers ────────────────────────────────────────────────────────────

def _normalize(value: float, reference: float) -> float:
    """Divide value by reference, capped at 1.0. Assumes value >= 0 and reference > 0."""
    if reference <= 0:
        raise ValueError(f"reference must be > 0, got {reference}")
    return min(value / reference, 1.0)


def _categorise(score: float) -> str:
    """Map score to risk category using THRESHOLDS from config."""
    for category, (low, high) in THRESHOLDS.items():
        if low <= score < high:
            return category
    return "VERY_HIGH"


# ── Public API ────────────────────────────────────────────────────────────────

def score_zone(
    slope_deg: float,
    rain_24h_mm: float,
    rain_3d_mm: float,
    soil_wetness_index: Optional[float] = None,
    soil_moisture: Optional[float] = None,
    rain_7d_mm: Optional[float] = None,
    elevation_m: Optional[float] = None,
) -> RiskResult:
    """
    Compute prototype risk score for a single zone.

    Parameters
    ----------
    slope_deg          : Terrain slope in degrees (must be >= 0).
    rain_24h_mm        : Observed/sample rainfall in past 24 hours in mm (must be >= 0).
    rain_3d_mm         : Observed/sample 3-day accumulated rainfall in mm (must be >= 0).
    soil_wetness_index : SAMPLE_MOCK normalized soil-wetness index [0.0, 1.0].
                         (Not a real SMAP satellite measurement).
    soil_moisture      : Backward-compatibility alias for soil_wetness_index.
    rain_7d_mm         : Optional 7-day rainfall (mm). Passed through as metadata only.
    elevation_m        : Optional elevation (m). NOT used as a risk factor;
                         passed through as metadata only.

    Returns
    -------
    RiskResult with score, category, normalized_features, and contributors.

    Raises
    ------
    ValueError : If required inputs are missing, non-finite, or physically invalid
                 (e.g., negative slope, negative rainfall, soil wetness outside [0, 1]).
    """
    # ── Missing required input checks ─────────────────────────────────────────
    if slope_deg is None:
        raise ValueError("Missing required scoring input: 'slope_deg'")
    if rain_24h_mm is None:
        raise ValueError("Missing required scoring input: 'rain_24h_mm'")
    if rain_3d_mm is None:
        raise ValueError("Missing required scoring input: 'rain_3d_mm'")

    # Resolve soil_wetness_index parameter / alias
    sw_val = soil_wetness_index if soil_wetness_index is not None else soil_moisture
    if sw_val is None:
        raise ValueError(
            "Missing required scoring input: 'soil_wetness_index' (or 'soil_moisture')"
        )

    # ── Non-finite checks ─────────────────────────────────────────────────────
    inputs = {
        "slope_deg": slope_deg,
        "rain_24h_mm": rain_24h_mm,
        "rain_3d_mm": rain_3d_mm,
        "soil_wetness_index": sw_val,
    }
    for name, val in inputs.items():
        if not math.isfinite(val):
            raise ValueError(
                f"Invalid input '{name}' = {val!r}. "
                "All required inputs must be finite numbers."
            )

    # ── Physical validity checks ──────────────────────────────────────────────
    # Do not silently clamp physically invalid inputs into valid scores!
    if slope_deg < 0.0:
        raise ValueError(f"Physically invalid negative slope: slope_deg={slope_deg} < 0")
    if rain_24h_mm < 0.0:
        raise ValueError(f"Physically invalid negative rainfall: rain_24h_mm={rain_24h_mm} < 0")
    if rain_3d_mm < 0.0:
        raise ValueError(f"Physically invalid negative rainfall: rain_3d_mm={rain_3d_mm} < 0")
    if not (0.0 <= sw_val <= 1.0):
        raise ValueError(
            f"Physically invalid soil wetness index: {sw_val}. "
            "SAMPLE_MOCK soil_wetness_index must be within [0.0, 1.0]."
        )

    # ── Normalise each feature to [0.0, 1.0] ──────────────────────────────────
    terrain_norm = _normalize(slope_deg, PROTOTYPE_NORMALIZATION_REFS["slope_deg"])
    recent_norm = _normalize(rain_24h_mm, PROTOTYPE_NORMALIZATION_REFS["rain_24h_mm"])
    antecedent_norm = _normalize(rain_3d_mm, PROTOTYPE_NORMALIZATION_REFS["rain_3d_mm"])
    soil_norm = _normalize(sw_val, PROTOTYPE_NORMALIZATION_REFS["soil_wetness_index"])

    normalized_features = NormalizedFeatures(
        terrain=round(terrain_norm, 4),
        recent_rainfall=round(recent_norm, 4),
        antecedent_rainfall=round(antecedent_norm, 4),
        soil_wetness=round(soil_norm, 4),
    )

    # ── Weighted sum ──────────────────────────────────────────────────────────
    terrain_contribution = WEIGHTS["terrain"] * terrain_norm
    recent_contribution = WEIGHTS["recent_rainfall"] * recent_norm
    antecedent_contribution = WEIGHTS["antecedent_rainfall"] * antecedent_norm
    soil_contribution = WEIGHTS["soil_wetness"] * soil_norm

    score = (
        terrain_contribution
        + recent_contribution
        + antecedent_contribution
        + soil_contribution
    )
    score = min(max(score, 0.0), 1.0)

    # ── Build contributors list (sorted by contribution descending) ───────────
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
                feature=f"soil_wetness_index ({sw_val:.2f})",
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
        normalized_features=normalized_features,
        contributors=contributors,
        elevation_m=elevation_m,
        rain_7d_mm=rain_7d_mm,
    )
