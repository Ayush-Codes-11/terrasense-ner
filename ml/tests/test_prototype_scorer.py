"""
Tests for ml/prototype_scorer.py

All tests use the scorer's public API (score_zone) and config values.
They verify algorithmic properties, not specific numeric outputs,
so they remain valid if config parameters are tuned.
"""
import math
import sys
from pathlib import Path

import pytest

# Add repo root to path so ml package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.prototype_scorer import score_zone, RiskResult
from ml.scorer_config import THRESHOLDS, WEIGHTS


# ── Helper ────────────────────────────────────────────────────────────────────

def baseline() -> RiskResult:
    """Moderate-risk baseline zone for parameterised tests."""
    return score_zone(slope_deg=25, rain_24h_mm=20, rain_3d_mm=60, soil_moisture=0.40)


# ── 1. Score always within [0, 1] ─────────────────────────────────────────────

def test_score_bounds_normal():
    r = baseline()
    assert 0.0 <= r.score <= 1.0


def test_score_bounds_zero_inputs():
    r = score_zone(slope_deg=0, rain_24h_mm=0, rain_3d_mm=0, soil_moisture=0.0)
    assert r.score == 0.0


def test_score_bounds_max_inputs():
    r = score_zone(slope_deg=999, rain_24h_mm=9999, rain_3d_mm=9999, soil_moisture=1.0)
    assert r.score == 1.0


def test_score_no_nan_on_zeros():
    r = score_zone(slope_deg=0, rain_24h_mm=0, rain_3d_mm=0, soil_moisture=0.0)
    assert not math.isnan(r.score)


# ── 2. Deterministic ──────────────────────────────────────────────────────────

def test_deterministic():
    r1 = score_zone(30, 30, 90, 0.5)
    r2 = score_zone(30, 30, 90, 0.5)
    assert r1.score == r2.score
    assert r1.risk_category == r2.risk_category


# ── 3. Monotone: increasing rain_24h never decreases score ────────────────────

@pytest.mark.parametrize("rain_24h_low, rain_24h_high", [
    (0, 1), (5, 20), (20, 70), (70, 200),
])
def test_monotone_rain_24h(rain_24h_low, rain_24h_high):
    r_low  = score_zone(25, rain_24h_low,  60, 0.4)
    r_high = score_zone(25, rain_24h_high, 60, 0.4)
    assert r_high.score >= r_low.score, (
        f"score decreased when rain_24h went {rain_24h_low}→{rain_24h_high}: "
        f"{r_low.score:.4f} → {r_high.score:.4f}"
    )


# ── 4. Monotone: increasing soil_moisture never decreases score ───────────────

@pytest.mark.parametrize("sm_low, sm_high", [
    (0.0, 0.1), (0.2, 0.5), (0.5, 0.9), (0.9, 1.0),
])
def test_monotone_soil_moisture(sm_low, sm_high):
    r_low  = score_zone(25, 20, 60, sm_low)
    r_high = score_zone(25, 20, 60, sm_high)
    assert r_high.score >= r_low.score, (
        f"score decreased when soil_moisture went {sm_low}→{sm_high}: "
        f"{r_low.score:.4f} → {r_high.score:.4f}"
    )


# ── 5. Monotone: increasing slope → increasing terrain component ──────────────

@pytest.mark.parametrize("slope_low, slope_high", [
    (0, 5), (5, 20), (20, 40), (40, 90),
])
def test_monotone_slope_terrain_component(slope_low, slope_high):
    r_low  = score_zone(slope_low,  0, 0, 0.0)
    r_high = score_zone(slope_high, 0, 0, 0.0)
    # With rain=0 and sm=0 the only variable is terrain_component
    assert r_high.terrain_component >= r_low.terrain_component, (
        f"terrain_component decreased when slope went {slope_low}→{slope_high}: "
        f"{r_low.terrain_component:.4f} → {r_high.terrain_component:.4f}"
    )
    assert r_high.score >= r_low.score


# ── 6. Category mapping at boundaries ─────────────────────────────────────────

def test_zero_input_is_low():
    r = score_zone(0, 0, 0, 0)
    assert r.risk_category == "LOW"


