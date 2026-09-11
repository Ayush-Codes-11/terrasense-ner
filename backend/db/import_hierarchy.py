"""Deterministic import of the committed prototype dataset, with no source writes."""
import json
import math
from collections import Counter
from pathlib import Path

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import MultiPolygon, shape
from shapely.validation import explain_validity
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from db.models import AnalysisZone, District, Region, State
from services.hierarchy_loader import HierarchyLoader

REPO_ROOT = Path(__file__).resolve().parents[2]
PILOT_ID = "IND-ADM2-76128533B34203923268864"
DISTRICT_COUNTS = {"IN-AR": 25, "IN-AS": 33, "IN-MN": 16, "IN-ML": 11,
                   "IN-MZ": 11, "IN-NL": 11, "IN-SK": 4, "IN-TR": 8}
ZONE_IDS = {f"{letter}{number:02}" for letter in "ABCDE" for number in range(1, 6)}
TABLES = (Region.__table__, State.__table__, District.__table__, AnalysisZone.__table__)


class DatasetValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise DatasetValidationError(message)


def to_multipolygon(geometry, feature_id):
    """Wrap Polygon rings only. Reject malformed/invalid data; never repair it."""
    try:
        require(geometry is not None, "null geometry")
        kind = geometry.get("type")
        require(kind in ("Polygon", "MultiPolygon"), "expected Polygon/MultiPolygon")
        polygons = [geometry["coordinates"]] if kind == "Polygon" else geometry["coordinates"]
        require(bool(polygons), "empty geometry")
        for polygon in polygons:
            require(bool(polygon), "empty polygon")
            for ring in polygon:
                require(len(ring) >= 4 and ring[0] == ring[-1], "ring must be closed")
                for point in ring:
                    require(len(point) == 2 and all(math.isfinite(v) for v in point),
                            "expected finite 2D coordinates")
                    require(-180 <= point[0] <= 180 and -90 <= point[1] <= 90,
                            "coordinates outside EPSG:4326 range")
        result = shape(geometry)
        require(not result.is_empty and result.is_valid, explain_validity(result))
        return MultiPolygon([result]) if kind == "Polygon" else result
    except (KeyError, TypeError, ValueError) as error:
        raise DatasetValidationError(f"{feature_id}: {error}") from error


def load_records(repo_root=REPO_ROOT):
    """Validate source contracts before any DB access, returning stable ordered rows."""
    repo_root = Path(repo_root)
    data_dir = repo_root / "data" / "geodata" / "ner"
    metadata = json.loads((data_dir / "metadata.json").read_text(encoding="utf-8"))
    require(metadata["pilot_district_id"] == PILOT_ID, "Aizawl pilot ID mismatch")
    require(metadata["dataset_source"]["adm1_states"]["boundary_vintage"] == "2011",
            "ADM1 vintage mismatch")
    require(metadata["dataset_source"]["adm2_districts"]["boundary_vintage"] == "2021",
            "ADM2 vintage mismatch")
    loader = HierarchyLoader(data_dir=data_dir)
    require(loader.available and loader.status == "READY", "HierarchyLoader is not READY")
    require(set(loader.regions) == {"NER"}, "Region set mismatch")
    require(set(loader.states) == set(DISTRICT_COUNTS), "State set mismatch")
    counts = Counter(d.state_id for d in loader.districts.values())
    require(counts == DISTRICT_COUNTS, f"District count mismatch: {dict(counts)}")
    require(all(s.region_id == "NER" for s in loader.states.values()), "State region mismatch")
    pilot = loader.districts[PILOT_ID]
    require(pilot.district_name == "Aizawl" and pilot.state_id == "IN-MZ"
            and pilot.lgd_code is None, "Aizawl record mismatch")
    require([d.district_id for d in loader.districts.values()
             if d.district_name == "Aizawl" and d.state_id == "IN-MZ"] == [PILOT_ID],
            "Aizawl must match exactly once under IN-MZ")

    records = {table.name: [] for table in TABLES}
    for region in sorted(loader.regions.values(), key=lambda r: r.region_id):
        records["regions"].append({**region.model_dump(), "source_metadata": metadata})
    for state_id, state in sorted(loader.states.items()):
        feature = loader.state_features[state_id]
        records["states"].append({
            **state.model_dump(),
            "source_metadata": {"dataset": metadata["dataset_source"]["adm1_states"],
                                "feature": feature["properties"]},
            "geometry": from_shape(to_multipolygon(feature.get("geometry"), state_id),
                                   srid=4326, extended=True),
        })
    for district_id, district in sorted(loader.districts.items()):
        feature = loader.district_features[district_id]
        records["districts"].append({
            **district.model_dump(),
            "source_metadata": {"dataset": metadata["dataset_source"]["adm2_districts"],
                                "feature": feature["properties"]},
            "geometry": from_shape(to_multipolygon(feature.get("geometry"), district_id),
                                   srid=4326, extended=True),
        })
    grid = json.loads((repo_root / "data" / "sample" / "grid-risk.geojson")
                      .read_text(encoding="utf-8"))
    features = grid["features"]
    ids = [f["properties"]["zone_id"] for f in features]
    require(len(ids) == 25 and set(ids) == ZONE_IDS, "Canonical zone IDs/count mismatch")
    for feature in sorted(features, key=lambda f: f["properties"]["zone_id"]):
        zone_id = feature["properties"]["zone_id"]
        records["analysis_zones"].append({
            "zone_id": zone_id, "district_id": PILOT_ID, "zone_type": "PROTOTYPE_ANALYSIS_GRID",
            "geometry": from_shape(to_multipolygon(feature.get("geometry"), zone_id),
                                   srid=4326, extended=True),
        })
    return records


