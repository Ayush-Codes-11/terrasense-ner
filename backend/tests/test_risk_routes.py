"""
Tests for backend risk routes:
  - GET /risk/current
  - GET /risk/current/{zone_id}
  - GET /risk/forecast/{zone_id}
  - GET /health
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure backend and repo root are importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from backend.main import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["risk_engine"] == "prototype_scorer_active"
    assert data["data_mode"] == "SAMPLE_MOCK"


def test_get_all_current_risk():
    res = client.get("/risk/current")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 25
    assert len(data["zones"]) == 25

    # Verify score semantics and prototype computations on every zone
    for z in data["zones"]:
        assert 0.0 <= z["score"] <= 1.0
        assert z["score_type"] == "prototype_relative_risk_score"
        assert z["is_probability"] is False
        assert z["is_calibrated"] is False
        assert z["computed_by"] == "prototype_scorer_v1"
        assert z["risk_category"] in ["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
        assert len(z["contributors"]) == 4

        # Verify nested normalized_features
        nf = z["normalized_features"]
        assert 0.0 <= nf["terrain"] <= 1.0
        assert 0.0 <= nf["recent_rainfall"] <= 1.0
        assert 0.0 <= nf["antecedent_rainfall"] <= 1.0
        assert 0.0 <= nf["soil_wetness"] <= 1.0
        assert "soil_wetness_index" in z


def test_get_zone_current_risk_c03():
    res = client.get("/risk/current/C03")
    assert res.status_code == 200
    data = res.json()
    assert data["zone_id"] == "C03"
    assert data["risk_category"] in ("MODERATE", "HIGH")
    assert 0.40 <= data["score"] <= 0.80  # score range valid for real DEM slope ~22°
    assert data["score_type"] == "prototype_relative_risk_score"
    assert data["is_probability"] is False
    assert data["is_calibrated"] is False

    # Phase 7: slope is sourced from REAL_DEM (22.06°), not SAMPLE_MOCK (42°)
    # Terrain normalized = 22.06 / 40 ≈ 0.55 (not capped at 1.0)
    assert "normalized_features" in data
    terrain_norm = data["normalized_features"]["terrain"]
    assert 0.4 < terrain_norm < 0.8, (
        f"Expected terrain_norm ~0.55 (REAL_DEM slope 22.06°/40°), got {terrain_norm}. "
        "If 1.0, slope may still be using SAMPLE_MOCK 42°."
    )

    # Phase 8: feature_provenance must show REAL_DEM for slope, SAMPLE_GPM_COMPATIBLE for observed rainfall
    prov = data.get("feature_provenance", {})
    assert prov.get("slope") == "REAL_DEM"
    assert prov.get("observed_rainfall") == "REAL_GPM"

    # Check contributors are sorted descending by contribution
    contribs = [c["contribution"] for c in data["contributors"]]
    assert contribs == sorted(contribs, reverse=True)


def test_get_zone_current_risk_not_found():
    res = client.get("/risk/current/INVALID")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_get_zone_forecast_distinction():
    res = client.get("/risk/forecast/C03")
    assert res.status_code == 200
    data = res.json()
    assert data["zone_id"] == "C03"

    # NOW is PROTOTYPE_COMPUTED
    assert data["now"]["mode"] == "PROTOTYPE_COMPUTED"
    assert data["now"]["is_probability"] is False
    assert data["now"]["score_type"] == "prototype_relative_risk_score"

    # Future windows in Phase 5 are dynamically PROTOTYPE_COMPUTED
    for win_key in ["24h", "48h", "72h"]:
        win = data["forecast"][win_key]
        assert win["mode"] == "PROTOTYPE_COMPUTED"
        assert win["score_type"] == "prototype_relative_risk_score"
        assert win["is_probability"] is False
        assert "antecedent_rain_mm" in win

