"""
Tests for Phase 5:
  - Canonical rainfall adapter (backend/services/rainfall.py)
  - Rolling 3-day rainfall accumulator (backend/services/rainfall_accumulator.py)
  - 4-horizon risk forecast engine (backend/services/risk_forecast.py)
  - Endpoint verification for /risk/forecast/{zone_id} and /weather/{zone_id}
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from backend.main import app
from backend.services.rainfall import get_rainfall_series, RainfallSeries, ObservedRainfall, ForecastIntervalRainfall
from backend.services.rainfall_accumulator import calculate_rolling_accumulation
from backend.services.risk_forecast import compute_zone_risk_outlook
from ml.prototype_scorer import score_zone

client = TestClient(app)


# ── 1-5: Rolling Accumulation Rules & Double-Counting ──────────────────────────

def test_rolling_now_accumulation():
    """NOW: recent_24h = D0, antecedent_3d = D-2 + D-1 + D0"""
    r = calculate_rolling_accumulation(d_minus_2=10.0, d_minus_1=20.0, d0=30.0, f1=15.0, f2=25.0, f3=5.0)
    assert r.now.recent_24h_mm == 30.0
    assert r.now.antecedent_3d_mm == 60.0  # 10 + 20 + 30
    assert r.now.forecast_interval_rain_mm is None


def test_rolling_24h_drops_d_minus_2():
    """+24h: D-2 drops out, F1 enters -> D-1 + D0 + F1"""
    r = calculate_rolling_accumulation(d_minus_2=10.0, d_minus_1=20.0, d0=30.0, f1=15.0, f2=25.0, f3=5.0)
    assert r.h24.recent_24h_mm == 15.0  # F1
    assert r.h24.antecedent_3d_mm == 65.0  # 20 + 30 + 15 (10 dropped)
    assert r.h24.forecast_interval_rain_mm == 15.0


def test_rolling_48h_drops_d_minus_1():
    """+48h: D-1 drops out, F2 enters -> D0 + F1 + F2"""
    r = calculate_rolling_accumulation(d_minus_2=10.0, d_minus_1=20.0, d0=30.0, f1=15.0, f2=25.0, f3=5.0)
    assert r.h48.recent_24h_mm == 25.0  # F2
    assert r.h48.antecedent_3d_mm == 70.0  # 30 + 15 + 25 (20 dropped)
    assert r.h48.forecast_interval_rain_mm == 25.0


def test_rolling_72h_drops_d0():
    """+72h: D0 drops out, F3 enters -> F1 + F2 + F3"""
    r = calculate_rolling_accumulation(d_minus_2=10.0, d_minus_1=20.0, d0=30.0, f1=15.0, f2=25.0, f3=5.0)
    assert r.h72.recent_24h_mm == 5.0  # F3
    assert r.h72.antecedent_3d_mm == 45.0  # 15 + 25 + 5 (30 dropped)
    assert r.h72.forecast_interval_rain_mm == 5.0


def test_no_double_counting():
    """Confirm total rain accounted in any 3d window equals exactly the sum of its 3 individual days."""
    d_minus_2, d_minus_1, d0, f1, f2, f3 = 12.0, 18.0, 24.0, 30.0, 14.0, 8.0
    r = calculate_rolling_accumulation(d_minus_2, d_minus_1, d0, f1, f2, f3)
    assert r.now.antecedent_3d_mm == d_minus_2 + d_minus_1 + d0
    assert r.h24.antecedent_3d_mm == d_minus_1 + d0 + f1
    assert r.h48.antecedent_3d_mm == d0 + f1 + f2
    assert r.h72.antecedent_3d_mm == f1 + f2 + f3


# ── 6: Determinism ─────────────────────────────────────────────────────────────

def test_forecast_deterministic():
    zone_props = {"zone_id": "C03", "slope": 42.0, "soil_wetness_index": 0.62}
    out1 = compute_zone_risk_outlook(zone_props)
    out2 = compute_zone_risk_outlook(zone_props)
    assert out1.now.risk_score == out2.now.risk_score
    assert out1.h24.risk_score == out2.h24.risk_score
    assert out1.h48.risk_score == out2.h48.risk_score
    assert out1.h72.risk_score == out2.h72.risk_score
    assert out1.risk_change_summary == out2.risk_change_summary


# ── 7-9: Monotonicity with Future Rainfall ────────────────────────────────────

def test_increasing_f1_cannot_reduce_24h_score():
    base_props = {"zone_id": "C03", "slope": 30.0, "soil_wetness_index": 0.4}
    s_low = RainfallSeries(
        zone_id="C03",
        observed_daily_mm=ObservedRainfall(10, 15, 20),
        forecast_interval_mm=ForecastIntervalRainfall(10.0, 20.0, 10.0),
        data_type="SAMPLE_MOCK", is_live=False, source="test", note="test",
    )
    s_high = RainfallSeries(
        zone_id="C03",
        observed_daily_mm=ObservedRainfall(10, 15, 20),
        forecast_interval_mm=ForecastIntervalRainfall(60.0, 20.0, 10.0),
        data_type="SAMPLE_MOCK", is_live=False, source="test", note="test",
    )
    out_low = compute_zone_risk_outlook(base_props, s_low)
    out_high = compute_zone_risk_outlook(base_props, s_high)
    assert out_high.h24.risk_score >= out_low.h24.risk_score


def test_increasing_f2_cannot_reduce_48h_score():
    base_props = {"zone_id": "C03", "slope": 30.0, "soil_wetness_index": 0.4}
    s_low = RainfallSeries(
        zone_id="C03",
        observed_daily_mm=ObservedRainfall(10, 15, 20),
        forecast_interval_mm=ForecastIntervalRainfall(20.0, 10.0, 10.0),
        data_type="SAMPLE_MOCK", is_live=False, source="test", note="test",
    )
    s_high = RainfallSeries(
        zone_id="C03",
        observed_daily_mm=ObservedRainfall(10, 15, 20),
        forecast_interval_mm=ForecastIntervalRainfall(20.0, 60.0, 10.0),
        data_type="SAMPLE_MOCK", is_live=False, source="test", note="test",
    )
    out_low = compute_zone_risk_outlook(base_props, s_low)
    out_high = compute_zone_risk_outlook(base_props, s_high)
    assert out_high.h48.risk_score >= out_low.h48.risk_score


def test_increasing_f3_cannot_reduce_72h_score():
    base_props = {"zone_id": "C03", "slope": 30.0, "soil_wetness_index": 0.4}
    s_low = RainfallSeries(
        zone_id="C03",
        observed_daily_mm=ObservedRainfall(10, 15, 20),
        forecast_interval_mm=ForecastIntervalRainfall(20.0, 20.0, 5.0),
        data_type="SAMPLE_MOCK", is_live=False, source="test", note="test",
    )
    s_high = RainfallSeries(
        zone_id="C03",
        observed_daily_mm=ObservedRainfall(10, 15, 20),
        forecast_interval_mm=ForecastIntervalRainfall(20.0, 20.0, 55.0),
        data_type="SAMPLE_MOCK", is_live=False, source="test", note="test",
    )
    out_low = compute_zone_risk_outlook(base_props, s_low)
    out_high = compute_zone_risk_outlook(base_props, s_high)
    assert out_high.h72.risk_score >= out_low.h72.risk_score


# ── 10-11: Negative & Missing Input Guards ─────────────────────────────────────

def test_negative_forecast_rainfall_rejected():
    with pytest.raises(ValueError, match="Physically invalid negative rainfall"):
        calculate_rolling_accumulation(10, 10, 10, -5.0, 10, 10)


def test_missing_rainfall_input_rejected():
    with pytest.raises(ValueError, match="Missing required rainfall input"):
        calculate_rolling_accumulation(10, None, 10, 10, 10, 10)


# ── 12-14: Score Bounds & Semantics across All Horizons ────────────────────────

def test_all_horizons_in_bounds_and_computed():
    zone_props = {"zone_id": "C03", "slope": 42.0, "soil_wetness_index": 0.62}
    out = compute_zone_risk_outlook(zone_props)
    for h in [out.now, out.h24, out.h48, out.h72]:
        assert 0.0 <= h.risk_score <= 1.0
        assert h.is_probability is False
        assert h.is_calibrated is False
        assert h.score_type == "prototype_relative_risk_score"
        assert h.mode == "PROTOTYPE_COMPUTED"
        assert h.risk_category in ["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
        assert len(h.contributors) == 4
        assert "terrain" in h.normalized_features


# ── 15: Legacy Mock Fields Have Zero Effect ────────────────────────────────────

def test_legacy_forecast_fields_have_no_effect():
    """Injecting old mock forecast properties must have no effect on calculated outlook."""
    p1 = {"zone_id": "C03", "slope": 42.0, "soil_wetness_index": 0.62}
    p2 = {
        "zone_id": "C03", "slope": 42.0, "soil_wetness_index": 0.62,
        "forecast_risk_24h": "LOW",
        "forecast_score_24h": 0.01,
        "forecast_risk_48h": "LOW",
        "forecast_score_48h": 0.01,
        "forecast_risk_72h": "LOW",
        "forecast_score_72h": 0.01,
    }
    out1 = compute_zone_risk_outlook(p1)
    out2 = compute_zone_risk_outlook(p2)
    assert out1.h24.risk_score == out2.h24.risk_score
    assert out1.h48.risk_score == out2.h48.risk_score
    assert out1.h72.risk_score == out2.h72.risk_score


# ── 16: Consistency of NOW Horizon with Direct Scorer ─────────────────────────

def test_now_horizon_matches_direct_scorer():
    """The NOW horizon from compute_zone_risk_outlook must match direct score_zone call."""
    zone_props = {"zone_id": "C03", "slope": 42.0, "soil_wetness_index": 0.62}
    series = get_rainfall_series("C03")
    direct_res = score_zone(
        slope_deg=42.0,
        rain_24h_mm=series.observed_daily_mm.d0,
        rain_3d_mm=series.observed_daily_mm.d_minus_2 + series.observed_daily_mm.d_minus_1 + series.observed_daily_mm.d0,
        soil_wetness_index=0.62,
    )
    outlook = compute_zone_risk_outlook(zone_props, series)
    assert outlook.now.risk_score == direct_res.score
    assert outlook.now.risk_category == direct_res.risk_category


# ── Endpoint Verification ──────────────────────────────────────────────────────

def test_endpoint_risk_forecast_c03():
    res = client.get("/risk/forecast/C03")
    assert res.status_code == 200
    data = res.json()
    assert data["zone_id"] == "C03"

    # All 4 windows are PROTOTYPE_COMPUTED
    for w_key in ["now", "24h", "48h", "72h"]:
        w = data["windows"][w_key]
        assert w["mode"] == "PROTOTYPE_COMPUTED"
        assert w["is_probability"] is False
        assert 0.0 <= w["risk_score"] <= 1.0
        assert "recent_24h_rain_mm" in w
        assert "antecedent_3d_rain_mm" in w

    # Check deterministic transition explanation
    assert "risk_change_summary" in data
    assert len(data["transition_details"]) >= 2

    # Verify C03 demo scenario progression: NOW (HIGH) -> +24h (VERY_HIGH) -> +48h (VERY_HIGH) -> +72h (HIGH)
    assert data["windows"]["now"]["risk_category"] == "HIGH"
    assert data["windows"]["24h"]["risk_category"] == "VERY_HIGH"
    assert data["windows"]["48h"]["risk_category"] == "VERY_HIGH"
    assert data["windows"]["72h"]["risk_category"] == "HIGH"


def test_endpoint_weather_c03():
    res = client.get("/weather/C03")
    assert res.status_code == 200
    data = res.json()
    assert data["zone_id"] == "C03"
    assert data["observed_daily_mm"]["d0"] == 32.0
    assert data["forecast_interval_mm"]["0_24h"] == 65.0
    assert data["rolling_3d_accumulation_mm"]["now"] == 87.0
    assert data["rolling_3d_accumulation_mm"]["24h"] == 127.0