def test_max_input_is_very_high():
    r = score_zone(9999, 9999, 9999, 1.0)
    assert r.risk_category == "VERY_HIGH"


@pytest.mark.parametrize("category, low, high", [
    (cat, v[0], v[1]) for cat, v in THRESHOLDS.items()
])
def test_thresholds_cover_score_range(category, low, high):
    """Verify that the expected category appears in THRESHOLDS at all."""
    assert category in THRESHOLDS
    assert low < high or (category == "VERY_HIGH" and high > 1.0)


def test_moderate_band_lower_boundary():
    """Score == 0.25 should be MODERATE (lower bound inclusive)."""
    # Equal normalised inputs of 0.25 each → score = Σ(weight * 0.25) = 0.25
    from ml.scorer_config import FEATURE_REFS
    slope   = 0.25 * FEATURE_REFS["slope_deg"]
    rain24  = 0.25 * FEATURE_REFS["rain_24h_mm"]
    rain3d  = 0.25 * FEATURE_REFS["rain_3d_mm"]
    sm      = 0.25 * FEATURE_REFS["soil_moisture"]
    r = score_zone(slope, rain24, rain3d, sm)
    assert abs(r.score - 0.25) < 1e-6
    assert r.risk_category == "MODERATE"


# ── 7. Input validation & Physical guards ─────────────────────────────────────

def test_nan_input_raises():
    with pytest.raises(ValueError, match="Invalid input"):
        score_zone(float("nan"), 20, 60, 0.4)


def test_inf_input_raises():
    with pytest.raises(ValueError, match="Invalid input"):
        score_zone(25, float("inf"), 60, 0.4)


def test_negative_inf_raises():
    with pytest.raises(ValueError, match="Invalid input"):
        score_zone(25, 20, float("-inf"), 0.4)


def test_negative_slope_raises():
    with pytest.raises(ValueError, match="Physically invalid negative slope"):
        score_zone(-1.0, 20, 60, 0.4)


def test_negative_rain_24h_raises():
    with pytest.raises(ValueError, match="Physically invalid negative rainfall"):
        score_zone(25, -0.5, 60, 0.4)


def test_negative_rain_3d_raises():
    with pytest.raises(ValueError, match="Physically invalid negative rainfall"):
        score_zone(25, 20, -5.0, 0.4)


def test_soil_wetness_negative_raises():
    with pytest.raises(ValueError, match="Physically invalid soil wetness index"):
        score_zone(25, 20, 60, -0.05)


def test_soil_wetness_greater_than_one_raises():
    with pytest.raises(ValueError, match="Physically invalid soil wetness index"):
        score_zone(25, 20, 60, 1.05)


def test_missing_slope_raises():
    with pytest.raises(ValueError, match="Missing required scoring input"):
        score_zone(None, 20, 60, 0.4)


def test_missing_rain_24h_raises():
    with pytest.raises(ValueError, match="Missing required scoring input"):
        score_zone(25, None, 60, 0.4)


def test_missing_rain_3d_raises():
    with pytest.raises(ValueError, match="Missing required scoring input"):
        score_zone(25, 20, None, 0.4)


def test_missing_soil_wetness_raises():
    with pytest.raises(ValueError, match="Missing required scoring input"):
        score_zone(25, 20, 60, None)


def test_nested_normalized_features_object():
    """Verify normalized_features is nested and represents normalized inputs, not weighted contributions."""
    r = score_zone(20, 35, 75, 0.5)
    nf = r.normalized_features
    assert nf is not None
    # slope: 20 / 40.0 = 0.5
    assert abs(nf.terrain - 0.5) < 1e-4
    # rain_24h: 35 / 70.0 = 0.5
    assert abs(nf.recent_rainfall - 0.5) < 1e-4
    # rain_3d: 75 / 150.0 = 0.5
    assert abs(nf.antecedent_rainfall - 0.5) < 1e-4
    # soil wetness: 0.5 / 1.0 = 0.5
    assert abs(nf.soil_wetness - 0.5) < 1e-4

    # Verify contributors hold the actual weighted contribution (weight * normalized_input)
    terrain_contrib = next(c for c in r.contributors if c.component == "terrain")
    assert abs(terrain_contrib.contribution - (WEIGHTS["terrain"] * 0.5)) < 1e-4

    # Backward compatibility properties match normalized_features
    assert r.terrain_component == nf.terrain
    assert r.recent_rainfall_component == nf.recent_rainfall
    assert r.antecedent_rainfall_component == nf.antecedent_rainfall
    assert r.soil_wetness_component == nf.soil_wetness


