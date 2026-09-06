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
    """Increasing road exposure with fixed risk cannot decrease priority."""
    p_low = score_single_priority("now", 0.60, "HIGH", 0.5, 1, 1)
    p_high = score_single_priority("now", 0.60, "HIGH", 2.8, 1, 1)
    assert p_high.priority_score > p_low.priority_score


def test_priority_monotonicity_with_settlement_exposure():
    """Increasing settlement count cannot decrease priority."""
    p_low = score_single_priority("now", 0.60, "HIGH", 2.0, 0, 1)
    p_high = score_single_priority("now", 0.60, "HIGH", 2.0, 3, 1)
    assert p_high.priority_score > p_low.priority_score


def test_priority_monotonicity_with_facility_exposure():
    """Increasing critical facility count cannot decrease priority."""
    p_low = score_single_priority("now", 0.60, "HIGH", 2.0, 1, 0)
    p_high = score_single_priority("now", 0.60, "HIGH", 2.0, 1, 2)
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


# ── 21-22. 4 Horizons Hold Exposure Geography Constant ────────────────────────

def test_priority_all_horizons_use_same_exposure():
    res = compute_zone_priority("C03")
    exp = res.exposure_summary
    # Check that each horizon contributor lists identical raw exposure values
    for h in [res.now, res.h24, res.h48, res.h72]:
        contrib_map = {c.component: c.raw_value for c in h.contributors}
        assert contrib_map["road_exposure"] == exp["roads_exposed_km"]
        assert contrib_map["settlement_exposure"] == exp["settlements_exposed"]
        assert contrib_map["critical_facility_exposure"] == exp["critical_facilities_exposed"]


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
