import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.main import app


def test_official_contacts_are_reference_only_and_source_attributed():
    response = TestClient(app).get("/contacts/official")
    assert response.status_code == 200
    body = response.json()
    assert body["operational_status"] == "REFERENCE_ONLY"
    assert any(item["phone"] == "112" for item in body["contacts"])
    assert all(item["verified_from_source"] is True for item in body["contacts"])
