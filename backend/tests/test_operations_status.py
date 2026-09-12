import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.main import app


def test_operations_status_is_explicit_about_unconfigured_streams():
    response = TestClient(app).get("/operations/status")
    assert response.status_code == 200
    body = response.json()
    assert body["connectivity"]["kafka"] in {"NOT_CONFIGURED", "UNAVAILABLE", "ONLINE"}
    assert body["connectivity"]["offline_field_reports"] == "AVAILABLE"
    assert body["model_readiness"]["calibrated_probability"] is False
    assert body["verification"]["status"] in {"PASS", "UNAVAILABLE"}
