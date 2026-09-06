"""
osm_parser.py — Parses Overpass JSON elements into clean GeoJSON FeatureCollections.

════════════════════════════════════════════════════════════════════════════════
RULES:
1. Complete geometry / center handling:
   - Ways with 'geometry' -> LineString.
   - Nodes with 'lat'/'lon' -> Point.
   - Ways/relations with 'center' -> Point (OSM center used for exposure counting).
2. Deduplicate objects using (element['type'], element['id']).
3. Preserve useful tags without fabricating missing names.
4. Clean GeoJSON FeatureCollections with properties:
   - osm_type, osm_id, name, category, and relevant tags.
════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


def parse_osm_roads(data: dict) -> dict:
    """
    Parses Overpass JSON elements into a GeoJSON FeatureCollection of roads.
    Preserves: highway, name, ref, bridge, tunnel, surface tags.
    """
    elements = data.get("elements", [])
    features: List[dict] = []
    seen: Set[Tuple[str, int]] = set()

    for el in elements:
        el_type = el.get("type")
        el_id = el.get("id")
        if not el_type or el_id is None:
            continue

        key = (el_type, el_id)
        if key in seen:
            continue
        seen.add(key)

        tags = el.get("tags", {})
        if "highway" not in tags:
            continue

        # Extract coordinates from way geometry
        geom_points = el.get("geometry", [])
        if not geom_points or len(geom_points) < 2:
            continue

        # GeoJSON is [longitude, latitude]
        coords = [[pt["lon"], pt["lat"]] for pt in geom_points if "lon" in pt and "lat" in pt]
        if len(coords) < 2:
            continue

        name = tags.get("name")  # Do NOT fabricate missing road names
        highway_type = tags.get("highway", "road")

        props = {
            "osm_type": el_type,
            "osm_id": el_id,
            "road_id": f"OSM_{el_type[0].upper()}{el_id}",
            "name": name,
            "highway": highway_type,
            "ref": tags.get("ref"),
            "bridge": tags.get("bridge"),
            "tunnel": tags.get("tunnel"),
            "surface": tags.get("surface"),
            "service": tags.get("service"),
            "access": tags.get("access"),
            "vehicle": tags.get("vehicle"),
            "motor_vehicle": tags.get("motor_vehicle"),
            "source": "OpenStreetMap contributors",
            "data_type": "REAL_OSM",
            "blockage_verified": False,
            "road_status": "EXPOSED_NOT_VERIFIED_BLOCKED",
        }

        features.append({
            "type": "Feature",
            "id": f"osm_way_{el_id}",
            "properties": props,
            "geometry": {
                "type": "LineString",
                "coordinates": coords,
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def parse_osm_settlements(data: dict) -> dict:
    """
    Parses Overpass JSON elements into a GeoJSON FeatureCollection of settlements.
    Uses point coordinates for nodes, or element 'center' for ways/relations (documented MVP behavior).
    """
    elements = data.get("elements", [])
    features: List[dict] = []
    seen: Set[Tuple[str, int]] = set()

    for el in elements:
        el_type = el.get("type")
        el_id = el.get("id")
        if not el_type or el_id is None:
            continue

        key = (el_type, el_id)
        if key in seen:
            continue
        seen.add(key)

        tags = el.get("tags", {})
        place_type = tags.get("place")
        if not place_type:
            continue

        # Extract coordinate: node lat/lon or way/relation center
        lon: Optional[float] = None
        lat: Optional[float] = None

        if el_type == "node" and "lat" in el and "lon" in el:
            lat = el["lat"]
            lon = el["lon"]
        elif "center" in el and "lat" in el["center"] and "lon" in el["center"]:
            lat = el["center"]["lat"]
            lon = el["center"]["lon"]

        if lat is None or lon is None:
            continue

        name = tags.get("name")
        props = {
            "osm_type": el_type,
            "osm_id": el_id,
            "community_id": f"OSM_{el_type[0].upper()}{el_id}",
            "village_id": f"OSM_{el_type[0].upper()}{el_id}",
            "name": name,
            "place": place_type,
            "population": tags.get("population"),
            "admin_level": tags.get("admin_level"),
            "source": "OpenStreetMap contributors",
            "data_type": "REAL_OSM",
        }

        features.append({
            "type": "Feature",
            "id": f"osm_settlement_{el_type}_{el_id}",
            "properties": props,
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def parse_osm_critical_facilities(data: dict) -> dict:
    """
    Parses Overpass JSON elements into a GeoJSON FeatureCollection of critical facilities
    (hospitals, clinics, police, fire stations, healthcare facilities).
    """
    elements = data.get("elements", [])
    features: List[dict] = []
    seen: Set[Tuple[str, int]] = set()

    for el in elements:
        el_type = el.get("type")
        el_id = el.get("id")
        if not el_type or el_id is None:
            continue

        key = (el_type, el_id)
        if key in seen:
            continue
        seen.add(key)

        tags = el.get("tags", {})
        amenity = tags.get("amenity")
        healthcare = tags.get("healthcare")

        category: Optional[str] = None
        if amenity in ("hospital", "clinic") or healthcare:
            category = "hospital" if amenity == "hospital" else "clinic"
        elif amenity == "police":
            category = "police"
        elif amenity == "fire_station":
            category = "fire_station"
        else:
            continue

        # Extract coordinate: node lat/lon or way/relation center
        lon: Optional[float] = None
        lat: Optional[float] = None

        if el_type == "node" and "lat" in el and "lon" in el:
            lat = el["lat"]
            lon = el["lon"]
        elif "center" in el and "lat" in el["center"] and "lon" in el["center"]:
            lat = el["center"]["lat"]
            lon = el["center"]["lon"]

        if lat is None or lon is None:
            continue

        name = tags.get("name")
        props = {
            "osm_type": el_type,
            "osm_id": el_id,
            "facility_id": f"OSM_{el_type[0].upper()}{el_id}",
            "name": name,
            "category": category,
            "amenity": amenity,
            "healthcare": healthcare,
            "operator": tags.get("operator"),
            "emergency": tags.get("emergency"),
            "source": "OpenStreetMap contributors",
            "data_type": "REAL_OSM",
        }

        features.append({
            "type": "Feature",
            "id": f"osm_facility_{el_type}_{el_id}",
            "properties": props,
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }
