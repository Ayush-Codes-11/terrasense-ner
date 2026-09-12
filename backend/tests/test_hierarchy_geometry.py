"""Opt-in map geometry must preserve the original metadata API."""
import pytest
from fastapi.testclient import TestClient
from main import app
from services.hierarchy_loader import HierarchyLoader


@pytest.mark.parametrize("path,count,collection,key", [
    ("/regions/NER/states", 8, "state_features", "state_id"),
    ("/states", 8, "state_features", "state_id"),
    ("/states/IN-MZ/districts", 11, "district_features", "district_id"),
])
def test_geometry_opt_in_matches_canonical(path, count, collection, key, monkeypatch):
    monkeypatch.setenv("HIERARCHY_DATA_SOURCE", "file")
    loader = HierarchyLoader()
    with TestClient(app) as client:
        plain = client.get(path).json()
        response = client.get(path + "?include_geometry=true")
    assert response.status_code == 200
    geo = response.json()
    assert "features" not in plain
    assert geo["type"] == "FeatureCollection" and geo["count"] == count
    assert [f["properties"] for f in geo["features"]] == plain["items"]
    for f in geo["features"]:
        assert f["geometry"] == getattr(loader, collection)[f["properties"][key]]["geometry"]


def test_geometry_unknown_and_unavailable(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setenv("HIERARCHY_DATA_SOURCE", "file")
        assert client.get("/states/UNKNOWN/districts?include_geometry=true").status_code == 404
        monkeypatch.setenv("HIERARCHY_DATA_SOURCE", "postgis")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        response = client.get("/states?include_geometry=true")
        assert response.status_code == 503
        assert response.json()["detail"]["status"] == "BOUNDARY_DATA_UNAVAILABLE"
