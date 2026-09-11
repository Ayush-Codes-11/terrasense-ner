"""Tests for the read-only Northeast administrative hierarchy API."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from backend.main import app


client = TestClient(app)


def test_hierarchy_states_and_region():
    region = client.get("/hierarchy/region")
    states = client.get("/hierarchy/states")
    assert region.status_code == 200
    assert region.json()["features"][0]["properties"]["region_id"] == "NER"
    assert states.status_code == 200
    assert len(states.json()["features"]) == 8
    assert all(feature["properties"]["region_id"] == "NER" for feature in states.json()["features"])


def test_hierarchy_districts_and_aizawl():
    districts = client.get("/hierarchy/districts")
    assert districts.status_code == 200
    assert len(districts.json()["features"]) == 119

    aizawl_id = "IND-ADM2-76128533B34203923268864"
    aizawl = client.get(f"/hierarchy/districts/{aizawl_id}")
    assert aizawl.status_code == 200
    assert aizawl.json()["properties"]["district_name"] == "Aizawl"
    assert aizawl.json()["properties"]["state_id"] == "IN-MZ"


def test_hierarchy_state_district_relation_and_not_found():
    districts = client.get("/hierarchy/states/IN-MZ/districts")
    assert districts.status_code == 200
    assert len(districts.json()["features"]) == 11
    assert all(
        feature["properties"]["state_id"] == "IN-MZ"
        for feature in districts.json()["features"]
    )

    assert client.get("/hierarchy/states/XX-XX").status_code == 404
    assert client.get("/hierarchy/districts/unknown").status_code == 404
