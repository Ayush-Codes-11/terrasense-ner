"""Opt-in live tests. Every test uses an isolated schema rolled back at teardown."""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateSchema

from db.import_hierarchy import (
    DISTRICT_COUNTS, PILOT_ID, TABLES, import_records, load_records, validate_database,
)
from db.models import AnalysisZone, District, Region, State
from db.session import create_db_engine

pytestmark = pytest.mark.postgis


@pytest.fixture
def migrated_database():
    url = os.getenv("POSTGIS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set POSTGIS_TEST_DATABASE_URL to opt into live PostGIS validation")
    engine = create_db_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            schema = "test_hierarchy_" + uuid4().hex
            connection.execute(CreateSchema(schema))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            connection.info["migration_schema"] = schema
            config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            yield connection, config, schema
            transaction.rollback()
    finally:
        engine.dispose()


def test_live_migration_import_spatial_parity_and_idempotency(migrated_database):
    connection, config, schema = migrated_database
    command.upgrade(config, "head")  # An already applied migration is a no-op.
    assert connection.scalar(text("SELECT count(*) FROM pg_extension WHERE extname = 'postgis'")) == 1
    inspector = inspect(connection)
    assert set(inspector.get_table_names(schema=schema)) == {
        "alembic_version", "regions", "states", "districts", "analysis_zones"}
    for table in TABLES[1:]:
        indexes = inspector.get_indexes(table.name, schema=schema)
        assert any(i["name"] == f"ix_{table.name}_geometry"
                   and i["dialect_options"]["postgresql_using"] == "gist" for i in indexes)
        assert len(inspector.get_foreign_keys(table.name, schema=schema)) == 1
    records = load_records()
    report = import_records(connection, records)
    assert report["counts"] == {"regions": 1, "states": 8, "districts": 119, "analysis_zones": 25}
    assert report["district_counts"] == DISTRICT_COUNTS
    pilot = connection.execute(select(District.__table__).where(
        District.district_id == PILOT_ID)).mappings().one()
    assert (pilot["district_name"], pilot["state_id"], pilot["lgd_code"],
            pilot["coverage_level"], pilot["risk_model_status"]) == (
        "Aizawl", "IN-MZ", None, "DETAILED_PILOT", "STATIC_ML_VALIDATION_PENDING")
    other_statuses = connection.execute(select(District.coverage_level, District.risk_model_status)
                                       .where(District.district_id != PILOT_ID)).all()
    assert len(other_statuses) == 118
    assert all(tuple(status) == ("DISTRICT_BOUNDARY_ONLY", "NOT_IMPLEMENTED")
               for status in other_statuses)
    zone_parents = connection.execute(select(AnalysisZone.district_id)).scalars().all()
    assert len(zone_parents) == 25 and set(zone_parents) == {PILOT_ID}
    before = [connection.execute(select(t).order_by(*t.primary_key.columns)).all() for t in TABLES]
    assert import_records(connection, records) == report
    after = [connection.execute(select(t).order_by(*t.primary_key.columns)).all() for t in TABLES]
    assert before == after
    assert validate_database(connection, records)["source_parity"] is True

    # Prove database enforcement, not merely source validation.
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(Region.__table__.insert(), records["regions"][0])
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(State.__table__.insert(),
                           {**records["states"][0], "state_id": "ORPHAN", "region_id": "MISSING"})
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(text("UPDATE states SET geometry = ST_GeomFromText('MULTIPOLYGON EMPTY', 4326)"))

    # A downgrade/re-upgrade is reproducible within this disposable schema.
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    assert import_records(connection, records) == report
