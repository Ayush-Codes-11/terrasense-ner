"""
gsi_inventory.py — GSI BhooSanket Landslide Inventory service for TerraSense NER.

Data source:
  GSI BhooSanket Public Portal — Landslide_Public layer
  URL: https://bhusanket.gsi.gov.in/gisserver/rest/services/Hosted/Public_Portal_Dashboard_Map/FeatureServer/0
  Access: Publicly accessible without authentication.
  Note:  The original /India_All_Landslided FeatureServer (on the same gsi.gov.in domain)
         requires an authenticated GIS token (HTTP 499). The Hosted/Public_Portal_Dashboard_Map
         FeatureServer is the public-facing equivalent and is accessible without credentials.

Phase 7: Load and audit the cached Mizoram GSI records.
         Feasibility gate is based on real record inspection.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LANDSLIDE_DIR = _REPO_ROOT / "data" / "real" / "landslides"
_RAW_FILE = _LANDSLIDE_DIR / "gsi_mizoram_raw.json"
_FEASIBILITY_FILE = _LANDSLIDE_DIR / "model_feasibility.json"

PILOT_BBOX = (92.6801, 23.6896, 92.7551, 23.7646)  # xmin, ymin, xmax, ymax


@lru_cache(maxsize=1)
def load_raw_records() -> Dict[str, Any]:
    """Load and cache the raw Mizoram GSI records from disk."""
    if _RAW_FILE.exists():
        try:
            with open(_RAW_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: could not read GSI raw file: {e}")
    return {"retrieved_features": []}


def get_all_mizoram_records() -> List[Dict[str, Any]]:
    """Returns all raw GSI feature records for Mizoram."""
    return load_raw_records().get("retrieved_features", [])


def _has_usable_date(attrs: Dict[str, Any]) -> bool:
    """Returns True if the record has a non-empty, non-whitespace date."""
    for field in ("date", "date_acc", "datetimety", "exactdatei"):
        val = attrs.get(field)
        if val and str(val).strip() and str(val).strip() not in (" ", ""):
            return True
    return False


def _has_coordinates(feature: Dict[str, Any]) -> bool:
    """Returns True if feature has valid lat/lon from attributes or geometry."""
    attrs = feature.get("attributes", {})
    geom = feature.get("geometry", {})
    lat = attrs.get("latitude") or attrs.get("u_lat") or geom.get("y")
    lon = attrs.get("longitude") or attrs.get("u_long") or geom.get("x")
    if lat is None or lon is None:
        return False
    try:
        float(lat)
        float(lon)
        return True
    except (TypeError, ValueError):
        return False


def _get_coords(feature: Dict[str, Any]):
    """Returns (lat, lon) floats or (None, None)."""
    attrs = feature.get("attributes", {})
    geom = feature.get("geometry", {})
    lat = attrs.get("latitude") or attrs.get("u_lat") or geom.get("y")
    lon = attrs.get("longitude") or attrs.get("u_long") or geom.get("x")
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None, None


def audit_records() -> Dict[str, Any]:
    """
    Audits the cached GSI Mizoram records.

    Returns counts for:
    - total Mizoram records
    - records by district
    - pilot-bbox records
    - records with usable coordinates
    - records with exact dates (YYYY-MM-DD)
    - records with partial dates (any non-empty date field)
    - records with no date
    - duplicate coordinate pairs
    """
    records = get_all_mizoram_records()
    xmin, ymin, xmax, ymax = PILOT_BBOX

    by_district: Dict[str, int] = {}
    pilot_count = 0
    has_coords = 0
    exact_dates = 0
    partial_dates = 0
    no_date = 0
    coord_pairs: Dict[tuple, int] = {}

    for feat in records:
        attrs = feat.get("attributes", {})

        # District count
        dist = str(attrs.get("district", "Unknown")).strip()
        by_district[dist] = by_district.get(dist, 0) + 1

        # Coordinate check
        lat, lon = _get_coords(feat)
        if lat is not None and lon is not None:
            has_coords += 1
            key = (round(lat, 5), round(lon, 5))
            coord_pairs[key] = coord_pairs.get(key, 0) + 1
            # Pilot bbox check
            if xmin <= lon <= xmax and ymin <= lat <= ymax:
                pilot_count += 1

        # Date quality
        date_val = str(attrs.get("date", "") or "").strip()
        if date_val and date_val != " " and len(date_val) > 1:
            # Check for YYYY-MM-DD format
            if (
                len(date_val) >= 10
                and (date_val[4] == "-" or date_val[4] == "/")
                and date_val[:4].isdigit()
            ):
                exact_dates += 1
            else:
                partial_dates += 1
        else:
            no_date += 1

    dup_pairs = sum(1 for v in coord_pairs.values() if v > 1)
    dup_records = sum(v - 1 for v in coord_pairs.values() if v > 1)

    return {
        "total_mizoram": len(records),
        "by_district": by_district,
        "pilot_bbox_count": pilot_count,
        "has_usable_coordinates": has_coords,
        "exact_date_records": exact_dates,
        "partial_date_records": partial_dates,
        "no_date_records": no_date,
        "duplicate_coordinate_pairs": dup_pairs,
        "duplicate_records_total": dup_records,
    }


def load_feasibility_result() -> Optional[Dict[str, Any]]:
    """Loads the model feasibility gate result from disk."""
    if _FEASIBILITY_FILE.exists():
        try:
            with open(_FEASIBILITY_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None
