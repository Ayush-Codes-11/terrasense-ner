"""
scorer_config.py — Single source of all prototype scorer parameters.

══════════════════════════════════════════════════════════════════════
⚠  THESE ARE HEURISTIC DEMO PARAMETERS, NOT SCIENTIFIC OR GOVERNMENT
   THRESHOLDS. They have not been validated against real landslide
   inventories and must not be used for operational decision-making.
   
   The 40°, 70 mm, and 150 mm values are strictly prototype normalization
   denominators used to scale features onto [0.0, 1.0]. They are NOT
   operational alert thresholds, severe rainfall triggers, or saturation
   limits.
══════════════════════════════════════════════════════════════════════

Modifying these values changes the scoring without touching scorer logic.
Phase 4 replaces all precomputed GeoJSON risk_score values with these.
A future XGBoost/trained-model phase replaces this module entirely.
"""

# ── Prototype Normalization Reference Values ─────────────────────────────────
# ⚠ HEURISTIC DEMO PARAMETERS ONLY.
# These values are strictly normalization denominators for scaling features to [0.0, 1.0].
# They are NOT warning thresholds, NOT operational alert levels, and NOT
# scientifically validated critical landslide rainfall or saturation limits.
#
# Scaling formula: normalized_feature = min(raw_value / REFERENCE, 1.0)
# All raw inputs must be >= 0 (and soil wetness must be within [0.0, 1.0]).

PROTOTYPE_NORMALIZATION_REFS: dict[str, float] = {
    "slope_deg": 40.0,           # prototype normalization reference (degrees)
    "rain_24h_mm": 70.0,         # prototype normalization reference (mm)
    "rain_3d_mm": 150.0,         # prototype normalization reference (mm)
    # SAMPLE_MOCK normalized soil-wetness index [0.0, 1.0] (not a real SMAP measurement)
    "soil_wetness_index": 1.0,
    "soil_moisture": 1.0,        # backward-compatibility alias
}

# Backward compatibility alias
FEATURE_REFS = PROTOTYPE_NORMALIZATION_REFS

# ── Component weights ─────────────────────────────────────────────────────────
# Must sum to 1.0. If you add a new component, adjust the others accordingly.

WEIGHTS: dict[str, float] = {
    "terrain":              0.25,
    "recent_rainfall":      0.30,
    "antecedent_rainfall":  0.30,
    "soil_wetness":         0.15,
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "WEIGHTS must sum to 1.0"

# ── Classification bands ──────────────────────────────────────────────────────
# (lower_inclusive, upper_exclusive) – the highest band is [0.75, 1.0].
# These are demo classification bands, not validated operational thresholds.

THRESHOLDS: dict[str, tuple[float, float]] = {
    "LOW":       (0.00, 0.25),
    "MODERATE":  (0.25, 0.50),
    "HIGH":      (0.50, 0.75),
    "VERY_HIGH": (0.75, 1.01),   # upper bound > 1 so score=1.0 maps to VERY_HIGH
}

# ── Score semantics ───────────────────────────────────────────────────────────
# These constants are embedded in every API response so consumers know what
# the number represents. Do NOT change IS_PROBABILITY to True unless the
# model has been formally calibrated.

SCORE_TYPE      = "prototype_relative_risk_score"
IS_PROBABILITY  = False   # 0.84 ≠ "84% chance of landslide"
IS_CALIBRATED   = False   # no validation against real inventories yet
COMPUTED_BY     = "prototype_scorer_v1"

# ── Human-readable component labels ──────────────────────────────────────────

COMPONENT_LABELS: dict[str, str] = {
    "terrain":              "Terrain slope",
    "recent_rainfall":      "Recent 24h rainfall",
    "antecedent_rainfall":  "3-day antecedent rainfall",
    "soil_wetness":         "Soil wetness index",
}
