"""
Tests for the Phase 2 spatial hierarchy loader.
"""
import json
import pytest
from pathlib import Path

from models.hierarchy import CoverageLevel, RiskModelStatus, HierarchyStatus
from services.hierarchy_loader import HierarchyLoader, HierarchyDataError

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "hierarchy"

def test_missing_directory_reports_unavailable(tmp_path):
    loader = HierarchyLoader(data_dir=tmp_path)
    assert not loader.available
    assert loader.status == HierarchyStatus.BOUNDARY_DATA_UNAVAILABLE

def test_valid_hierarchy_loads():
    loader = HierarchyLoader(data_dir=FIXTURE_DIR)
    assert loader.available
    assert loader.status == HierarchyStatus.READY

    assert "NER" in loader.regions
    assert "IN-MZ" in loader.states
    assert "TEST-AIZAWL" in loader.districts
    assert "TEST-LUNGLEI" in loader.districts

    # Check relationships
    assert loader.states["IN-MZ"].region_id == "NER"
    assert loader.districts["TEST-AIZAWL"].state_id == "IN-MZ"

def test_administrative_geometries_accessible():
    loader = HierarchyLoader(data_dir=FIXTURE_DIR)
    assert loader.available

    # Verify we didn't discard the feature wrappers containing the boundaries
    assert "IN-MZ" in loader.state_features
    assert loader.state_features["IN-MZ"]["geometry"]["type"] == "Polygon"

    assert "TEST-AIZAWL" in loader.district_features
    assert loader.district_features["TEST-AIZAWL"]["geometry"]["type"] == "Polygon"

def test_pilot_district_id_makes_detailed_pilot():
    loader = HierarchyLoader(data_dir=FIXTURE_DIR)

    aizawl = loader.districts["TEST-AIZAWL"]
    assert aizawl.coverage_level == CoverageLevel.DETAILED_PILOT
    assert aizawl.risk_model_status == RiskModelStatus.STATIC_ML_VALIDATION_PENDING

def test_non_pilot_district_remains_boundary_only():
    loader = HierarchyLoader(data_dir=FIXTURE_DIR)

    lunglei = loader.districts["TEST-LUNGLEI"]
    assert lunglei.coverage_level == CoverageLevel.DISTRICT_BOUNDARY_ONLY
    assert lunglei.risk_model_status == RiskModelStatus.NOT_IMPLEMENTED

def test_no_pilot_id_means_no_detailed_pilot(tmp_path):
    # Copy fixtures to tmp_path but remove pilot_district_id
    with open(FIXTURE_DIR / "metadata.json") as f:
        meta = json.load(f)
    if "pilot_district_id" in meta:
        del meta["pilot_district_id"]

    with open(tmp_path / "metadata.json", "w") as f:
        json.dump(meta, f)

    with open(FIXTURE_DIR / "states.geojson") as f:
        json.dump(json.load(f), open(tmp_path / "states.geojson", "w"))

    with open(FIXTURE_DIR / "districts.geojson") as f:
        json.dump(json.load(f), open(tmp_path / "districts.geojson", "w"))

    loader = HierarchyLoader(data_dir=tmp_path)
    assert loader.available

    aizawl = loader.districts["TEST-AIZAWL"]
    assert aizawl.coverage_level == CoverageLevel.DISTRICT_BOUNDARY_ONLY

def test_invalid_pilot_district_id_rejected(tmp_path):
    with open(FIXTURE_DIR / "metadata.json") as f:
        meta = json.load(f)
    meta["pilot_district_id"] = "DOES_NOT_EXIST"

    with open(tmp_path / "metadata.json", "w") as f:
        json.dump(meta, f)

    with open(FIXTURE_DIR / "states.geojson") as f:
        json.dump(json.load(f), open(tmp_path / "states.geojson", "w"))

    with open(FIXTURE_DIR / "districts.geojson") as f:
        json.dump(json.load(f), open(tmp_path / "districts.geojson", "w"))

    with pytest.raises(HierarchyDataError, match="not a loaded district"):
        HierarchyLoader(data_dir=tmp_path)

