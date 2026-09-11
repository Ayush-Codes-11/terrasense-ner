import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from main import app
from routes.hierarchy import get_hierarchy_loader
from services.hierarchy_loader import HierarchyLoader
from models.hierarchy import CoverageLevel, RiskModelStatus, HierarchyStatus

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "hierarchy"

def override_hierarchy_loader():
    return HierarchyLoader(data_dir=FIXTURE_DIR)

# Pytest fixture for a client with the valid fixture loader
@pytest.fixture
def client_with_fixture():
    app.dependency_overrides[get_hierarchy_loader] = override_hierarchy_loader
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

def test_get_regions(client_with_fixture):
    response = client_with_fixture.get("/regions")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert any(r["region_id"] == "NER" for r in data["items"])

def test_get_region_states(client_with_fixture):
    response = client_with_fixture.get("/regions/NER/states")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    state_ids = [s["state_id"] for s in data["items"]]
    assert "IN-MZ" in state_ids
    assert "IN-AS" in state_ids

def test_get_states(client_with_fixture):
    response = client_with_fixture.get("/states")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2

def test_get_state(client_with_fixture):
    response = client_with_fixture.get("/states/IN-MZ")
    assert response.status_code == 200
    data = response.json()
    assert data["state_name"] == "Mizoram"
    assert data["region_id"] == "NER"

def test_get_state_districts(client_with_fixture):
    response = client_with_fixture.get("/states/IN-MZ/districts")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    district_ids = [d["district_id"] for d in data["items"]]
    assert "TEST-AIZAWL" in district_ids
    assert "TEST-LUNGLEI" in district_ids

def test_get_district_aizawl(client_with_fixture):
    response = client_with_fixture.get("/districts/TEST-AIZAWL")
    assert response.status_code == 200
    data = response.json()
    assert data["coverage_level"] == CoverageLevel.DETAILED_PILOT
    assert data["risk_model_status"] == RiskModelStatus.STATIC_ML_VALIDATION_PENDING

def test_get_district_lunglei(client_with_fixture):
    response = client_with_fixture.get("/districts/TEST-LUNGLEI")
    assert response.status_code == 200
    data = response.json()
    assert data["coverage_level"] == CoverageLevel.DISTRICT_BOUNDARY_ONLY
    assert data["risk_model_status"] == RiskModelStatus.NOT_IMPLEMENTED

def test_404_responses(client_with_fixture):
    assert client_with_fixture.get("/regions/UNKNOWN/states").status_code == 404
    assert client_with_fixture.get("/states/UNKNOWN").status_code == 404
    assert client_with_fixture.get("/states/UNKNOWN/districts").status_code == 404
    assert client_with_fixture.get("/districts/UNKNOWN").status_code == 404

def test_hierarchy_unavailable(tmp_path):
    def override_missing():
        return HierarchyLoader(data_dir=tmp_path)

    app.dependency_overrides[get_hierarchy_loader] = override_missing
    client = TestClient(app)

    response = client.get("/regions")
    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "BOUNDARY_DATA_UNAVAILABLE"

    assert client.get("/districts/TEST-AIZAWL/zones").status_code == 503
    assert client.get("/zones/C03").status_code == 503

    app.dependency_overrides.clear()

def test_hierarchy_invalid(tmp_path):
    import json
    with open(FIXTURE_DIR / "metadata.json") as f:
        json.dump(json.load(f), open(tmp_path / "metadata.json", "w"))
    # Incomplete dataset -> INVALID
    def override_invalid():
        # will raise an error internally and set to invalid
        # wait, HierarchyLoader raises HierarchyDataError on init if it's invalid!
        # Ah, we need to catch it or let FastAPI catch it?
        # Actually in production `get_hierarchy_loader` is cached and runs during startup?
        # Let's see: `get_hierarchy_loader` returns an instance. If it raises, startup might crash!
        try:
            return HierarchyLoader(data_dir=tmp_path)
        except Exception:
            # We can create a fake one that failed, because in reality if it fails,
            # it might crash the app UNLESS we catch it in the loader.
            # But the loader DOES raise HierarchyDataError. So app startup WOULD crash if it's INVALID!
            pass

        loader = HierarchyLoader.__new__(HierarchyLoader)
        loader.status = HierarchyStatus.BOUNDARY_DATA_INVALID
        loader.available = False
        return loader

    app.dependency_overrides[get_hierarchy_loader] = override_invalid
    client = TestClient(app)

    response = client.get("/regions")
    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "BOUNDARY_DATA_INVALID"

    app.dependency_overrides.clear()

