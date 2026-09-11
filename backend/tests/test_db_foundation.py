import io
import json
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from geoalchemy2.shape import to_shape
from sqlalchemy.dialects import postgresql

from db.base import Base
from db.import_hierarchy import (
    DISTRICT_COUNTS, PILOT_ID, TABLES, DatasetValidationError,
    load_records, to_multipolygon, upsert_statement,
)
from db.session import DatabaseConfigurationError, create_db_engine, database_url

ROOT = Path(__file__).resolve().parents[2]
LOCAL_URL = "postgresql+psycopg://terrasense:terrasense@localhost:5432/terrasense"


def test_database_config_is_explicit_and_optional(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(DatabaseConfigurationError, match="required"):
        database_url()
    monkeypatch.setenv("DATABASE_URL", LOCAL_URL)
    url = database_url()
    assert (url.drivername, url.host, url.port, url.database) == (
        "postgresql+psycopg", "localhost", 5432, "terrasense")
    assert database_url(LOCAL_URL.replace("terrasense@", "p%40ss%25@")).password == "p@ss%"


@pytest.mark.parametrize("value", ["sqlite:///test.db", "postgresql://user:secret@host/db",
                                  "postgresql+psycopg://user:secret@host",
                                  "postgresql+psycopg://user:secret@host:bad/db",
                                  "postgresql+psycopg://user:secret@host:99999/db",
                                  "not-a-url"])
def test_invalid_database_urls_do_not_expose_credentials(value):
    with pytest.raises(DatabaseConfigurationError) as error:
        database_url(value)
    assert "secret" not in str(error.value)


def test_engine_creation_does_not_connect():
    engine = create_db_engine(LOCAL_URL)
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
        assert engine.pool.checkedout() == 0
    finally:
        engine.dispose()


def test_runtime_app_has_no_database_requirement(monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/regions").json()["count"] == 1


def test_schema_has_required_keys_spatial_indexes_and_constraints():
    assert set(Base.metadata.tables) == {"regions", "states", "districts", "analysis_zones"}
    for table in TABLES:
        assert len(table.primary_key.columns) == 1
        if table.name == "regions":
            continue
        geom = table.c.geometry
        assert geom.type.geometry_type == "MULTIPOLYGON"
        assert geom.type.srid == 4326 and not geom.nullable
        assert len(table.foreign_keys) == 1
        assert all(not fk.parent.nullable for fk in table.foreign_keys)
        indexes = {i.name: i for i in table.indexes}
        assert indexes[f"ix_{table.name}_geometry"].dialect_options["postgresql"]["using"] == "gist"
        assert f"ck_{table.name}_geometry_valid" in {c.name for c in table.constraints}


def test_polygon_wrapping_preserves_rings_and_coordinates():
    coordinates = [[[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]],
                   [[1, 1], [1, 2], [2, 2], [2, 1], [1, 1]]]
    polygon = {"type": "Polygon", "coordinates": coordinates}
    multi = to_multipolygon(polygon, "test-polygon")
    assert multi.geom_type == "MultiPolygon"
    assert list(multi.geoms[0].exterior.coords) == [tuple(p) for p in coordinates[0]]
    assert list(multi.geoms[0].interiors[0].coords) == [tuple(p) for p in coordinates[1]]
    assert multi.equals_exact(to_multipolygon(
        {"type": "MultiPolygon", "coordinates": [coordinates]}, "test-multi"), 0)


@pytest.mark.parametrize("geometry", [None, {"type": "Point", "coordinates": [0, 0]},
    {"type": "Polygon", "coordinates": []},
    {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]},
    {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]},
    {"type": "Polygon", "coordinates": [[[0, 0], [181, 0], [1, 1], [0, 0]]]},
])
def test_invalid_geometry_reports_feature_id_without_repair(geometry):
    with pytest.raises(DatasetValidationError, match="broken-feature"):
        to_multipolygon(geometry, "broken-feature")


def test_canonical_mapping_is_deterministic_and_preserves_source_data():
    first, second = load_records(), load_records()
    assert {k: len(v) for k, v in first.items()} == {
        "regions": 1, "states": 8, "districts": 119, "analysis_zones": 25}
    for table in TABLES:
        pk = list(table.primary_key.columns)[0].name
        assert [r[pk] for r in first[table.name]] == sorted(r[pk] for r in first[table.name])
        for left, right in zip(first[table.name], second[table.name]):
            assert left == right
            if "geometry" in left:
                assert left["geometry"].srid == 4326
                assert to_shape(left["geometry"]).is_valid
    states = first["states"]
    assert {r["state_id"] for r in states} == set(DISTRICT_COUNTS)
    assert all(r["region_id"] == "NER" for r in states)
    districts = first["districts"]
    pilot = next(r for r in districts if r["district_id"] == PILOT_ID)
    assert (pilot["district_name"], pilot["state_id"], pilot["lgd_code"],
            pilot["coverage_level"], pilot["risk_model_status"]) == (
        "Aizawl", "IN-MZ", None, "DETAILED_PILOT", "STATIC_ML_VALIDATION_PENDING")
    assert all(r["coverage_level"] == "DISTRICT_BOUNDARY_ONLY"
               and r["risk_model_status"] == "NOT_IMPLEMENTED"
               for r in districts if r["district_id"] != PILOT_ID)
    assert all(r["district_id"] == PILOT_ID and r["zone_type"] == "PROTOTYPE_ANALYSIS_GRID"
               for r in first["analysis_zones"])
    source = json.loads((ROOT / "data/geodata/ner/metadata.json").read_text())
    assert first["regions"][0]["source_metadata"] == source
    assert all(r["source_metadata"]["dataset"] == source["dataset_source"]["adm2_districts"]
               for r in districts)
    for name in ("states", "districts"):
        key = "state_id" if name == "states" else "district_id"
        features = json.loads((ROOT / f"data/geodata/ner/{name}.geojson").read_text())["features"]
        properties = {f["properties"][key]: f["properties"] for f in features}
        assert all(r["source_metadata"]["feature"] == properties[r[key]] for r in first[name])


@pytest.mark.parametrize("table", TABLES, ids=lambda table: table.name)
def test_upsert_conflicts_on_primary_key_and_updates_every_non_key(table):
    statement = upsert_statement(table)
    sql = str(statement.compile(dialect=postgresql.dialect()))
    pk = list(table.primary_key.columns)[0].name
    assert f"ON CONFLICT ({pk}) DO UPDATE SET" in sql
    update = sql.split("DO UPDATE SET", 1)[1]
    for column in table.columns:
        if not column.primary_key:
            assert f"{column.name} = excluded.{column.name}" in update
    assert f"{pk} =" not in update


def test_migration_generates_reproducible_offline_sql(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", LOCAL_URL)
    def render():
        output = io.StringIO()
        config = Config(str(ROOT / "alembic.ini"), output_buffer=output)
        command.upgrade(config, "head", sql=True)
        return output.getvalue()
    sql = render()
    assert sql == render()
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in sql
    for table in TABLES:
        assert f"CREATE TABLE {table.name}" in sql
    assert sql.count("geometry(MULTIPOLYGON,4326)") == 3
    assert sql.count("USING gist (geometry)") == 3
    assert sql.count("FOREIGN KEY") == 3
    assert "COMMIT" in sql
