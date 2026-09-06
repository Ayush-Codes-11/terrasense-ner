"""
test_exposure_priority.py — Comprehensive unit and integration tests for Phase 6:
  - Bounding box derivation from pilot grid
  - Offline OSM element parsing (highways, settlements, critical facilities)
  - Duplicate deduplication and missing name handling
  - Clipped geodesic road length calculation (only inside counted, outside excluded)
  - Boundary handling with covers/intersects
  - Non-blockage guarantee (road_status="EXPOSED_NOT_VERIFIED_BLOCKED", blockage_verified=False)
  - Determinism & monotonicity of priority scoring
  - Priority category mapping
  - 4-horizon priority evaluation holding exposure constant
  - Provenance preservation (REAL_OSM vs SAMPLE_MOCK)
  - Endpoints: /geodata/osm/status, /exposure/{zone_id}, /priority/{zone_id}

100% OFFLINE — ZERO LIVE NETWORK DEPENDENCY.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Point, Polygon

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from backend.main import app
from backend.services.osm_fetcher import get_pilot_bbox
from backend.services.osm_parser import (
    parse_osm_roads,
    parse_osm_settlements,
    parse_osm_critical_facilities,
)
from backend.services.exposure_engine import (
    _calc_linestring_length_km,
    compute_zone_exposure,
    get_osm_provenance_status,
)
from backend.services.priority_config import (
    get_priority_category,
    REF_ROAD_EXPOSURE_KM,
    REF_SETTLEMENTS_COUNT,
    REF_CRITICAL_FACILITIES_COUNT,
    WEIGHT_LANDSLIDE_RISK,
    WEIGHT_ROAD_EXPOSURE,
    WEIGHT_SETTLEMENT_EXPOSURE,
    WEIGHT_CRITICAL_FACILITY_EXPOSURE,
)
from backend.services.priority_engine import (
    score_single_priority,
    compute_zone_priority,
)

client = TestClient(app)


# ── 1. Pilot Bbox Derivation ──────────────────────────────────────────────────

def test_pilot_bbox_derived_correctly():
    south, west, north, east = get_pilot_bbox()
    # Aizawl pilot grid boundaries
    assert 23.68 <= south <= 23.70
    assert 92.67 <= west <= 92.69
    assert 23.75 <= north <= 23.77
    assert 92.75 <= east <= 92.76
    assert south < north
    assert west < east


# ── 2-6. OSM Parsing, Deduplication & Missing Names ───────────────────────────

def test_osm_road_parsing_and_deduplication():
    raw_data = {
        "elements": [
            {
                "type": "way",
                "id": 1001,
                "tags": {"highway": "primary", "name": "Bawngkawn Road", "ref": "NH-54", "surface": "asphalt"},
                "geometry": [{"lat": 23.72, "lon": 92.71}, {"lat": 23.73, "lon": 92.72}],
            },
            # Duplicate ID: must be deduplicated
            {
                "type": "way",
                "id": 1001,
                "tags": {"highway": "primary", "name": "Bawngkawn Road Duplicate"},
                "geometry": [{"lat": 23.72, "lon": 92.71}, {"lat": 23.73, "lon": 92.72}],
            },
            # Road without name: must NOT fabricate
            {
                "type": "way",
                "id": 1002,
                "tags": {"highway": "residential"},
                "geometry": [{"lat": 23.74, "lon": 92.73}, {"lat": 23.75, "lon": 92.74}],
            },
        ]
    }
    fc = parse_osm_roads(raw_data)
    features = fc["features"]
    assert len(features) == 2  # duplicate 1001 removed

    f1 = features[0]
    assert f1["properties"]["osm_id"] == 1001
    assert f1["properties"]["name"] == "Bawngkawn Road"
    assert f1["properties"]["ref"] == "NH-54"
    assert f1["properties"]["blockage_verified"] is False
    assert f1["properties"]["road_status"] == "EXPOSED_NOT_VERIFIED_BLOCKED"

    f2 = features[1]
    assert f2["properties"]["osm_id"] == 1002
    assert f2["properties"]["name"] is None  # Never fabricated!


def test_osm_settlement_parsing_nodes_and_ways():
    raw_data = {
        "elements": [
            {
                "type": "node",
                "id": 2001,
                "lat": 23.725,
                "lon": 92.715,
                "tags": {"place": "village", "name": "Khatla", "population": "12000"},
            },
            # Settlement defined as way/relation polygon: uses 'center'
            {
                "type": "way",
                "id": 2002,
                "center": {"lat": 23.735, "lon": 92.725},
                "tags": {"place": "town", "name": "Zarkawt"},
            },
            # Duplicate
            {
                "type": "node",
                "id": 2001,
                "lat": 23.725,
                "lon": 92.715,
                "tags": {"place": "village", "name": "Khatla Dup"},
            },
        ]
    }
    fc = parse_osm_settlements(raw_data)
    features = fc["features"]
    assert len(features) == 2

    assert features[0]["properties"]["name"] == "Khatla"
    assert features[0]["geometry"]["coordinates"] == [92.715, 23.725]

    assert features[1]["properties"]["name"] == "Zarkawt"
    assert features[1]["geometry"]["coordinates"] == [92.725, 23.735]


def test_osm_critical_facilities_parsing():
    raw_data = {
        "elements": [
            {
                "type": "node",
                "id": 3001,
                "lat": 23.727,
                "lon": 92.718,
                "tags": {"amenity": "hospital", "name": "Civil Hospital Aizawl", "emergency": "yes"},
            },
            {
                "type": "node",
                "id": 3002,
                "lat": 23.729,
                "lon": 92.719,
                "tags": {"amenity": "police", "name": "Aizawl Police Station"},
            },
            {
                "type": "way",
                "id": 3003,
                "center": {"lat": 23.731, "lon": 92.721},
                "tags": {"healthcare": "clinic", "name": "Khatla Clinic"},
            },
        ]
    }
    fc = parse_osm_critical_facilities(raw_data)
    features = fc["features"]
    assert len(features) == 3

    f_map = {f["properties"]["osm_id"]: f["properties"] for f in features}
    assert f_map[3001]["category"] == "hospital"
    assert f_map[3002]["category"] == "police"
    assert f_map[3003]["category"] == "clinic"


# ── 7-12. Geodesic Clipping & Point In/Out Testing ────────────────────────────

def test_road_length_clipped_only_inside_zone():
    """
    Creates a square zone [0.0, 1.0] and a road running from [-1.0, 0.5] to [2.0, 0.5].
    The clipped road length must strictly represent only the [0.0, 1.0] section.
    """
    line_full = LineString([(-1.0, 23.7), (2.0, 23.7)])
    zone_poly = Polygon([(0.0, 23.6), (1.0, 23.6), (1.0, 23.8), (0.0, 23.8)])

    clipped = line_full.intersection(zone_poly)
    assert clipped.geom_type == "LineString"

    len_full = _calc_linestring_length_km(line_full)
    len_clipped = _calc_linestring_length_km(clipped)

    assert len_clipped > 0.0
    assert len_clipped < len_full
    # Full road is 3 degrees lon, clipped is exactly 1 degree lon (approx 1/3)
    assert 0.30 <= (len_clipped / len_full) <= 0.36


def test_outside_road_and_outside_settlement_excluded():
    """Features completely outside the zone polygon must have zero contribution."""
    mock_roads = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "outside_road",
                "properties": {"name": "Remote Road", "highway": "tertiary"},
                "geometry": {"type": "LineString", "coordinates": [[90.0, 20.0], [90.1, 20.1]]},
            }
        ],
    }
    mock_settlements = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "outside_village",
                "properties": {"name": "Distant Village", "place": "village"},
                "geometry": {"type": "Point", "coordinates": [90.0, 20.0]},
            }
        ],
    }
    mock_facilities = {
        "type": "FeatureCollection",
        "features": [],
    }

    res = compute_zone_exposure("C03", mock_roads, mock_settlements, mock_facilities)
    assert res.road_feature_count == 0
    assert res.road_length_km == 0.0
    assert res.settlements_exposed == 0
    assert res.critical_facilities_exposed == 0


def test_inside_and_boundary_settlement_counted():
    """Zone C03 center is ~ [92.7176, 23.7271]. Placing points inside must be counted."""
    mock_roads = {"type": "FeatureCollection", "features": []}
    mock_settlements = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "inside_village",
                "properties": {"name": "Central Village", "place": "village"},
                "geometry": {"type": "Point", "coordinates": [92.7176, 23.7271]},
            }
        ],
    }
    mock_facilities = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "inside_hospital",
                "properties": {"name": "Zone Clinic", "category": "clinic"},
                "geometry": {"type": "Point", "coordinates": [92.7176, 23.7271]},
            }
        ],
    }
    res = compute_zone_exposure("C03", mock_roads, mock_settlements, mock_facilities)
    assert res.settlements_exposed == 1
    assert res.critical_facilities_exposed == 1


def test_exposed_road_not_marked_blocked():
    """Exposed road must strictly have blockage_verified=False and road_status='EXPOSED_NOT_VERIFIED_BLOCKED'."""
    res = compute_zone_exposure("C03")
    for r in res.exposed_roads:
        assert r.blockage_verified is False
        assert r.road_status == "EXPOSED_NOT_VERIFIED_BLOCKED"


# ── 13-20. Priority Engine: Determinism, Bounds, Monotonicity ─────────────────

def test_priority_score_bounds_and_determinism():
    p1 = score_single_priority("now", landslide_risk_score=0.65, landslide_risk_category="HIGH", road_km=2.5, settlements_count=2, facilities_count=1)
    p2 = score_single_priority("now", landslide_risk_score=0.65, landslide_risk_category="HIGH", road_km=2.5, settlements_count=2, facilities_count=1)
    assert p1.priority_score == p2.priority_score
    assert p1.priority == p2.priority
    assert 0.0 <= p1.priority_score <= 1.0


def test_priority_monotonicity_with_landslide_risk():
    """Increasing landslide risk with fixed exposure cannot decrease priority."""
    p_low = score_single_priority("now", 0.30, "MODERATE", 2.0, 1, 1)
    p_high = score_single_priority("now", 0.85, "VERY_HIGH", 2.0, 1, 1)
    assert p_high.priority_score > p_low.priority_score


def test_priority_monotonicity_with_road_exposure():
    """Increasing motorable road exposure with fixed risk strictly increases priority."""
    p_low = score_single_priority("now", 0.60, "HIGH", 5.0, 1, 1)
    p_high = score_single_priority("now", 0.60, "HIGH", 25.0, 1, 1)
    assert p_high.priority_score > p_low.priority_score


def test_priority_settlement_is_context_metric_only():
    """Settlement exposure is retained as context only (weight 0.0 in Phase 6 priority)."""
    p_low = score_single_priority("now", 0.60, "HIGH", 20.0, 0, 1)
    p_high = score_single_priority("now", 0.60, "HIGH", 20.0, 3, 1)
    assert p_high.priority_score == p_low.priority_score


def test_priority_monotonicity_with_facility_exposure():
    """Increasing critical facility count cannot decrease priority."""
    p_low = score_single_priority("now", 0.60, "HIGH", 20.0, 1, 0)
    p_high = score_single_priority("now", 0.60, "HIGH", 20.0, 1, 2)
    assert p_high.priority_score > p_low.priority_score


def test_priority_categories_mapping():
    assert get_priority_category(0.10) == "LOW"
    assert get_priority_category(0.24) == "LOW"
    assert get_priority_category(0.25) == "MODERATE"
    assert get_priority_category(0.49) == "MODERATE"
    assert get_priority_category(0.50) == "HIGH"
    assert get_priority_category(0.74) == "HIGH"
    assert get_priority_category(0.75) == "VERY_HIGH"
    assert get_priority_category(0.99) == "VERY_HIGH"


def test_p90_normalization_references_prevent_premature_saturation():
    """
    Validates that P90 references (~38 km road, 3 facilities) prevent widespread saturation:
    - 10 km of road should not saturate (norm_road < 1.0)
    - 2 facilities should not saturate (norm_facilities < 1.0)
    """
    assert REF_ROAD_EXPOSURE_KM >= 35.0
    assert REF_CRITICAL_FACILITIES_COUNT >= 3.0

    p_10km = score_single_priority("now", 0.5, "HIGH", 10.0, 1, 2)
    p_40km = score_single_priority("now", 0.5, "HIGH", 40.0, 1, 2)
    assert p_40km.priority_score > p_10km.priority_score


def test_motorable_whitelist_excludes_pedestrian_and_track():
    """Steps, footways, paths, and tracks must not contribute to motorable road km."""
    mock_roads = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "r_motorable",
                "properties": {"highway": "residential", "name": "Main Street"},
                "geometry": {"type": "LineString", "coordinates": [[92.715, 23.725], [92.720, 23.725]]},
            },
            {
                "type": "Feature",
                "id": "r_steps",
                "properties": {"highway": "steps", "name": "Public Stairs"},
                "geometry": {"type": "LineString", "coordinates": [[92.715, 23.726], [92.720, 23.726]]},
            },
            {
                "type": "Feature",
                "id": "r_track",
                "properties": {"highway": "track", "name": "Forest Track"},
                "geometry": {"type": "LineString", "coordinates": [[92.715, 23.727], [92.720, 23.727]]},
            },
        ],
    }
    mock_settlements = {"type": "FeatureCollection", "features": []}
    mock_facilities = {"type": "FeatureCollection", "features": []}

    res = compute_zone_exposure("C03", mock_roads, mock_settlements, mock_facilities)
    assert res.osm_road_segments_count == 3
    assert res.motorable_road_segments_count == 1
    assert res.pedestrian_road_km > 0.0
    assert res.track_road_km > 0.0
    # Motorable road length must only equal the length of the residential road
    assert res.motorable_road_km < res.total_road_km


def test_duplicate_overlapping_ways_do_not_double_count_length():
    """
    Two overlapping identical ways in the same zone must be unioned so
    the motorable network length is counted once, not doubled.
    """
    mock_roads = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "r1",
                "properties": {"highway": "primary", "name": "Highway Seg 1"},
                "geometry": {"type": "LineString", "coordinates": [[92.715, 23.725], [92.720, 23.725]]},
            },
            # Exact duplicate alignment with different OSM way ID
            {
                "type": "Feature",
                "id": "r2",
                "properties": {"highway": "primary", "name": "Highway Seg 2 Overlap"},
                "geometry": {"type": "LineString", "coordinates": [[92.715, 23.725], [92.720, 23.725]]},
            },
        ],
    }
    mock_settlements = {"type": "FeatureCollection", "features": []}
    mock_facilities = {"type": "FeatureCollection", "features": []}

    res_single = compute_zone_exposure("C03", {"type": "FeatureCollection", "features": [mock_roads["features"][0]]}, mock_settlements, mock_facilities)
    res_double = compute_zone_exposure("C03", mock_roads, mock_settlements, mock_facilities)

    assert res_double.osm_road_segments_count == 2
    assert res_double.motorable_road_segments_count == 2
    # Unary union guarantees unique network length matches the single line length!
    assert abs(res_double.motorable_road_km - res_single.motorable_road_km) < 0.001


def test_explicit_access_restrictions_excluded():
    """Roads with explicit access=no or motor_vehicle=no must not contribute to motorable km."""
    mock_roads = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "r_public",
                "properties": {"highway": "residential", "name": "Public Way"},
                "geometry": {"type": "LineString", "coordinates": [[92.715, 23.725], [92.720, 23.725]]},
            },
            {
                "type": "Feature",
                "id": "r_no_access",
                "properties": {"highway": "residential", "name": "Barred Way", "access": "no"},
                "geometry": {"type": "LineString", "coordinates": [[92.715, 23.726], [92.720, 23.726]]},
            },
            {
                "type": "Feature",
                "id": "r_private",
                "properties": {"highway": "residential", "name": "Private Compound", "access": "private"},
                "geometry": {"type": "LineString", "coordinates": [[92.715, 23.727], [92.720, 23.727]]},
            },
        ],
    }
    mock_settlements = {"type": "FeatureCollection", "features": []}
    mock_facilities = {"type": "FeatureCollection", "features": []}

    res = compute_zone_exposure("C03", mock_roads, mock_settlements, mock_facilities)
    # The barred way (access=no) must not be counted as motorable
    assert not any(r.feature_id == "r_no_access" and r.is_motorable for r in res.exposed_roads)
    # The private way must have access_restricted=True
    private_item = next(r for r in res.exposed_roads if r.feature_id == "r_private")
    assert private_item.access_restricted is True


def test_critical_facilities_whitelist_and_conservative_deduplication():
    """
    Whitelists hospitals/clinics/police/fire stations, excludes generic healthcare=centre,
    and conservatively merges facilities with matching names within <=50m.
    """
    mock_facilities = {
        "type": "FeatureCollection",
        "features": [
            # Whitelisted Hospital Node
            {
                "type": "Feature",
                "id": "f_hosp_node",
                "properties": {"name": "Ebenezar Hospital", "amenity": "hospital", "category": "hospital"},
                "geometry": {"type": "Point", "coordinates": [92.7176, 23.7271]},
            },
            # Duplicate Polygon Center ~15m away
            {
                "type": "Feature",
                "id": "f_hosp_way",
                "properties": {"name": "Ebenezar Hospital Area", "amenity": "hospital", "category": "hospital"},
                "geometry": {"type": "Point", "coordinates": [92.7177, 23.7272]},
            },
            # Different facility ~35m away: must NOT be merged
            {
                "type": "Feature",
                "id": "f_police",
                "properties": {"name": "Central Police Post", "amenity": "police", "category": "police"},
                "geometry": {"type": "Point", "coordinates": [92.7179, 23.7273]},
            },
            # Non-whitelisted generic healthcare=centre with no amenity tag
            {
                "type": "Feature",
                "id": "f_generic",
                "properties": {"name": "Generic Health Centre", "healthcare": "centre"},
                "geometry": {"type": "Point", "coordinates": [92.7180, 23.7274]},
            },
        ],
    }
    mock_roads = {"type": "FeatureCollection", "features": []}
    mock_settlements = {"type": "FeatureCollection", "features": []}

    res = compute_zone_exposure("C03", mock_roads, mock_settlements, mock_facilities)
    # Total raw facilities in zone: 3 (excluding generic health centre)
    # Deduplicated facilities: 2 (Ebenezar merged, Central Police Post preserved)
    assert res.critical_facilities_exposed == 2
    names = [f.name for f in res.exposed_facilities]
    assert "Central Police Post" in names
    assert any("Ebenezar" in n for n in names)


# ── 21-22. 4 Horizons Hold Exposure Geography Constant ────────────────────────

def test_priority_all_horizons_use_same_exposure():
    res = compute_zone_priority("C03")
    exp = res.exposure_summary
    # Check that each horizon contributor lists identical raw exposure values
    for h in [res.now, res.h24, res.h48, res.h72]:
        contrib_map = {c.component: c.raw_value for c in h.contributors}
        assert contrib_map["road_exposure"] == exp["motorable_road_km"]
        assert contrib_map["critical_facility_exposure"] == exp["critical_facilities"]


def test_priority_explanation_indirect_rainfall_only():
    """Priority explanation must not describe raw rainfall mm, only landslide risk."""
    res = compute_zone_priority("C03")
    assert "mm" not in res.explanation.lower()
    assert "landslide-risk" in res.explanation.lower() or "landslide risk" in res.explanation.lower()
    assert "prototype hazard zone" in res.explanation.lower()
    assert "intersect the prototype hazard zone" in res.horizon_transitions[0].lower()



# ── 23-25. Endpoint Verification ──────────────────────────────────────────────

def test_endpoint_geodata_osm_status():
    res = client.get("/geodata/osm/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("OSM snapshot", "Cached OSM", "Sample fallback")
    assert "attribution" in data
    assert "data_meta" in data


def test_endpoint_exposure_c03():
    res = client.get("/exposure/C03")
    assert res.status_code == 200
    data = res.json()
    assert data["zone_id"] == "C03"
    assert data["summary"]["roads_blocked"] == 0
    assert data["summary"]["roads_exposed"] >= 0
    assert data["hazard_geometry"] == "SAMPLE_MOCK"
    assert data["analysis_mode"] in ("PROTOTYPE_MIXED_PROVENANCE", "SAMPLE_FALLBACK")


def test_endpoint_priority_c03():
    res = client.get("/priority/C03")
    assert res.status_code == 200
    data = res.json()
    assert data["zone_id"] == "C03"
    assert data["priority"] in ("LOW", "MODERATE", "HIGH", "VERY_HIGH")
    assert "now" in data["windows"]
    assert "24h" in data["windows"]
    assert "48h" in data["windows"]
    assert "72h" in data["windows"]
    assert data["priority_label"] == "PROTOTYPE DECISION-SUPPORT — NOT OFFICIAL"


def test_endpoint_invalid_zone_404():
    res = client.get("/exposure/INVALID_ZONE")
    assert res.status_code == 404
    res2 = client.get("/priority/INVALID_ZONE")
    assert res2.status_code == 404
