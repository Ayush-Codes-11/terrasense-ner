"""
fetch_osm_aizawl.py — Fetches real OpenStreetMap vector features for Aizawl pilot grid
via Overpass API and saves a timestamped snapshot under data/real/osm/.

Usage:
  python backend/scripts/fetch_osm_aizawl.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root and backend are on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from backend.services.osm_fetcher import (
    get_pilot_bbox,
    build_roads_query,
    build_settlements_query,
    build_critical_facilities_query,
    execute_overpass_query,
)
from backend.services.osm_parser import (
    parse_osm_roads,
    parse_osm_settlements,
    parse_osm_critical_facilities,
)

_OUTPUT_DIR = _REPO_ROOT / "data" / "real" / "osm"


def main():
    print("=" * 70, flush=True)
    print("TerraSense NER — Real OSM Snapshot Fetcher for Aizawl Pilot", flush=True)
    print("=" * 70, flush=True)

    # 1. Derive bounding box from pilot grid
    south, west, north, east = get_pilot_bbox()
    print(f"Pilot grid bbox: south={south:.4f}, west={west:.4f}, north={north:.4f}, east={east:.4f}", flush=True)

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    # 2. Fetch roads
    print("\n[1/3] Querying Overpass for highways/roads...", flush=True)
    roads_q = build_roads_query(south, west, north, east)
    roads_raw = execute_overpass_query(roads_q)
    roads_fc = parse_osm_roads(roads_raw)
    roads_count = len(roads_fc["features"])
    print(f"  [OK] Parsed {roads_count} road features.", flush=True)

    # 3. Fetch settlements
    print("\n[2/3] Querying Overpass for settlements...", flush=True)
    settlements_q = build_settlements_query(south, west, north, east)
    settlements_raw = execute_overpass_query(settlements_q)
    settlements_fc = parse_osm_settlements(settlements_raw)
    settlements_count = len(settlements_fc["features"])
    print(f"  [OK] Parsed {settlements_count} settlement features.", flush=True)

    # 4. Fetch critical facilities
    print("\n[3/3] Querying Overpass for critical facilities...", flush=True)
    facilities_q = build_critical_facilities_query(south, west, north, east)
    facilities_raw = execute_overpass_query(facilities_q)
    facilities_fc = parse_osm_critical_facilities(facilities_raw)
    facilities_count = len(facilities_fc["features"])
    print(f"  [OK] Parsed {facilities_count} critical facility features.", flush=True)

    # 5. Save GeoJSON files
    roads_path = _OUTPUT_DIR / "roads.geojson"
    with open(roads_path, "w", encoding="utf-8") as f:
        json.dump(roads_fc, f, indent=2)

    settlements_path = _OUTPUT_DIR / "settlements.geojson"
    with open(settlements_path, "w", encoding="utf-8") as f:
        json.dump(settlements_fc, f, indent=2)

    facilities_path = _OUTPUT_DIR / "critical_facilities.geojson"
    with open(facilities_path, "w", encoding="utf-8") as f:
        json.dump(facilities_fc, f, indent=2)

    # 6. Save metadata
    metadata = {
        "data_type": "REAL_OSM",
        "source": "OpenStreetMap contributors via Overpass API",
        "retrieved_at": retrieved_at,
        "bbox": [south, west, north, east],
        "is_live": False,
        "attribution": "© OpenStreetMap contributors",
        "feature_counts": {
            "roads": roads_count,
            "settlements": settlements_count,
            "critical_facilities": facilities_count,
        },
        "file_sizes_bytes": {
            "roads.geojson": roads_path.stat().st_size,
            "settlements.geojson": settlements_path.stat().st_size,
            "critical_facilities.geojson": facilities_path.stat().st_size,
        },
    }

    metadata_path = _OUTPUT_DIR / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("\n" + "=" * 70)
    print("Snapshot saved successfully to data/real/osm/:")
    print(f"  - roads.geojson:               {roads_count} features ({roads_path.stat().st_size / 1024:.1f} KB)")
    print(f"  - settlements.geojson:         {settlements_count} features ({settlements_path.stat().st_size / 1024:.1f} KB)")
    print(f"  - critical_facilities.geojson: {facilities_count} features ({facilities_path.stat().st_size / 1024:.1f} KB)")
    print(f"  - metadata.json:               retrieved_at {retrieved_at}")
    print("=" * 70)


if __name__ == "__main__":
    main()
