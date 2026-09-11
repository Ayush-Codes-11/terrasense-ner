"""Offline checks for the Phase 3 PostGIS schema and seed generator."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "backend" / "db" / "migrations" / "001_ner_hierarchy.sql"
SEED_SCRIPT = ROOT / "backend" / "scripts" / "generate_ner_postgis_seed.py"


def test_postgis_migration_defines_hierarchy_constraints_and_indexes():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in sql
    assert "CREATE SCHEMA IF NOT EXISTS terrasense" in sql
    assert "terrasense.regions" in sql
    assert "terrasense.states" in sql
    assert "terrasense.districts" in sql
    assert "REFERENCES terrasense.regions(region_id)" in sql
    assert "REFERENCES terrasense.states(state_id)" in sql
    assert "geometry(MultiPolygon, 4326)" in sql
    assert "USING gist" in sql


def test_postgis_seed_generator_is_present_and_does_not_require_database():
    script = SEED_SCRIPT.read_text(encoding="utf-8")
    assert "generate_ner_postgis_seed.py" in script
    assert "ST_GeomFromGeoJSON" in script
    assert "ON CONFLICT" in script
    assert "psycopg" not in script
