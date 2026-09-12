"""Read-only deployment gate; never invoked by application startup."""
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

from db.import_hierarchy import DatasetValidationError, load_records, validate_database


def check_readiness(connection):
    """Caller owns a read-only transaction. Fail rather than repair any mismatch."""
    if connection.scalar(text(
        "SELECT count(*) FROM pg_extension WHERE extname = 'postgis'"
    )) != 1:
        raise DatasetValidationError("PostGIS extension is unavailable.")
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    expected = set(ScriptDirectory.from_config(config).get_heads())
    context = MigrationContext.configure(connection, opts={
        "version_table_schema": connection.info.get("migration_schema")})
    if set(context.get_current_heads()) != expected:
        raise DatasetValidationError("Database Alembic revision is not current.")
    # Also checks table presence, every canonical field, exact geometry, and orphans.
    report = validate_database(connection, load_records())
    return {"ready": True, "alembic_heads": sorted(expected), **report}