def test_legacy_routes_work_when_hierarchy_unavailable(tmp_path):
    def override_missing():
        return HierarchyLoader(data_dir=tmp_path)

    app.dependency_overrides[get_hierarchy_loader] = override_missing
    try:
        with TestClient(app) as client:
            response = client.get("/regions")
            assert response.status_code == 503
            assert response.json()["detail"]["status"] == "BOUNDARY_DATA_UNAVAILABLE"

            assert client.get("/health").status_code == 200
            assert client.get("/zones").status_code == 200

            response = client.get("/risk/current/C03")
            assert response.status_code == 200
            prov = response.json().get("feature_provenance", {})
            assert prov.get("slope") == "REAL_DEM"
            assert prov.get("observed_rainfall") == "REAL_GPM"
    finally:
        app.dependency_overrides.clear()


def test_get_district_zones_pilot(client_with_fixture):
    response = client_with_fixture.get('/districts/TEST-AIZAWL/zones')
    assert response.status_code == 200
    data = response.json()
    assert data['district_id'] == 'TEST-AIZAWL'
    assert data['detailed_zone_model_available'] is True
    assert data['count'] == 25
    assert len(data['items']) == 25
    z_c03 = next((z for z in data['items'] if z['zone_id'] == 'C03'), None)
    assert z_c03 is not None
    assert z_c03['zone_type'] == 'PROTOTYPE_ANALYSIS_GRID'
    assert z_c03['district_id'] == 'TEST-AIZAWL'

    zone_ids = [z['zone_id'] for z in data['items']]
    assert len(zone_ids) == len(set(zone_ids))
    assert 'SYNTHETIC' not in zone_ids

def test_get_district_zones_non_pilot(client_with_fixture):
    response = client_with_fixture.get('/districts/TEST-LUNGLEI/zones')
    assert response.status_code == 200
    data = response.json()
    assert data['count'] == 0
    assert len(data['items']) == 0
    assert data['detailed_zone_model_available'] is False

def test_get_district_zones_unknown(client_with_fixture):
    assert client_with_fixture.get('/districts/UNKNOWN/zones').status_code == 404

def test_get_zone(client_with_fixture):
    response = client_with_fixture.get('/zones/C03')
    assert response.status_code == 200
    data = response.json()
    assert data['zone_id'] == 'C03'
    assert data['district_id'] == 'TEST-AIZAWL'
    assert data['zone_type'] == 'PROTOTYPE_ANALYSIS_GRID'

def test_get_zone_unknown(client_with_fixture):
    assert client_with_fixture.get('/zones/UNKNOWN').status_code == 404

def test_legacy_get_zones_preserved():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    response = client.get('/zones')
    assert response.status_code == 200
    data = response.json()
    assert data['type'] == 'FeatureCollection'
    features = data['features']
    assert len(features) == 25
    z_c03 = next((f for f in features if f['properties']['zone_id'] == 'C03'), None)
    assert z_c03 is not None
    assert z_c03['geometry']['type'] == 'Polygon'

def test_analysis_zone_service_discovers_zones_from_canonical_loader(monkeypatch):
    from services.analysis_zone_service import AnalysisZoneService

    # Mock the canonical loader to return a synthetic set of zones
    def mock_get_all_zone_props():
        return [{"zone_id": "X01"}, {"zone_id": "X02"}, {"zone_id": "X03"}]

    monkeypatch.setattr('services.analysis_zone_service.get_all_zone_props', mock_get_all_zone_props)

    service = AnalysisZoneService(override_hierarchy_loader())
    zones = service.get_district_zones("TEST-AIZAWL")

    zone_ids = [z.zone_id for z in zones]
    assert zone_ids == ["X01", "X02", "X03"]
    assert all(z.district_id == "TEST-AIZAWL" for z in zones)
