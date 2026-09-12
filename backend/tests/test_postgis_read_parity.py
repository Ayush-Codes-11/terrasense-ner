"""Live API and geometry parity on an isolated, committed test schema."""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.schema import CreateSchema, DropSchema

from db.hierarchy_parity import compare_file_and_postgis_hierarchy
from db.hierarchy_reader import get_postgis_engine
from db.import_hierarchy import import_records, load_records
from db.session import create_db_engine, database_url
from main import app
from services import hierarchy_source
from services.hierarchy_loader import HierarchyLoader

pytestmark = pytest.mark.postgis
PILOT = "IND-ADM2-76128533B34203923268864"
ANJAW = "IND-ADM2-76128533B55878637000592"


@pytest.fixture(scope="module")
def imported_read_database():
    raw_url = os.getenv("POSTGIS_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Set POSTGIS_TEST_DATABASE_URL to opt into live PostGIS read parity")
    admin_engine = create_db_engine(raw_url)
    schema = "test_read_parity_" + uuid4().hex
    scoped_url = database_url(raw_url).update_query_dict({
        "options": f"-csearch_path={schema},public"}).render_as_string(hide_password=False)
    scoped_engine = create_db_engine(scoped_url)
    try:
        with admin_engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        # Commit so separate request sessions can see the imported test data.
        with scoped_engine.begin() as connection:
            connection.info["migration_schema"] = schema
            config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            import_records(connection, load_records())
        yield scoped_url, scoped_engine
    finally:
        get_postgis_engine(scoped_url).dispose()
        scoped_engine.dispose()
        # Only the randomly named schema created above is removed.
        with admin_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True, if_exists=True))
        admin_engine.dispose()


def test_live_postgis_api_matches_file_contract_and_releases_sessions(imported_read_database, monkeypatch):
    url, _ = imported_read_database
    loader = HierarchyLoader()
    assert ANJAW in loader.districts, "The validated Anjaw ID is missing; do not substitute another ID"
    paths = ["/regions", "/regions/NER/states", "/states", "/states/IN-MZ",
             f"/districts/{PILOT}", f"/districts/{PILOT}/zones", "/zones/C03", "/zones/c03",
             f"/districts/{ANJAW}/zones"]
    paths += [f"/states/{state_id}/districts" for state_id in sorted(loader.states)]
    paths += ["/regions/UNKNOWN/states", "/states/UNKNOWN", "/states/UNKNOWN/districts",
              "/districts/UNKNOWN", "/districts/UNKNOWN/zones", "/zones/UNKNOWN"]
    monkeypatch.setenv("HIERARCHY_DATA_SOURCE", "file")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        expected = {path: client.get(path) for path in paths}
    assert expected["/regions"].json()["count"] == 1
    assert expected["/states"].json()["count"] == 8
    assert expected["/states/IN-MZ/districts"].json()["count"] == 11
    assert expected[f"/districts/{PILOT}/zones"].json()["count"] == 25
    assert expected[f"/districts/{ANJAW}/zones"].json()["items"] == []
    assert expected[f"/districts/{ANJAW}/zones"].json()["detailed_zone_model_available"] is False

    monkeypatch.setenv("HIERARCHY_DATA_SOURCE", "postgis")
    monkeypatch.setenv("DATABASE_URL", url)
    def forbidden_file_loader():
        raise AssertionError("PostGIS runtime must not fall back to the file loader")
    monkeypatch.setattr(hierarchy_source, "get_file_hierarchy_loader", forbidden_file_loader)
    engine = get_postgis_engine(url)
    statements = []
    def record_sql(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(engine, "before_cursor_execute", record_sql)
    try:
        with TestClient(app) as client:
            for path in paths:
                actual = client.get(path)
                assert (actual.status_code, actual.json()) == (
                    expected[path].status_code, expected[path].json()), path
                assert engine.pool.checkedout() == 0
            assert client.get("/health").status_code == 200
            assert len(client.get("/zones").json()["features"]) == 25
            risk = client.get("/risk/current/C03").json()
            assert risk["risk_score"] == pytest.approx(0.7103, abs=0.0001)
            assert risk["risk_category"] == "HIGH"
    finally:
        event.remove(engine, "before_cursor_execute", record_sql)
    assert sum("REPEATABLE READ, READ ONLY" in statement for statement in statements) == len(paths)
    assert not any(statement.lstrip().split()[0].upper() in
                   {"INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"}
                   for statement in statements)


def test_live_file_postgis_domain_and_geometry_parity(imported_read_database):
    _, engine = imported_read_database
    report = compare_file_and_postgis_hierarchy(engine)
    assert report == {"regions_match": True, "states_match": True, "districts_match": True,
                      "zones_match": True, "geometry_match": True, "mismatches": []}
    assert engine.pool.checkedout() == 0
