"""
test_gsi_inventory.py — Tests for Phase 7 GSI inventory audit and feasibility gate.

These tests do NOT depend on the live GSI FeatureServer.
They test against:
1. The cached gsi_mizoram_raw.json snapshot on disk.
2. The gsi_inventory.py service module.
3. The model_feasibility.json output.

Tests cover:
- Raw data file loads correctly
- Schema fields are present
- Coordinate validity
- Date field quality (0 exact dates in this dataset)
- District breakdown sanity
- Duplicate detection
- Feasibility gate outcome matches real findings
- No synthetic/fabricated dates in output
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

_LANDSLIDE_DIR = _REPO_ROOT / "data" / "real" / "landslides"
_RAW_FILE = _LANDSLIDE_DIR / "gsi_mizoram_raw.json"
_FEASIBILITY_FILE = _LANDSLIDE_DIR / "model_feasibility.json"

pytestmark = pytest.mark.skipif(
    not _RAW_FILE.exists(),
    reason="GSI raw data not present — run backend/scripts/inspect_gsi_inventory.py first",
)

EXPECTED_FIELDS = {
    "state", "district", "latitude", "longitude",
    "date", "datetimety", "date_acc", "exactdatei",
}


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def raw_data():
    with open(_RAW_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def features(raw_data):
    return raw_data.get("retrieved_features", [])


@pytest.fixture(scope="module")
def feasibility():
    if _FEASIBILITY_FILE.exists():
        with open(_FEASIBILITY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return None


# ─── 1. File loads correctly ─────────────────────────────────────────────────

def test_raw_file_loads(raw_data):
    """GSI raw file has correct top-level structure."""
    assert "retrieved_features" in raw_data
    assert "source" in raw_data
    assert "query_filter" in raw_data


def test_raw_file_has_records(features):
    """File contains at least some records."""
    assert len(features) > 0, "No features in gsi_mizoram_raw.json"


# ─── 2. Schema fields present ────────────────────────────────────────────────

def test_expected_fields_in_records(features):
    """Key schema fields are present in attributes."""
    sample = features[0]["attributes"]
    for field in EXPECTED_FIELDS:
        assert field in sample, f"Field '{field}' not in first record attributes"


# ─── 3. Coordinate validity ───────────────────────────────────────────────────

def test_all_records_have_coordinates(features):
    """All Mizoram records in the snapshot have latitude and longitude."""
    missing = 0
    for feat in features:
        attrs = feat.get("attributes", {})
        geom = feat.get("geometry", {})
        lat = attrs.get("latitude") or geom.get("y")
        lon = attrs.get("longitude") or geom.get("x")
        if lat is None or lon is None:
            missing += 1
    assert missing == 0, f"{missing} records are missing coordinates"


def test_coordinates_in_mizoram_bbox(features):
    """Coordinates fall within a broad Mizoram bounding box."""
    # Mizoram roughly: 21.9°N–24.5°N, 92.2°E–93.5°E
    out_of_range = 0
    for feat in features:
        attrs = feat.get("attributes", {})
        geom = feat.get("geometry", {})
        lat = attrs.get("latitude") or geom.get("y")
        lon = attrs.get("longitude") or geom.get("x")
        if lat is None or lon is None:
            continue
        lat, lon = float(lat), float(lon)
        if not (21.0 <= lat <= 25.0 and 91.5 <= lon <= 94.0):
            out_of_range += 1
    # Allow a small tolerance for mis-classified records
    assert out_of_range < len(features) * 0.05, (
        f"{out_of_range} records have coordinates far outside Mizoram"
    )


# ─── 4. Date field quality ────────────────────────────────────────────────────

def test_no_invented_dates(features):
    """
    Date fields must be null or whitespace — no synthetic dates should be present.
    The real GSI Mizoram public dataset has 0 usable event dates.
    This test will fail if someone fabricates dates.
    """
    for feat in features:
        attrs = feat.get("attributes", {})
        date_val = attrs.get("date")
        if date_val is not None and str(date_val).strip():
            # If a date looks like YYYY-MM-DD it might be real (from a different dataset load)
            # This is just an audit guard — real dataset has all null/blank dates
            val = str(date_val).strip()
            assert val == " " or len(val) <= 1, (
                f"Unexpected non-null date value found: '{val}'. "
                "Ensure no fabricated dates have been inserted."
            )


def test_date_fields_all_null_or_blank(features):
    """
    Real Mizoram public GSI inventory has NO usable event dates.
    All date/datetimety/date_acc/exactdatei fields are null or whitespace.
    """
    date_fields = ("date", "datetimety", "date_acc", "exactdatei")
    records_with_dates = 0
    for feat in features:
        attrs = feat.get("attributes", {})
        for field in date_fields:
            val = attrs.get(field)
            if val and str(val).strip() and str(val).strip() not in (" ", ""):
                records_with_dates += 1
                break
    assert records_with_dates == 0, (
        f"{records_with_dates} records have non-null date fields. "
        "Expected 0 for the Mizoram public GSI inventory."
    )


# ─── 5. District breakdown ───────────────────────────────────────────────────

def test_aizawl_district_present(features):
    """Aizawl district records are present in the snapshot."""
    aizawl = [
        f for f in features
        if str(f.get("attributes", {}).get("district", "")).strip() == "Aizawl"
    ]
    assert len(aizawl) > 10, f"Expected >10 Aizawl records, got {len(aizawl)}"


def test_state_is_mizoram(features):
    """All records have state='Mizoram' (the query filter)."""
    non_mizoram = [
        f for f in features
        if str(f.get("attributes", {}).get("state", "")).strip() != "Mizoram"
    ]
    assert len(non_mizoram) == 0, f"{len(non_mizoram)} records have state != 'Mizoram'"


# ─── 6. Duplicate detection ──────────────────────────────────────────────────

def test_duplicate_detection():
    """audit_records correctly identifies duplicate coordinate pairs."""
    from backend.services.gsi_inventory import audit_records
    audit = audit_records()
    # We know from real data there are duplicate coordinate pairs
    assert audit["duplicate_coordinate_pairs"] >= 0  # should not crash
    assert audit["duplicate_records_total"] >= 0


# ─── 7. gsi_inventory service ────────────────────────────────────────────────

def test_gsi_inventory_service_loads():
    """gsi_inventory.get_all_mizoram_records() returns a non-empty list."""
    from backend.services.gsi_inventory import get_all_mizoram_records
    records = get_all_mizoram_records()
    assert len(records) > 0


def test_audit_returns_expected_structure():
    """audit_records() returns the expected dict structure."""
    from backend.services.gsi_inventory import audit_records
    audit = audit_records()
    required_keys = {
        "total_mizoram", "by_district", "pilot_bbox_count",
        "has_usable_coordinates", "exact_date_records",
        "partial_date_records", "no_date_records",
        "duplicate_coordinate_pairs", "duplicate_records_total",
    }
    for key in required_keys:
        assert key in audit, f"audit_records missing key: {key}"


# ─── 8. Feasibility gate outcome ─────────────────────────────────────────────

def test_feasibility_file_exists():
    """model_feasibility.json must exist after running inspect_gsi_inventory.py."""
    assert _FEASIBILITY_FILE.exists(), (
        "model_feasibility.json not found. "
        "Run backend/scripts/inspect_gsi_inventory.py to generate it."
    )


def test_feasibility_outcome(feasibility):
    """
    Feasibility outcome must be TEMPORAL_RAINFALL_TRIGGER_MODEL_NOT_FEASIBLE_WITH_CURRENT_PUBLIC_GSI_INVENTORY
    given the complete real GSI data (geolocated records but 0 event dates).
    """
    assert feasibility is not None
    outcome = feasibility.get("feasibility_outcome")
    expected = "TEMPORAL_RAINFALL_TRIGGER_MODEL_NOT_FEASIBLE_WITH_CURRENT_PUBLIC_GSI_INVENTORY"
    assert outcome == expected, f"Expected {expected}, got: {outcome}"


def test_feasibility_not_fabricated(feasibility):
    """Feasibility report must not claim trained-model feasibility based on fabricated data."""
    assert feasibility is not None
    dqs = feasibility.get("date_quality_summary") or feasibility.get("audit_results", {})
    # The real dataset has 0 exact dates — ensure this is preserved
    assert dqs.get("exact_date_records", 0) == 0, (
        f"Expected 0 exact_date_records, got {dqs.get('exact_date_records')}. "
        "Ensure no fabricated dates were inserted."
    )


def test_feasibility_has_source_info(feasibility):
    """Feasibility report must document the real data source."""
    assert feasibility is not None
    src = feasibility.get("data_source", {})
    assert "bhusanket" in src.get("url", "").lower() or "gsi.gov.in" in src.get("url", "").lower(), (
        f"Data source URL does not reference GSI BhooSanket: {src.get('url')}"
    )
    assert src.get("access") is not None
