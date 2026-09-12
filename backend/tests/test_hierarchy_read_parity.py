"""Offline negative tests for the parity checker, not a substitute for live parity."""
from types import SimpleNamespace

import pytest
from shapely.geometry import mapping, MultiPolygon, shape

from db.hierarchy_parity import compare_hierarchy_readers
from services.data_loader import load_grid_risk
from services.hierarchy_loader import HierarchyLoader
from services.hierarchy_repository import FileHierarchyRepository


@pytest.fixture
def parity_pair():
    loader = HierarchyLoader()
    adapter = FileHierarchyRepository(loader)
    features = {"states": loader.state_features, "districts": loader.district_features,
                "analysis_zones": {f["properties"]["zone_id"]: f for f in load_grid_risk()["features"]}}
    geometries = {}
    for table, rows in features.items():
        geometries[table] = {}
        for key, feature in rows.items():
            geom = shape(feature["geometry"])
            if geom.geom_type == "Polygon":
                geom = MultiPolygon([geom])
            geometries[table][key] = mapping(geom)
    reader = SimpleNamespace(
        regions=dict(adapter.regions), states=dict(adapter.states), districts=dict(adapter.districts),
        get_district_zones=adapter.get_district_zones, geometries=geometries,
        geometry_srids={table: dict.fromkeys(rows, 4326) for table, rows in features.items()})
    return loader, reader


def test_parity_accepts_only_the_phase3a_polygon_wrapper(parity_pair):
    report = compare_hierarchy_readers(*parity_pair)
    assert report["geometry_match"] and report["mismatches"] == []


@pytest.mark.parametrize("damage", ["missing", "srid", "type", "coordinate"])
def test_parity_rejects_geometry_changes(parity_pair, damage):
    loader, reader = parity_pair
    if damage == "missing":
        reader.geometries["analysis_zones"].pop("C03")
    elif damage == "srid":
        reader.geometry_srids["analysis_zones"]["C03"] = 3857
    elif damage == "type":
        geom = shape(reader.geometries["analysis_zones"]["C03"])
        reader.geometries["analysis_zones"]["C03"] = mapping(geom.geoms[0])
    else:
        from shapely.affinity import translate
        geom = shape(reader.geometries["analysis_zones"]["C03"])
        reader.geometries["analysis_zones"]["C03"] = mapping(translate(geom, xoff=1e-10))
    report = compare_hierarchy_readers(loader, reader)
    assert report["geometry_match"] is False
    assert "analysis_zones/C03: geometry or SRID differs" in report["mismatches"]


def test_parity_rejects_domain_changes(parity_pair):
    loader, reader = parity_pair
    reader.states["IN-MZ"] = reader.states["IN-MZ"].model_copy(update={"state_name": "Changed"})
    report = compare_hierarchy_readers(loader, reader)
    assert report["states_match"] is False
    assert "states/IN-MZ: fields differ" in report["mismatches"]