def upsert_statement(table):
    statement = insert(table)
    return statement.on_conflict_do_update(
        index_elements=list(table.primary_key.columns),
        set_={column.name: statement.excluded[column.name]
              for column in table.columns if not column.primary_key},
    )


def validate_database(connection, records):
    """Check SQL spatial invariants and exact scalar/coordinate parity with sources."""
    counts = {}
    for table in TABLES:
        pk = list(table.primary_key.columns)[0]
        duplicates = connection.execute(
            select(pk).group_by(pk).having(func.count() > 1)).scalars().all()
        require(not duplicates, f"{table.name}: duplicate IDs {duplicates}")
        if "geometry" in table.c:
            geom = table.c.geometry
            invalid = connection.execute(select(pk, func.ST_IsValidReason(geom)).where(
                geom.is_(None) | ~func.ST_IsValid(geom) | func.ST_IsEmpty(geom)
                | (func.ST_SRID(geom) != 4326))).all()
            require(not invalid, f"{table.name}: invalid geometries {invalid}")
        actual = {row[pk.name]: row for row in connection.execute(select(table)).mappings()}
        expected = {row[pk.name]: row for row in records[table.name]}
        require(set(actual) == set(expected),
                f"{table.name}: IDs differ; missing={sorted(set(expected) - set(actual))}, "
                f"extra={sorted(set(actual) - set(expected))}")
        for feature_id, row in expected.items():
            for key, value in row.items():
                equal = (to_shape(actual[feature_id][key]).equals_exact(to_shape(value), 0)
                         if key == "geometry" else actual[feature_id][key] == value)
                require(equal, f"{table.name}/{feature_id}: {key} differs from source")
        counts[table.name] = len(actual)
    for child, parent, fk in [(State.__table__, Region.__table__, "region_id"),
                              (District.__table__, State.__table__, "state_id"),
                              (AnalysisZone.__table__, District.__table__, "district_id")]:
        parent_pk = list(parent.primary_key.columns)[0]
        orphans = connection.scalar(select(func.count()).select_from(
            child.outerjoin(parent, child.c[fk] == parent_pk)).where(parent_pk.is_(None)))
        require(orphans == 0, f"{child.name}: {orphans} orphan records")
    district_counts = dict(connection.execute(select(District.state_id, func.count())
                                             .group_by(District.state_id)).all())
    require(district_counts == DISTRICT_COUNTS, f"District count mismatch: {district_counts}")
    return {"counts": counts, "district_counts": district_counts,
            "pilot_id": PILOT_ID, "geometry_valid": True, "geometry_srid": 4326,
            "duplicates": 0, "orphans": 0, "source_parity": True}


def import_records(connection, records):
    """Caller must own a transaction: validation failure rolls back the entire import."""
    require(connection.in_transaction(), "Import requires an explicit transaction")
    for table in TABLES:
        connection.execute(upsert_statement(table), records[table.name])
    return validate_database(connection, records)
