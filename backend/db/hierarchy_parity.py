"""Developer/CI parity checks. Read-only and never called by production routes."""
import json

from shapely.geometry import MultiPolygon, shape

from db.hierarchy_reader import PostGISHierarchyReader
from services.data_loader import load_grid_risk
from services.hierarchy_loader import HierarchyLoader
from services.hierarchy_repository import FileHierarchyRepository


def compare_hierarchy_readers(file_loader, postgis_reader):
    file_reader = FileHierarchyRepository(file_loader)
    mismatches = []
    report = {}
    for collection in ("regions", "states", "districts"):
        left = {key: value.model_dump(mode="json")
                for key, value in getattr(file_reader, collection).items()}
        right = {key: value.model_dump(mode="json")
                 for key, value in getattr(postgis_reader, collection).items()}
        report[f"{collection}_match"] = left == right
        mismatches.extend(f"{collection}/{key}: fields differ" for key in sorted(left.keys() | right.keys())
                          if left.get(key) != right.get(key))
    file_zones = {z.zone_id: z.model_dump(mode="json") for district_id in file_reader.districts
                  for z in file_reader.get_district_zones(district_id)}
    db_zones = {z.zone_id: z.model_dump(mode="json") for district_id in postgis_reader.districts
                for z in postgis_reader.get_district_zones(district_id)}
    report["zones_match"] = file_zones == db_zones
    mismatches.extend(f"analysis_zones/{key}: fields differ" for key in sorted(file_zones.keys() | db_zones.keys())
                      if file_zones.get(key) != db_zones.get(key))

    geometry_errors = []
    metadata = json.loads((file_loader.data_dir / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("crs") != "EPSG:4326":
        geometry_errors.append("file source CRS is not EPSG:4326")
    sources = {
        "states": file_loader.state_features,
        "districts": file_loader.district_features,
        "analysis_zones": {f["properties"]["zone_id"]: f for f in load_grid_risk()["features"]},
    }
    for collection, features in sources.items():
        db_geometries = postgis_reader.geometries.get(collection, {})
        for key in sorted(features.keys() | db_geometries.keys()):
            try:
                left = shape(features[key]["geometry"])
                # Phase 3A intentionally wraps source Polygons; coordinates/rings stay identical.
                if left.geom_type == "Polygon":
                    left = MultiPolygon([left])
                right = shape(db_geometries[key])
                match = (postgis_reader.geometry_srids[collection][key] == 4326
                         and left.geom_type == right.geom_type == "MultiPolygon"
                         and left.is_valid and right.is_valid
                         and not left.is_empty and not right.is_empty
                         and left.equals(right) and left.equals_exact(right, 0))
            except (KeyError, TypeError, ValueError, AttributeError):
                match = False
            if not match:
                geometry_errors.append(f"{collection}/{key}: geometry or SRID differs")
    report["geometry_match"] = not geometry_errors
    report["mismatches"] = mismatches + geometry_errors
    return report


def compare_file_and_postgis_hierarchy(engine):
    return compare_hierarchy_readers(HierarchyLoader(),
                                     PostGISHierarchyReader(engine, include_geometry=True))
