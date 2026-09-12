"""Offline tests for real-data evidence and explicit model limitations."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

from backend.main import app

client = TestClient(app)


def test_real_risk_status_reports_sources_and_limits():
    response = client.get("/risk/real/status")
    assert response.status_code == 200
    body = response.json()
    assert body["static_model_status"] == "NOT_TRAINED"
    assert body["dynamic_model_status"] == "NOT_VALIDATED"
    assert body["is_probability"] is False
    assert body["sources"]["landslide_inventory"]["date_linked_events"] == 0


def test_real_risk_a01_uses_real_inputs_and_is_not_probability():
    response = client.get("/risk/real/A01")
    assert response.status_code == 200
    body = response.json()
    assert body["zone_id"] == "A01"
    assert body["fusion"]["is_probability"] is False
    assert body["fusion"]["is_calibrated"] is False
    assert body["provenance"]["terrain"] == "REAL_DEM"
    assert body["provenance"]["landslide_inventory"] == "REAL_GSI_SPATIAL_INVENTORY"
    assert 0.0 <= body["fusion"]["score"] <= 1.0


def test_real_risk_rejects_unknown_zone():
    assert client.get("/risk/real/UNKNOWN").status_code == 404