def test_duplicate_state_ids_rejected(tmp_path):
    with open(FIXTURE_DIR / "metadata.json") as f:
        json.dump(json.load(f), open(tmp_path / "metadata.json", "w"))

    with open(tmp_path / "districts.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "features": []}, f)

    states = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"state_id": "S1", "state_name": "S1", "region_id": "NER"}, "geometry": {"type": "Polygon", "coordinates": []}},
            {"type": "Feature", "properties": {"state_id": "S1", "state_name": "S2", "region_id": "NER"}, "geometry": {"type": "Polygon", "coordinates": []}}
        ]
    }
    with open(tmp_path / "states.geojson", "w") as f:
        json.dump(states, f)

    with pytest.raises(HierarchyDataError, match="Duplicate state ID"):
        try:
            HierarchyLoader(data_dir=tmp_path)
        except HierarchyDataError as e:
            # Prove it sets invalid status
            loader = HierarchyLoader.__new__(HierarchyLoader)
            # Need to catch and check state manually if we want to ensure status is invalid
            raise e

def test_malformed_data_is_invalid_status(tmp_path):
    with open(FIXTURE_DIR / "metadata.json") as f:
        json.dump(json.load(f), open(tmp_path / "metadata.json", "w"))

    with open(tmp_path / "districts.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "features": []}, f)

    states = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"state_id": "S1", "state_name": "S1", "region_id": "NER"}},
            {"type": "Feature", "properties": {"state_id": "S1", "state_name": "S2", "region_id": "NER"}}
        ]
    }
    with open(tmp_path / "states.geojson", "w") as f:
        json.dump(states, f)

    try:
        HierarchyLoader(data_dir=tmp_path)
    except HierarchyDataError:
        pass # Expected

    # Test instance state
    try:
        loader = HierarchyLoader(data_dir=tmp_path)
    except HierarchyDataError:
        # We can't access loader since it raised in __init__
        pass

    # We can check by separating init and load
    loader = HierarchyLoader.__new__(HierarchyLoader)
    loader.data_dir = tmp_path
    loader.available = False
    loader.status = HierarchyStatus.BOUNDARY_DATA_UNAVAILABLE
    loader.regions = {}
    loader.states = {}
    loader.districts = {}
    loader.state_features = {}
    loader.district_features = {}
    loader._pilot_district_id = None

    with pytest.raises(HierarchyDataError):
        loader._load()

    assert loader.status == HierarchyStatus.BOUNDARY_DATA_INVALID
    assert not loader.available


def test_duplicate_district_ids_rejected(tmp_path):
    with open(FIXTURE_DIR / "metadata.json") as f:
        json.dump(json.load(f), open(tmp_path / "metadata.json", "w"))

    with open(FIXTURE_DIR / "states.geojson") as f:
        json.dump(json.load(f), open(tmp_path / "states.geojson", "w"))

    districts = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"district_id": "D1", "district_name": "D1", "state_id": "IN-MZ"}, "geometry": {"type": "Polygon", "coordinates": []}},
            {"type": "Feature", "properties": {"district_id": "D1", "district_name": "D2", "state_id": "IN-MZ"}, "geometry": {"type": "Polygon", "coordinates": []}}
        ]
    }
    with open(tmp_path / "districts.geojson", "w") as f:
        json.dump(districts, f)

    with pytest.raises(HierarchyDataError, match="Duplicate district ID"):
        HierarchyLoader(data_dir=tmp_path)

def test_district_referencing_nonexistent_state_rejected(tmp_path):
    with open(FIXTURE_DIR / "metadata.json") as f:
        json.dump(json.load(f), open(tmp_path / "metadata.json", "w"))

    with open(FIXTURE_DIR / "states.geojson") as f:
        json.dump(json.load(f), open(tmp_path / "states.geojson", "w"))

    districts = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"district_id": "D1", "district_name": "D1", "state_id": "BAD-STATE"}}
        ]
    }
    with open(tmp_path / "districts.geojson", "w") as f:
        json.dump(districts, f)

    with pytest.raises(HierarchyDataError, match="references nonexistent state"):
        HierarchyLoader(data_dir=tmp_path)

def test_loader_never_fabricates_state_or_district(tmp_path):
    # Only loads what is explicitly in the fixture files
    with open(FIXTURE_DIR / "metadata.json") as f:
        meta = json.load(f)
    if "pilot_district_id" in meta:
        del meta["pilot_district_id"]
    with open(tmp_path / "metadata.json", "w") as f:
        json.dump(meta, f)

    states = {
        "type": "FeatureCollection",
        "features": []
    }
    with open(tmp_path / "states.geojson", "w") as f:
        json.dump(states, f)

    districts = {
        "type": "FeatureCollection",
        "features": []
    }
    with open(tmp_path / "districts.geojson", "w") as f:
        json.dump(districts, f)

    loader = HierarchyLoader(data_dir=tmp_path)
    assert loader.available
    assert len(loader.states) == 0
    assert len(loader.districts) == 0

