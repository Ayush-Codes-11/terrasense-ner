"""
inspect_gsi_inventory.py — Runs audit on the cached GSI Mizoram records
and produces data/real/landslides/model_feasibility.json.

Run from the repo root:
    python backend/scripts/inspect_gsi_inventory.py

Output:
    data/real/landslides/model_feasibility.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add repo root and backend to path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from backend.services.gsi_inventory import audit_records, _LANDSLIDE_DIR

FEASIBILITY_FILE = _LANDSLIDE_DIR / "model_feasibility.json"

# ─── Known global counts (from live API query, 2026-09-06) ───
GLOBAL_COUNTS = {
    "total_all_india": 31545,
    "total_mizoram": 2046,
    "total_aizawl_district": 457,
    "total_pilot_bbox": 60,
    "note": (
        "Counts from live GSI BhooSanket FeatureServer (Hosted/Public_Portal_Dashboard_Map, layer 0). "
        "2000 records fetched (API max per request). Actual Mizoram total is 2046."
    ),
}


def main():
    print("=" * 60)
    print("GSI Inventory Audit — TerraSense Phase 7")
    print("=" * 60)

    audit = audit_records()
    print(json.dumps(audit, indent=2))

    # ── Feasibility decision ──
    total = audit["total_mizoram"]
    pilot = audit["pilot_bbox_count"]
    exact_dates = audit["exact_date_records"]
    partial_dates = audit["partial_date_records"]
    no_date = audit["no_date_records"]
    has_coords = audit["has_usable_coordinates"]
    dups = audit["duplicate_records_total"]

    # A trained model requires: geolocated + dated records in sufficient volume.
    # For Mizoram / Aizawl pilot: 0 exact-date + 0 partial-date records
    # → temporal ML training is not feasible.
    # Records with geolocated-but-undated positions CAN support a
    # static spatial susceptibility map (inventory density / kernel density),
    # but NOT a temporally validated XGBoost rainfall-triggered model.

    has_any_date = (exact_dates + partial_dates) > 0
    has_enough_aizawl = pilot >= 10  # minimum 10 pilot-bbox records with dates

    if exact_dates >= 30 and pilot >= 10:
        outcome = "TRAINED_MODEL_FEASIBLE"
        rationale = (
            f"Sufficient geolocated + exact-date records ({exact_dates} exact-date, "
            f"{pilot} in pilot bbox). XGBoost training may be attempted."
        )
    elif has_coords >= 50 and not has_any_date:
        outcome = "STATIC_SUSCEPTIBILITY_MODEL_MAY_BE_FEASIBLE"
        rationale = (
            f"{has_coords} geolocated records exist (including {pilot} in pilot bbox), "
            f"but ZERO records have any usable event date ({exact_dates} exact-date, "
            f"{partial_dates} partial-date, {no_date} no-date). "
            "A static spatial susceptibility map based on inventory point density may be possible, "
            "but a temporally validated rainfall-triggered ML model (XGBoost) is NOT feasible "
            "with this dataset alone — event timing cannot be linked to rainfall triggers."
        )
    else:
        outcome = "KEEP_TRANSPARENT_PROTOTYPE_SCORER"
        rationale = (
            f"Insufficient usable data: {exact_dates} exact-date records, "
            f"{has_coords} geolocated records, {pilot} in pilot bbox. "
            "Prototype scorer is the appropriate model for this stage."
        )

    feasibility = {
        "feasibility_outcome": outcome,
        "rationale": rationale,
        "data_source": {
            "name": "GSI BhooSanket Public Portal — Landslide_Public",
            "url": (
                "https://bhusanket.gsi.gov.in/gisserver/rest/services/"
                "Hosted/Public_Portal_Dashboard_Map/FeatureServer/0"
            ),
            "access": "Public — no authentication required for this layer",
            "note": (
                "The alternative FeatureServer (Hosted/India_All_Landslided) on the same domain "
                "requires a GIS token (HTTP 499 Token Required). "
                "The Public_Portal_Dashboard_Map layer is the officially public-facing equivalent."
            ),
        },
        "global_counts": GLOBAL_COUNTS,
        "audit_results": audit,
        "criteria_applied": {
            "TRAINED_MODEL_FEASIBLE": "≥30 exact-date AND ≥10 pilot-bbox records",
            "STATIC_SUSCEPTIBILITY_MODEL_MAY_BE_FEASIBLE": (
                "≥50 geolocated records BUT 0 usable event dates → "
                "spatial density map possible, temporal ML not feasible"
            ),
            "KEEP_TRANSPARENT_PROTOTYPE_SCORER": "insufficient data for either",
        },
        "schema_fields_inspected": [
            "state", "district", "slide_name", "village",
            "latitude", "longitude", "u_lat", "u_long",
            "date", "datetimety", "date_acc", "exactdatei",
            "landslidet", "triggering", "landslides",
            "source", "geology", "class_type", "landslided",
        ],
        "date_field_findings": (
            "ALL date-related fields (date, datetimety, date_acc, exactdatei) are null or whitespace-only "
            "for all 2000 fetched Mizoram records. "
            "No event date is recoverable from this public layer for Mizoram. "
            "Dates were not inferred."
        ),
        "coordinate_findings": (
            f"All {has_coords} records have valid latitude/longitude fields. "
            f"{pilot} records fall within the Aizawl pilot bbox "
            "(92.6801°E–92.7551°E, 23.6896°N–23.7646°N). "
            f"{dups} duplicate coordinate entries (same lat/lon rounded to 5 dp)."
        ),
        "phase": 7,
        "assessed_at": "2026-09-06",
        "disclaimer": (
            "This feasibility assessment is based strictly on the REAL data obtained "
            "from the official GSI BhooSanket portal. No dates were inferred or fabricated."
        ),
    }

    FEASIBILITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FEASIBILITY_FILE, "w", encoding="utf-8") as f:
        json.dump(feasibility, f, indent=2)

    print()
    print("=" * 60)
    print(f"FEASIBILITY OUTCOME: {outcome}")
    print("=" * 60)
    print(rationale)
    print(f"\nSaved to: {FEASIBILITY_FILE}")


if __name__ == "__main__":
    main()
