"""Use DATABASE_URL only for explicit migration commands, never app startup."""
from alembic import context

from db.base import Base
from db import models  # noqa: F401 - register the four tables
from db.session import create_db_engine, database_url


def run(connection):
    context.configure(connection=connection, target_metadata=Base.metadata,
                      version_table_schema=connection.info.get("migration_schema"))
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=database_url(), target_metadata=Base.metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get("connection") is not None:
    run(context.config.attributes["connection"])
else:
    engine = create_db_engine()
    try:
        with engine.connect() as connection:
            run(connection)
    finally:
        engine.dispose()