def test_production_default_path_is_relative_to_backend():
    from services.hierarchy_loader import (
        _BACKEND_DIR,
        _DEFAULT_HIERARCHY_DIR,
        _REPO_ROOT,
    )

    assert _BACKEND_DIR == Path(__file__).resolve().parents[1]
    assert _REPO_ROOT == _BACKEND_DIR.parent
    assert _DEFAULT_HIERARCHY_DIR == _REPO_ROOT / "data" / "geodata" / "ner"


def test_partial_dataset_is_invalid(tmp_path):
    with open(FIXTURE_DIR / 'metadata.json') as f:
        json.dump(json.load(f), open(tmp_path / 'metadata.json', 'w'))
    with pytest.raises(HierarchyDataError, match='Partial hierarchy dataset found'):
        HierarchyLoader(data_dir=tmp_path)



def test_duplicate_region_ids_rejected(tmp_path):
    with open(FIXTURE_DIR / 'metadata.json') as f:
        meta = json.load(f)
    meta['regions'].append({'region_id': 'NER', 'region_name': 'Duplicate'})
    with open(tmp_path / 'metadata.json', 'w') as f:
        json.dump(meta, f)
    with open(FIXTURE_DIR / 'states.geojson') as f:
        json.dump(json.load(f), open(tmp_path / 'states.geojson', 'w'))
    with open(FIXTURE_DIR / 'districts.geojson') as f:
        json.dump(json.load(f), open(tmp_path / 'districts.geojson', 'w'))
    with pytest.raises(HierarchyDataError, match='Duplicate region ID'):
        HierarchyLoader(data_dir=tmp_path)



def test_missing_or_invalid_geometry_rejected(tmp_path):
    with open(FIXTURE_DIR / 'metadata.json') as f:
        json.dump(json.load(f), open(tmp_path / 'metadata.json', 'w'))
    with open(FIXTURE_DIR / 'districts.geojson') as f:
        json.dump(json.load(f), open(tmp_path / 'districts.geojson', 'w'))
    states = {
        'type': 'FeatureCollection',
        'features': [
            {'type': 'Feature', 'properties': {'state_id': 'S1', 'state_name': 'S1', 'region_id': 'NER'}, 'geometry': None}
        ]
    }
    with open(tmp_path / 'states.geojson', 'w') as f:
        json.dump(states, f)
    with pytest.raises(HierarchyDataError, match='invalid or missing geometry'):
        HierarchyLoader(data_dir=tmp_path)



def test_district_invalid_geometry_rejected(tmp_path):
    with open(FIXTURE_DIR / 'metadata.json') as f:
        json.dump(json.load(f), open(tmp_path / 'metadata.json', 'w'))
    with open(FIXTURE_DIR / 'states.geojson') as f:
        json.dump(json.load(f), open(tmp_path / 'states.geojson', 'w'))
    districts = {
        'type': 'FeatureCollection',
        'features': [
            {'type': 'Feature', 'properties': {'district_id': 'D1', 'district_name': 'D1', 'state_id': 'IN-MZ'}, 'geometry': {'type': 'LineString', 'coordinates': []}}
        ]
    }
    with open(tmp_path / 'districts.geojson', 'w') as f:
        json.dump(districts, f)
    with pytest.raises(HierarchyDataError, match='invalid or missing geometry'):
        HierarchyLoader(data_dir=tmp_path)



def test_state_referencing_nonexistent_region_rejected(tmp_path):
    with open(FIXTURE_DIR / 'metadata.json') as f:
        json.dump(json.load(f), open(tmp_path / 'metadata.json', 'w'))
    states = {
        'type': 'FeatureCollection',
        'features': [
            {'type': 'Feature', 'properties': {'state_id': 'S1', 'state_name': 'S1', 'region_id': 'NONEXISTENT'}, 'geometry': {'type': 'Polygon', 'coordinates': []}}
        ]
    }
    with open(tmp_path / 'states.geojson', 'w') as f:
        json.dump(states, f)
    with open(FIXTURE_DIR / 'districts.geojson') as f:
        json.dump(json.load(f), open(tmp_path / 'districts.geojson', 'w'))
    with pytest.raises(HierarchyDataError, match='references nonexistent region'):
        HierarchyLoader(data_dir=tmp_path)

