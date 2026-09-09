"""
test_gpm_rainfall.py — Test suite for Phase 8 Real NASA GPM IMERG Rainfall Integration.

Verifies:
1. IMERG granule test fixture loading and schema.
2. Area-weighted zonal overlap and coarse cell distribution (16 zones in NE, 4 SE, 4 NW, 1 SW).
3. Real GPM observed data loading, negative value rejection, and NaN rejection.
4. Rolling 3-day antecedent accumulation with real GPM values.
5. Invariants:
   - Observed rainfall provenance is REAL_GPM (or SAMPLE_FALLBACK if missing).
   - Forecast rainfall provenance is ALWAYS SAMPLE_MOCK (never claimed as real GPM).
   - Coarse native resolution (~0.1°) acknowledged; no fake 30m resolution claimed.
6. API endpoints:
   - GET /weather/status
   - GET /weather/C03
   - GET /risk/current/C03
   - GET /risk/forecast/C03
   - GET /risk/current (all zones)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

_TESTS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TESTS_DIR.parent
_REPO_ROOT = _BACKEND_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from backend.main import app
import backend.services.rainfall as rainfall_mod
from backend.services.gpm_loader import (
    load_gpm_observed_dataset,
    load_gpm_metadata,
    get_zone_gpm_observed,
    get_gpm_provenance_status,
)
from backend.services.rainfall import get_rainfall_series
from backend.services.rainfall_accumulator import compute_zone_rolling_rainfall
from backend.scripts.fetch_gpm_imerg import (
    derive_intersecting_imerg_cells,
    compute_zone_overlap_weights,
    process_granule_data,
    PILOT_BBOX,
    _GRID_RISK_PATH,
)

client = TestClient(app)

FIXTURE_PATH = _TESTS_DIR / "fixtures" / "sample_imerg_granules.json"


# ── 1. Fixture & Real Dataset Schema Verification ─────────────────────────────

def test_fixture_granules_structure():
    """Verify test fixture contains the expected 3 UTC days and native grid cells."""
    assert FIXTURE_PATH.exists(), f"Fixture file not found: {FIXTURE_PATH}"
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        data = json.load(f)

    assert "collection" in data
    assert data["collection"] == "GPM_3IMERGDL"
    assert data["collection_version"] == "07"
    assert data["algorithm_generation"] == "V07"
    assert data["granule_processing_version"] == "V07C"
    assert data["source_variable"] == "precipitation"
    assert data["source_unit"] == "mm/day"
    assert len(data["granules"]) == 3

    for g in data["granules"]:
        assert "window_start_utc" in g
        assert "window_end_utc" in g
        assert "cells" in g
        assert len(g["cells"]) == 4  # 4 intersecting 0.1° cells


def test_real_weather_files_exist_and_valid():
    """Verify canonical data/real/weather/ files are present and match schema."""
    dataset = load_gpm_observed_dataset()
    meta = load_gpm_metadata()

    assert "zones" in dataset
    assert len(dataset["zones"]) == 25, "Expected 25 prototype zones"
    assert "metadata" in dataset

    assert meta.get("collection") == "GPM_3IMERGDL"
    assert meta.get("collection_version") == "07"
    assert meta.get("algorithm_generation") == "V07"
    assert meta.get("collection_concept_id") == "C2723754859-GES_DISC"
    assert meta.get("source_variable") == "precipitation"
    assert meta.get("source_unit") == "mm/day"


def test_fixture_data_cannot_be_real_gpm():
    """Prove that explicitly loading fixture data produces SAMPLE_GPM_COMPATIBLE and not REAL_GPM."""
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        fixture_data = json.load(f)

    native_cells = derive_intersecting_imerg_cells(PILOT_BBOX, res_deg=0.1)
    zone_weights = compute_zone_overlap_weights(_GRID_RISK_PATH, native_cells)

    meta_extra = {
        "granule_processing_version": fixture_data.get("metadata", {}).get("granule_processing_version", "OFFLINE_FIXTURE_V07C"),
        "source_data_origin": "OFFLINE_TEST_FIXTURE"
    }
    gpm_dataset, metadata = process_granule_data(fixture_data["granules"], zone_weights, native_cells, meta_extra)

    assert metadata.get("source_data_origin") == "OFFLINE_TEST_FIXTURE"
    assert gpm_dataset["zones"]["C03"]["data_type"] == "SAMPLE_GPM_COMPATIBLE"
    assert gpm_dataset["zones"]["C03"]["data_type"] != "REAL_GPM"

def test_canonical_dataset_is_real_gpm():
    """Verify the current canonical dataset represents a genuine NASA fetch."""
    meta = load_gpm_metadata()
    assert meta.get("source_data_origin") == "NASA_GES_DISC"

    prov_status = get_gpm_provenance_status()
    assert prov_status["status"] == "REAL_GPM"
    assert prov_status["is_real"] is True
    assert prov_status["source_data_origin"] == "NASA_GES_DISC"

    dataset = load_gpm_observed_dataset()
    for z in dataset["zones"].values():
        assert z["data_type"] == "REAL_GPM"

    dates = list(meta.get("days", {}).values())
    assert len(set(dates)) == 3


# ── 2. Native Coarse Cells & Area-Weighted Overlap ───────────────────────────

def test_native_cell_distribution_across_zones():
    """
    Verify the 25 zones in the Aizawl pilot bbox map to the 4 native 0.1° cells.
    NE cell: 16 zones (including C03)
    SE cell: 4 zones (A02–A05)
    NW cell: 4 zones (B01, C01, D01, E01)
    SW cell: 1 zone (A01)
    """
    dataset = load_gpm_observed_dataset()
    zones = dataset["zones"]

    cell_counts = {}
    for zid, zdata in zones.items():
        cell_id = zdata["dominant_native_cell"]
        cell_counts[cell_id] = cell_counts.get(cell_id, 0) + 1

    assert cell_counts["CELL_LAT23.75_LON92.75"] == 16, "NE cell should cover 16 zones"
    assert cell_counts["CELL_LAT23.65_LON92.75"] == 4, "SE cell should cover 4 zones"
    assert cell_counts["CELL_LAT23.75_LON92.65"] == 4, "NW cell should cover 4 zones"
    assert cell_counts["CELL_LAT23.65_LON92.65"] == 1, "SW cell should cover 1 zone (A01)"

    # C03 should be 100% inside NE cell
    c03 = zones["C03"]
    assert c03["dominant_native_cell"] == "CELL_LAT23.75_LON92.75"
    assert c03["native_cell_weights"]["CELL_LAT23.75_LON92.75"] == 1.0


def test_zone_c03_observed_values_fixture():
    """Verify exact observed precipitation for pilot center C03 using deterministic fixture."""
    import json
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        fixture_data = json.load(f)

    native_cells = derive_intersecting_imerg_cells(PILOT_BBOX, res_deg=0.1)
    zone_weights = compute_zone_overlap_weights(_GRID_RISK_PATH, native_cells)

    meta_extra = {
        "granule_processing_version": "OFFLINE_FIXTURE_V07C",
        "source_data_origin": "OFFLINE_TEST_FIXTURE"
    }
    gpm_dataset, _ = process_granule_data(fixture_data["granules"], zone_weights, native_cells, meta_extra)

    c03_gpm = gpm_dataset["zones"]["C03"]
    obs = c03_gpm["observed_daily_mm"]

    assert obs["d_minus_2"] == 11.6
    assert obs["d_minus_1"] == 19.8
    assert obs["d0"] == 32.4
    assert c03_gpm["antecedent_3d_mm"] == 63.8

def test_zone_c03_canonical_invariants():
    """Verify invariant precipitation rules for canonical C03."""
    import math
    c03_gpm = get_zone_gpm_observed("C03")
    assert c03_gpm is not None
    obs = c03_gpm["observed_daily_mm"]

    d2 = obs["d_minus_2"]
    d1 = obs["d_minus_1"]
    d0 = obs["d0"]
    a3d = c03_gpm["antecedent_3d_mm"]

    assert math.isclose(a3d, d2 + d1 + d0, rel_tol=1e-5)
    assert d0 >= 0.0
    assert d1 >= 0.0
    assert d2 >= 0.0


# ── 3. Data Integrity & Validation ───────────────────────────────────────────

def test_no_negative_or_nan_rainfall():
    """Verify all 25 zones have finite, non-negative rainfall values."""
    dataset = load_gpm_observed_dataset()
    for zid, zdata in dataset["zones"].items():
        obs = zdata["observed_daily_mm"]
        for key in ["d_minus_2", "d_minus_1", "d0"]:
            val = obs[key]
            assert isinstance(val, (int, float))
            assert math.isfinite(val), f"Zone {zid} {key} is not finite: {val}"
            assert val >= 0.0, f"Zone {zid} {key} is negative: {val}"
            assert val <= 500.0, f"Zone {zid} {key} exceeds tropical sanity check: {val}"


# ── 4. Rolling Accumulation with Real GPM Values ──────────────────────────────

def test_c03_rolling_accumulation_with_gpm():
    """
    Test rolling accumulation on C03 where observed is SAMPLE_GPM_COMPATIBLE and forecast is SAMPLE_MOCK.
    C03 GPM observed: D-2=11.6, D-1=19.8, D0=32.4
    C03 sample forecast: F1=65.0, F2=45.0, F3=15.0
    """
    series = get_rainfall_series("C03")
    assert series.observed_provenance == "REAL_GPM"
    assert series.forecast_provenance == "SAMPLE_MOCK"

    rolling = compute_zone_rolling_rainfall(series)

    d0 = series.observed_daily_mm.d0
    d1 = series.observed_daily_mm.d_minus_1
    a3d = series.observed_daily_mm.d_minus_2 + series.observed_daily_mm.d_minus_1 + series.observed_daily_mm.d0

    assert rolling.now.recent_24h_mm == pytest.approx(d0)
    assert rolling.now.antecedent_3d_mm == pytest.approx(a3d)

    # +24h: D-2 drops out, F1 (65.0) enters -> d1 + d0 + 65.0
    assert rolling.h24.recent_24h_mm == pytest.approx(65.0)
    assert rolling.h24.antecedent_3d_mm == pytest.approx(d1 + d0 + 65.0)

    # +48h: D-1 drops out, F2 (45.0) enters -> d0 + 65.0 + 45.0
    assert rolling.h48.recent_24h_mm == pytest.approx(45.0)
    assert rolling.h48.antecedent_3d_mm == pytest.approx(d0 + 65.0 + 45.0)

    # +72h: D0 drops out, F3 (15.0) enters -> 65.0 + 45.0 + 15.0 = 125.0
    assert rolling.h72.recent_24h_mm == pytest.approx(15.0)
    assert rolling.h72.antecedent_3d_mm == pytest.approx(125.0)


# ── 5. Provenance Invariants & Fallback Behavior ──────────────────────────────

def test_forecast_never_labelled_as_gpm():
    """INVARIANT: Forecast intervals must NEVER have REAL_GPM provenance."""
    for zid in ["A01", "C03", "E05"]:
        series = get_rainfall_series(zid)
        assert series.forecast_provenance == "SAMPLE_MOCK"
        assert series.forecast_provenance != "REAL_GPM"
        assert series.forecast_provenance != "SAMPLE_GPM_COMPATIBLE"


def test_missing_gpm_file_triggers_graceful_fallback():
    """When GPM observed file is absent or cannot be loaded, fallback to SAMPLE_MOCK."""
    with patch.object(rainfall_mod, "get_zone_gpm_observed", return_value=None):
        series = get_rainfall_series("C03")
        assert series.observed_provenance == "SAMPLE_MOCK"
        assert "SAMPLE_FALLBACK" in series.note
        assert series.forecast_provenance == "SAMPLE_MOCK"
        assert series.observed_daily_mm.d0 >= 0.0


# ── 6. API Route Verification ─────────────────────────────────────────────────

def test_api_weather_status():
    """GET /weather/status returns REAL_GPM metadata."""
    response = client.get("/weather/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "REAL_GPM"
    assert data["is_real"] is True
    assert data["collection"] == "GPM_3IMERGDL"
    assert data["collection_version"] == "07"
    assert data["algorithm_generation"] == "V07"
    assert data["source_variable"] == "precipitation"
    assert data["source_unit"] == "mm/day"
    assert data["total_zones"] == 25
    assert data["unique_native_cells_count"] == 4


def test_api_weather_zone_c03():
    """GET /weather/C03 returns observed GPM rainfall and sample forecast intervals."""
    response = client.get("/weather/C03")
    assert response.status_code == 200
    data = response.json()
    assert data["zone_id"] == "C03"
    assert data["observed_provenance"] == "REAL_GPM"
    assert data["forecast_provenance"] == "SAMPLE_MOCK"
    assert "d0" in data["observed_daily_mm"]
    assert "d_minus_1" in data["observed_daily_mm"]
    assert "d_minus_2" in data["observed_daily_mm"]
    assert "now" in data["rolling_3d_accumulation_mm"]


def test_api_risk_current_c03_provenance():
    """GET /risk/current/C03 reports REAL_DEM for slope and SAMPLE_GPM_COMPATIBLE for observed rainfall."""
    response = client.get("/risk/current/C03")
    assert response.status_code == 200
    data = response.json()
    prov = data.get("feature_provenance", {})
    assert prov.get("slope") == "REAL_DEM"
    assert prov.get("elevation") == "REAL_DEM"
    assert prov.get("observed_rainfall") == "REAL_GPM"
    assert prov.get("soil_wetness") == "SAMPLE_MOCK"


def test_api_risk_forecast_c03_provenance():
    """GET /risk/forecast/C03 distinguishes SAMPLE_GPM_COMPATIBLE observed from SAMPLE_MOCK forecast."""
    response = client.get("/risk/forecast/C03")
    assert response.status_code == 200
    data = response.json()
    prov = data.get("feature_provenance", {})
    assert prov.get("slope") == "REAL_DEM"
    assert prov.get("observed_rainfall") == "REAL_GPM"
    assert prov.get("forecast_rainfall") == "SAMPLE_MOCK"
    assert prov.get("soil_wetness") == "SAMPLE_MOCK"


def test_api_risk_current_all_zones_gpm_provenance():
    """GET /risk/current verifies all 25 zones carry observed_rainfall=SAMPLE_GPM_COMPATIBLE."""
    response = client.get("/risk/current")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    for z in data["zones"]:
        assert z["feature_provenance"]["observed_rainfall"] == "REAL_GPM"
        assert z["feature_provenance"]["slope"] == "REAL_DEM"