def test_soil_wetness_index_naming():
    """Verify both soil_wetness_index and soil_moisture keyword arguments work identically."""
    r1 = score_zone(slope_deg=25, rain_24h_mm=20, rain_3d_mm=60, soil_wetness_index=0.45)
    r2 = score_zone(slope_deg=25, rain_24h_mm=20, rain_3d_mm=60, soil_moisture=0.45)
    assert r1.score == r2.score
    assert r1.normalized_features.soil_wetness == r2.normalized_features.soil_wetness


# ── 8. Precomputed risk_score is NOT an input ──────────────────────────────────

def test_precomputed_score_not_accepted():
    """score_zone() must not accept risk_score as a parameter."""
    import inspect
    sig = inspect.signature(score_zone)
    assert "risk_score" not in sig.parameters, (
        "score_zone must never accept precomputed 'risk_score' as input. "
        "Using GeoJSON precomputed values would leak them into the calculation."
    )

def test_precomputed_category_not_accepted():
    """score_zone() must not accept risk_category as a parameter."""
    import inspect
    sig = inspect.signature(score_zone)
    assert "risk_category" not in sig.parameters


# ── 9. Contributors ────────────────────────────────────────────────────────────

def test_contributors_count():
    r = baseline()
    assert len(r.contributors) == len(WEIGHTS)


def test_contributors_sorted_descending():
    r = score_zone(42, 48, 125, 0.62)  # high risk zone (C03-like)
    contribs = [c.contribution for c in r.contributors]
    assert contribs == sorted(contribs, reverse=True)


def test_contributors_sum_equals_score():
    r = baseline()
    total = sum(c.contribution for c in r.contributors)
    assert abs(total - r.score) < 1e-3


def test_contributor_fields_complete():
    r = baseline()
    for c in r.contributors:
        assert c.component
        assert c.feature
        assert c.display_name
        assert 0.0 <= c.normalized_input <= 1.0
        assert 0.0 <= c.contribution <= c.weight + 1e-9


# ── 10. Score semantics ────────────────────────────────────────────────────────

def test_is_not_probability():
    r = baseline()
    assert r.is_probability is False


def test_is_not_calibrated():
    r = baseline()
    assert r.is_calibrated is False


def test_score_type_string():
    r = baseline()
    assert "prototype" in r.score_type.lower()


# ── 11. Elevation not used as risk input ──────────────────────────────────────

def test_elevation_not_used():
    """Passing different elevation values must not change the score."""
    r1 = score_zone(25, 20, 60, 0.4, elevation_m=500)
    r2 = score_zone(25, 20, 60, 0.4, elevation_m=2000)
    assert r1.score == r2.score, (
        "Elevation must not affect the prototype score. "
        "It is passed through as metadata only."
    )


# ── 12. C03-like zone (worst case in sample data) ────────────────────────────

def test_c03_like_is_very_high():
    """Zone C03 (slope=42, rain_24h=48, rain_3d=125, sm=0.62) should be VERY_HIGH."""
    r = score_zone(slope_deg=42, rain_24h_mm=48, rain_3d_mm=125, soil_moisture=0.62)
    assert r.risk_category == "VERY_HIGH"
    assert r.score >= 0.75


def test_low_risk_zone_is_low():
    """Zone A01-like (slope=12, rain_24h=5, rain_3d=18, sm=0.25) should be LOW."""
    r = score_zone(slope_deg=12, rain_24h_mm=5, rain_3d_mm=18, soil_moisture=0.25)
    assert r.risk_category == "LOW"
    assert r.score < 0.25
