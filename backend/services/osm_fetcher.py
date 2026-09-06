"""
osm_fetcher.py — Overpass API query and fetch service for TerraSense NER.

════════════════════════════════════════════════════════════════════════════════
OFFICIAL DATA & ARCHITECTURAL SEMANTICS:
- Source: OpenStreetMap contributors
- Access: Overpass API
- Data type: Vector (GeoJSON FeatureCollection snapshots)
- Attribution required: "© OpenStreetMap contributors"
- Temporal behaviour: Treated as timestamped snapshots, NEVER labelled "live".
- Spatial bounding box: Derived directly from the TerraSense pilot hazard grid.
════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_GRID_RISK_PATH = _REPO_ROOT / "data" / "sample" / "grid-risk.geojson"

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def get_pilot_bbox() -> Tuple[float, float, float, float]:
    """
    Derives the exact (south, west, north, east) bounding box from the
    TerraSense pilot grid geometry.
    """
    if not _GRID_RISK_PATH.exists():
        raise FileNotFoundError(f"Pilot grid GeoJSON not found at {_GRID_RISK_PATH}")

    with open(_GRID_RISK_PATH, encoding="utf-8") as f:
        fc = json.load(f)

    lons: List[float] = []
    lats: List[float] = []

    for feature in fc.get("features", []):
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [])
        geom_type = geom.get("type", "")

        if geom_type == "Polygon":
            for ring in coords:
                for pt in ring:
                    lons.append(float(pt[0]))
                    lats.append(float(pt[1]))
        elif geom_type == "MultiPolygon":
            for poly in coords:
                for ring in poly:
                    for pt in ring:
                        lons.append(float(pt[0]))
                        lats.append(float(pt[1]))

    if not lons or not lats:
        raise ValueError("No coordinates found in pilot grid GeoJSON.")

    south = min(lats)
    west = min(lons)
    north = max(lats)
    east = max(lons)

    return south, west, north, east


def build_roads_query(south: float, west: float, north: float, east: float) -> str:
    """
    Builds Overpass QL query for highways/roads returning complete geometry and tags.
    """
    return f"""[out:json][timeout:60];
(
  way["highway"]({south},{west},{north},{east});
);
out tags geom;
"""


def build_settlements_query(south: float, west: float, north: float, east: float) -> str:
    """
    Builds Overpass QL query for mapped community/locality centres returning tags and centers.
    Includes city, town, village, hamlet, suburb, neighbourhood, quarter, locality.
    """
    return f"""[out:json][timeout:60];
(
  nwr["place"~"^(city|town|village|hamlet|suburb|neighbourhood|quarter|locality)$"]({south},{west},{north},{east});
);
out tags center;
"""


def build_critical_facilities_query(south: float, west: float, north: float, east: float) -> str:
    """
    Builds Overpass QL query for hospitals, clinics, police, and fire stations.
    """
    return f"""[out:json][timeout:60];
(
  nwr["amenity"~"hospital|clinic|police|fire_station"]({south},{west},{north},{east});
  nwr["healthcare"]({south},{west},{north},{east});
);
out tags center;
"""


def execute_overpass_query(
    query: str,
    timeout_sec: float = 60.0,
    endpoints: Optional[List[str]] = None,
) -> dict:
    """
    Executes an Overpass QL query against Overpass API endpoints with automatic fallback.
    """
    servers = endpoints or OVERPASS_ENDPOINTS
    headers = {
        "User-Agent": "TerraSense-NER/1.0 (Landslide Early Warning Research; Python/httpx)",
        "Accept": "application/json",
    }

    last_error: Optional[Exception] = None
    for endpoint in servers:
        try:
            print(f"  -> Connecting to {endpoint}...", flush=True)
            with httpx.Client(timeout=timeout_sec, follow_redirects=True) as client:
                resp = client.post(endpoint, data={"data": query}, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if "elements" in data:
                        return data
                    raise ValueError(f"Overpass response missing 'elements': {data.keys()}")
                elif resp.status_code in (429, 504):
                    print(f"  -> Server returned {resp.status_code}, trying next mirror...", flush=True)
                    continue
                else:
                    resp.raise_for_status()
        except Exception as exc:
            print(f"  -> Attempt failed ({exc}), trying next mirror...", flush=True)
            last_error = exc
            continue

    raise RuntimeError(
        f"All Overpass API endpoints failed. Last error: {last_error}"
    ) from last_error
