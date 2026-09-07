"""
exposure_engine.py — Spatial exposure engine intersecting TerraSense hazard zones
with OpenStreetMap infrastructure features (roads, settlements, critical facilities).

════════════════════════════════════════════════════════════════════════════════
ARCHITECTURAL & SCIENTIFIC GUARDRAILS:
1. MIXED-PROVENANCE WARNING:
   Hazard polygons are SAMPLE_MOCK pilot geometry.
   Exposure features are REAL_OSM (with SAMPLE_MOCK fallback if cache absent).
   Analysis mode: PROTOTYPE_MIXED_PROVENANCE.

2. ROAD TERMINOLOGY DISCIPLINE:
   A road intersecting a hazard zone is strictly:
   road_status = "EXPOSED_NOT_VERIFIED_BLOCKED", blockage_verified = False.
   Never automatically mark exposure as blockage.

3. GEODESIC CLIPPED ROAD LENGTH:
   Never calculate length from raw (lon, lat) degrees.
   The road is clipped to the zone polygon first (shapely.intersection).
   Geodesic length is calculated on the clipped segment using pyproj.Geod (WGS84).

4. POINT INCLUSION:
   Uses zone.covers(point) / zone.intersects(point) to handle boundary features safely.
════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pyproj import Geod
from shapely.geometry import Point, Polygon, MultiPolygon, LineString, MultiLineString, shape
from shapely.ops import unary_union

from services.priority_config import (
    MOTORABLE_HIGHWAY_CLASSES,
    TRACK_HIGHWAY_CLASSES,
    EXCLUDED_HIGHWAY_CLASSES,
    FACILITY_WHITELIST_AMENITIES,
    FACILITY_WHITELIST_HEALTHCARE,
)

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DATA_DIR = _REPO_ROOT / "data" if (_REPO_ROOT / "data").exists() else _BACKEND_DIR / "data"
_SAMPLE_DIR = _DATA_DIR / "sample"
_REAL_OSM_DIR = _DATA_DIR / "real" / "osm"

_GEOD = Geod(ellps="WGS84")


@dataclass
class ExposedRoadItem:
    feature_id: str
    name: Optional[str]
    highway: str
    length_km: float
    is_motorable: bool = True
    access: Optional[str] = None
    access_restricted: bool = False
    blockage_verified: bool = False
    road_status: str = "EXPOSED_NOT_VERIFIED_BLOCKED"


@dataclass
class ExposedSettlementItem:
    feature_id: str
    name: Optional[str]
    place: str
    community_id: Optional[str] = None


@dataclass
class ExposedFacilityItem:
    feature_id: str
    name: Optional[str]
    category: str
    amenity: Optional[str] = None
    healthcare: Optional[str] = None
    latitude: float = 0.0
    longitude: float = 0.0
    is_whitelisted: bool = True


@dataclass
class ZoneExposureResult:
    zone_id: str
    motorable_road_km: float              # Unique unioned length of motorable network (km)
    motorable_road_segments_count: int
    osm_road_segments_count: int          # Raw count of all intersecting OSM way segments
    total_road_km: float                  # Sum of all clipped road linework (km)
    pedestrian_road_km: float             # Steps, footways, paths, pedestrian
    track_road_km: float                  # Tracks
    communities_exposed: int              # Mapped community/locality centres
    critical_facilities_exposed: int      # Whitelisted and deduplicated count
    raw_facilities_count: int

    exposed_roads: List[ExposedRoadItem]
    exposed_settlements: List[ExposedSettlementItem]
    exposed_facilities: List[ExposedFacilityItem]

    hazard_geometry: str
    exposure_features: str
    analysis_mode: str
    data_source: str
    attribution: str
    note: str

    # Backward compatibility properties
    @property
    def road_feature_count(self) -> int:
        return self.osm_road_segments_count

    @property
    def road_length_km(self) -> float:
        return self.motorable_road_km

    @property
    def settlements_exposed(self) -> int:
        return self.communities_exposed


def _calc_linestring_length_km(geom) -> float:
    """
    Calculates geodesic length in kilometers using pyproj.Geod(ellps='WGS84').
    Handles LineString, MultiLineString, and GeometryCollection.
    """
    if geom is None or geom.is_empty:
        return 0.0

    total_m = 0.0
    geom_type = geom.geom_type

    if geom_type == "LineString":
        coords = list(geom.coords)
        if len(coords) >= 2:
            lons = [p[0] for p in coords]
            lats = [p[1] for p in coords]
            total_m += _GEOD.line_length(lons, lats)
    elif geom_type == "MultiLineString":
        for part in geom.geoms:
            total_m += _calc_linestring_length_km(part) * 1000.0
    elif geom_type == "GeometryCollection":
        for part in geom.geoms:
            if part.geom_type in ("LineString", "MultiLineString"):
                total_m += _calc_linestring_length_km(part) * 1000.0

    return round(total_m / 1000.0, 4)


def get_osm_provenance_status() -> Dict[str, Any]:
    """
    Returns the current status of the OSM data layer:
    - 'OSM snapshot' if real OSM files exist
    - 'Cached OSM' if metadata indicates cached
    - 'Sample fallback' if real files do not exist
    """
    meta_path = _REAL_OSM_DIR / "metadata.json"
    roads_path = _REAL_OSM_DIR / "roads.geojson"

    if roads_path.exists() and meta_path.exists():
        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            return {
                "status": "OSM snapshot",
                "is_real": True,
                "retrieved_at": meta.get("retrieved_at"),
                "source": meta.get("source", "OpenStreetMap contributors via Overpass API"),
                "attribution": meta.get("attribution", "© OpenStreetMap contributors"),
                "feature_counts": meta.get("feature_counts", {}),
                "layers_retrieved_at": meta.get("layers_retrieved_at", {}),
                "dataset_description": meta.get("dataset_description", "Cached multi-layer OpenStreetMap dataset"),
            }
        except Exception:
            return {
                "status": "Cached OSM",
                "is_real": True,
                "retrieved_at": None,
                "source": "OpenStreetMap contributors (Cached)",
                "attribution": "© OpenStreetMap contributors",
                "feature_counts": {},
            }

    return {
        "status": "Sample fallback",
        "is_real": False,
        "retrieved_at": None,
        "source": "TerraSense Sample Mock Geodata",
        "attribution": "Sample fallback data",
        "feature_counts": {},
    }


from functools import lru_cache

@lru_cache(maxsize=1)
def load_exposure_layers() -> Tuple[dict, dict, dict, str, str]:
    """
    Loads roads, settlements, and critical facilities.
    Prioritizes data/real/osm/. Falls back gracefully to data/sample/.
    Cached in memory for high-performance response times.
    """
    real_roads = _REAL_OSM_DIR / "roads.geojson"
    real_settlements = _REAL_OSM_DIR / "settlements.geojson"
    real_facilities = _REAL_OSM_DIR / "critical_facilities.geojson"

    if real_roads.exists() and real_settlements.exists() and real_facilities.exists():
        with open(real_roads, encoding="utf-8") as f:
            roads_fc = json.load(f)
        with open(real_settlements, encoding="utf-8") as f:
            settlements_fc = json.load(f)
        with open(real_facilities, encoding="utf-8") as f:
            facilities_fc = json.load(f)
        return (
            roads_fc,
            settlements_fc,
            facilities_fc,
            "REAL_OSM",
            "OpenStreetMap contributors via Overpass API",
        )

    # Fallback to sample
    with open(_SAMPLE_DIR / "roads.geojson", encoding="utf-8") as f:
        roads_fc = json.load(f)
    with open(_SAMPLE_DIR / "villages.geojson", encoding="utf-8") as f:
        settlements_fc = json.load(f)
    with open(_SAMPLE_DIR / "hospitals.geojson", encoding="utf-8") as f:
        facilities_fc = json.load(f)

    return (
        roads_fc,
        settlements_fc,
        facilities_fc,
        "SAMPLE_MOCK",
        "TerraSense Sample Mock Geodata",
    )


def _conservative_dedup_facilities(fac_items: List[ExposedFacilityItem]) -> List[ExposedFacilityItem]:
    """
    Conservative deduplication of critical facilities:
    Merges facilities with identical or fuzzy-matching names in close physical proximity (<=50m exact, <=30m fuzzy).
    Never merges facilities solely because they are nearby.
    """
    deduped: List[ExposedFacilityItem] = []
    seen: List[Tuple[str, str, Tuple[float, float], ExposedFacilityItem]] = []

    for item in fac_items:
        norm_name = (item.name or "").lower().strip()
        cat = item.category
        coords = (item.longitude, item.latitude)

        is_dup = False
        for s_name, s_cat, s_coords, s_item in seen:
            if cat == s_cat or not cat or not s_cat:
                dist = _GEOD.line_length([coords[0], s_coords[0]], [coords[1], s_coords[1]])
                # Exact normalized name match <= 50m
                if norm_name and s_name and norm_name == s_name and dist <= 50.0:
                    is_dup = True
                    break
                # Conservative fuzzy match (stem containment) <= 30m
                if norm_name and s_name and (norm_name in s_name or s_name in norm_name) and dist <= 30.0:
                    is_dup = True
                    break

        if not is_dup:
            seen.append((norm_name, cat, coords, item))
            deduped.append(item)

    return deduped


def get_critical_facilities_feature_collection(raw: bool = False) -> Tuple[dict, str, str]:
    """
    Returns critical facilities FeatureCollection.
    If raw=False (default): returns the 20 whitelisted & conservatively deduplicated
    critical facilities across the pilot area, strictly matching exposure engine semantics.
    If raw=True: returns the un-deduplicated 31 OSM healthcare/emergency features.
    """
    roads_fc, settlements_fc, facilities_fc, data_type, src = load_exposure_layers()
    if raw or data_type == "SAMPLE_MOCK":
        return facilities_fc, data_type, src

    raw_facilities: List[ExposedFacilityItem] = []
    for cf in facilities_fc.get("features", []):
        props = cf.get("properties", {})
        amenity = props.get("amenity")
        healthcare = props.get("healthcare")
        category_val = str(props.get("category") or props.get("facility_type", "")).lower()
        coords = cf.get("geometry", {}).get("coordinates", [])
        if coords and len(coords) >= 2:
            lon, lat = coords[0], coords[1]
        else:
            continue
        if amenity is not None or healthcare is not None:
            is_whitelisted = (amenity in FACILITY_WHITELIST_AMENITIES or healthcare in FACILITY_WHITELIST_HEALTHCARE)
        else:
            is_whitelisted = category_val in FACILITY_WHITELIST_AMENITIES

        if is_whitelisted:
            raw_facilities.append(
                ExposedFacilityItem(
                    feature_id=str(props.get("facility_id") or props.get("osm_id") or cf.get("id", "facility")),
                    name=props.get("name"),
                    category=str(props.get("category") or props.get("facility_type", "facility")),
                    amenity=amenity,
                    healthcare=healthcare,
                    latitude=lat,
                    longitude=lon,
                    is_whitelisted=True,
                )
            )

    deduped = _conservative_dedup_facilities(raw_facilities)
    deduped_features = [
        {
            "type": "Feature",
            "id": f"osm_facility_{d.category}_{d.feature_id}",
            "properties": {
                "osm_id": d.feature_id,
                "facility_id": d.feature_id,
                "name": d.name,
                "category": d.category,
                "amenity": d.amenity,
                "healthcare": d.healthcare,
                "is_whitelisted": True,
                "data_type": "REAL_OSM",
                "source": "OpenStreetMap contributors",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [d.longitude, d.latitude],
            },
        }
        for d in deduped
    ]

    return {
        "type": "FeatureCollection",
        "features": deduped_features,
    }, data_type, src


def compute_zone_exposure(
    zone_id: str,
    roads_fc: Optional[dict] = None,
    settlements_fc: Optional[dict] = None,
    facilities_fc: Optional[dict] = None,
) -> ZoneExposureResult:
    """
    Computes road, settlement, and critical-facility exposure for a single zone polygon.
    Clips road geometries to the zone polygon and calculates unique motorable network length
    using unary_union to prevent double-counting overlapping lines.
    Filters critical facilities through whitelist and conservative deduplication.
    """
    zid = zone_id.upper()

    # 1. Load zone polygon
    with open(_SAMPLE_DIR / "grid-risk.geojson", encoding="utf-8") as f:
        grid_fc = json.load(f)

    zone_feature = None
    for f in grid_fc.get("features", []):
        if str(f.get("properties", {}).get("zone_id", "")).upper() == zid:
            zone_feature = f
            break

    if not zone_feature:
        raise KeyError(f"Zone '{zid}' not found in pilot grid geometry.")

    zone_geom = shape(zone_feature["geometry"])

    # 2. Load layers if not provided
    if roads_fc is None or settlements_fc is None or facilities_fc is None:
        r_fc, s_fc, f_fc, exp_type, src = load_exposure_layers()
        roads_fc = roads_fc or r_fc
        settlements_fc = settlements_fc or s_fc
        facilities_fc = facilities_fc or f_fc
    else:
        exp_type = "REAL_OSM"
        src = "OpenStreetMap contributors"

    # 3. Intersect roads & compute unique motorable network length
    exposed_roads: List[ExposedRoadItem] = []
    total_road_km = 0.0
    pedestrian_road_km = 0.0
    track_road_km = 0.0
    osm_road_segments_count = 0
    motorable_segments_count = 0
    motorable_lines: List[LineString] = []
    z_minx, z_miny, z_maxx, z_maxy = zone_geom.bounds

    for rf in roads_fc.get("features", []):
        geom_dict = rf.get("geometry", {})
        coords = geom_dict.get("coordinates", [])
        if not coords:
            continue

        # Fast bbox rejection before creating full Shapely shape
        if geom_dict.get("type") == "LineString":
            r_minx = min(pt[0] for pt in coords)
            r_maxx = max(pt[0] for pt in coords)
            r_miny = min(pt[1] for pt in coords)
            r_maxy = max(pt[1] for pt in coords)
            if r_maxx < z_minx or r_minx > z_maxx or r_maxy < z_miny or r_miny > z_maxy:
                continue

        r_geom = shape(geom_dict)
        if not r_geom.intersects(zone_geom):
            continue

        clipped = r_geom.intersection(zone_geom)
        if clipped.is_empty:
            continue

        part_km = _calc_linestring_length_km(clipped)
        if part_km <= 0.0:
            continue

        osm_road_segments_count += 1
        total_road_km += part_km

        props = rf.get("properties", {})
        hw = str(props.get("highway") or props.get("road_type", "road"))
        access = props.get("access")
        vehicle = props.get("vehicle")
        motor_vehicle = props.get("motor_vehicle")

        is_track = hw in TRACK_HIGHWAY_CLASSES
        is_excluded = hw in EXCLUDED_HIGHWAY_CLASSES
        is_explicit_no_access = (access == "no" or vehicle == "no" or motor_vehicle == "no")
        is_private = (access == "private")

        if is_track:
            track_road_km += part_km
            is_motorable = False
        elif is_excluded or is_explicit_no_access:
            if is_excluded:
                pedestrian_road_km += part_km
            is_motorable = False
        elif hw in MOTORABLE_HIGHWAY_CLASSES or exp_type == "SAMPLE_MOCK":
            is_motorable = True
            motorable_segments_count += 1
            if isinstance(clipped, LineString):
                motorable_lines.append(clipped)
            elif isinstance(clipped, MultiLineString):
                motorable_lines.extend(clipped.geoms)
            elif hasattr(clipped, "geoms"):
                for g in clipped.geoms:
                    if isinstance(g, LineString):
                        motorable_lines.append(g)
        else:
            is_motorable = False

        exposed_roads.append(
            ExposedRoadItem(
                feature_id=str(props.get("road_id") or props.get("osm_id") or rf.get("id", "road")),
                name=props.get("name"),
                highway=hw,
                length_km=round(part_km, 3),
                is_motorable=is_motorable,
                access=access,
                access_restricted=is_private or is_explicit_no_access,
                blockage_verified=False,
                road_status="EXPOSED_NOT_VERIFIED_BLOCKED",
            )
        )

    # Calculate unique motorable network length using unary_union.
    # unary_union removes duplicate and overlapping linework while preserving
    # geometrically distinct parallel carriageways (legitimate dual carriageways are not collapsed into one).
    if motorable_lines:
        union_geom = unary_union(motorable_lines)
        unique_motorable_road_km = _calc_linestring_length_km(union_geom)
    else:
        unique_motorable_road_km = 0.0

    # 4. Intersect mapped community/locality centres
    exposed_settlements: List[ExposedSettlementItem] = []
    for sf in settlements_fc.get("features", []):
        coords = sf.get("geometry", {}).get("coordinates", [])
        if not coords or len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        if lon < z_minx or lon > z_maxx or lat < z_miny or lat > z_maxy:
            continue
        s_geom = Point(lon, lat)
        if zone_geom.covers(s_geom) or zone_geom.intersects(s_geom):
            props = sf.get("properties", {})
            exposed_settlements.append(
                ExposedSettlementItem(
                    feature_id=str(props.get("community_id") or props.get("village_id") or props.get("osm_id") or sf.get("id", "community")),
                    name=props.get("name"),
                    place=str(props.get("place", "locality")),
                    community_id=props.get("community_id") or props.get("village_id"),
                )
            )

    # 5. Intersect critical facilities with whitelist filtering
    raw_facilities: List[ExposedFacilityItem] = []
    for cf in facilities_fc.get("features", []):
        coords = cf.get("geometry", {}).get("coordinates", [])
        if not coords or len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        if lon < z_minx or lon > z_maxx or lat < z_miny or lat > z_maxy:
            continue
        c_geom = Point(lon, lat)
        if zone_geom.covers(c_geom) or zone_geom.intersects(c_geom):
            props = cf.get("properties", {})
            amenity = props.get("amenity")
            healthcare = props.get("healthcare")
            category_val = str(props.get("category") or props.get("facility_type", "")).lower()
            if exp_type == "SAMPLE_MOCK":
                is_whitelisted = category_val in FACILITY_WHITELIST_AMENITIES or True
            elif amenity is not None or healthcare is not None:
                is_whitelisted = (
                    amenity in FACILITY_WHITELIST_AMENITIES
                    or healthcare in FACILITY_WHITELIST_HEALTHCARE
                )
            else:
                is_whitelisted = category_val in FACILITY_WHITELIST_AMENITIES
            if is_whitelisted:
                raw_facilities.append(
                    ExposedFacilityItem(
                        feature_id=str(props.get("facility_id") or props.get("osm_id") or cf.get("id", "facility")),
                        name=props.get("name"),
                        category=str(props.get("category") or props.get("facility_type", "facility")),
                        amenity=amenity,
                        healthcare=healthcare,
                        latitude=lat,
                        longitude=lon,
                        is_whitelisted=True,
                    )
                )

    deduped_facilities = _conservative_dedup_facilities(raw_facilities)

    mode = "PROTOTYPE_MIXED_PROVENANCE" if exp_type == "REAL_OSM" else "SAMPLE_FALLBACK"

    return ZoneExposureResult(
        zone_id=zid,
        motorable_road_km=round(unique_motorable_road_km, 3),
        motorable_road_segments_count=motorable_segments_count,
        osm_road_segments_count=osm_road_segments_count,
        total_road_km=round(total_road_km, 3),
        pedestrian_road_km=round(pedestrian_road_km, 3),
        track_road_km=round(track_road_km, 3),
        communities_exposed=len(exposed_settlements),
        critical_facilities_exposed=len(deduped_facilities),
        raw_facilities_count=len(raw_facilities),
        exposed_roads=exposed_roads,
        exposed_settlements=exposed_settlements,
        exposed_facilities=deduped_facilities,
        hazard_geometry="SAMPLE_MOCK",
        exposure_features=exp_type,
        analysis_mode=mode,
        data_source=src,
        attribution="© OpenStreetMap contributors" if exp_type == "REAL_OSM" else "Sample fallback",
        note=(
            "Mixed-provenance prototype analysis: SAMPLE_MOCK hazard polygon intersected with "
            + ("REAL_OSM vector features. Not operationally validated." if exp_type == "REAL_OSM" else "SAMPLE_MOCK features.")
        ),
    )
