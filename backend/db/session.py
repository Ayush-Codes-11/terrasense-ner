"""Explicit, synchronous connections; no engine or environment reads at import."""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session


class DatabaseConfigurationError(ValueError):
    pass


def database_url(value: str | URL | None = None) -> URL:
    raw = value if value is not None else os.getenv("DATABASE_URL")
    if not raw:
        raise DatabaseConfigurationError("DATABASE_URL is required for database commands.")
    try:
        url = make_url(raw)
        # Accessing port also validates nonnumeric ports without echoing credentials.
        port = url.port
    except (ArgumentError, ValueError, TypeError):
        raise DatabaseConfigurationError("DATABASE_URL is not a valid SQLAlchemy URL.") from None
    if url.drivername != "postgresql+psycopg" or not url.database:
        raise DatabaseConfigurationError(
            "DATABASE_URL must use postgresql+psycopg and specify a database."
        )
    if port is not None and not 1 <= port <= 65535:
        raise DatabaseConfigurationError("DATABASE_URL port is out of range.")
    return url


def create_db_engine(value: str | URL | None = None):
    return create_engine(database_url(value), pool_pre_ping=True, hide_parameters=True)


@contextmanager
def session_scope(engine):
    """Commit on success; roll back and close on failure. Caller owns the engine."""
    with Session(engine) as session, session.begin():
        yield session
