"""Runtime source selection and safe failures; no live DB required."""
from contextlib import contextmanager
import socket

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import ProgrammingError

from db.hierarchy_reader import get_postgis_engine
from main import app
from services import hierarchy_source


@pytest.fixture(autouse=True)
def source_environment(monkeypatch):
    monkeypatch.delenv("HIERARCHY_DATA_SOURCE", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)


@pytest.mark.parametrize("source", [None, "file"])
def test_default_and_explicit_file_mode_need_no_database(source, monkeypatch):
    if source is not None:
        monkeypatch.setenv("HIERARCHY_DATA_SOURCE", source)
    with TestClient(app) as client:
        assert client.get("/regions").json()["count"] == 1
        assert client.get("/states").json()["count"] == 8
        assert client.get("/districts/IND-ADM2-76128533B34203923268864/zones").json()["count"] == 25


@pytest.mark.parametrize("source", ["", "FILE", "postgres", "secret-invalid-value"])
def test_invalid_source_fails_clearly_without_echoing_value(source, monkeypatch):
    monkeypatch.setenv("HIERARCHY_DATA_SOURCE", source)
    with TestClient(app) as client:
        response = client.get("/regions")
    assert response.status_code == 503
    assert response.json()["detail"] == {
        "status": "BOUNDARY_DATA_UNAVAILABLE",
        "message": "HIERARCHY_DATA_SOURCE must be 'file' or 'postgis'."}


def no_file_fallback(monkeypatch):
    def forbidden():
        raise AssertionError("Explicit PostGIS mode must not read the file loader")
    monkeypatch.setattr(hierarchy_source, "get_file_hierarchy_loader", forbidden)


def assert_safe_unavailable(client):
    for path in ("/regions", "/states", "/states/IN-MZ/districts",
                 "/districts/IND-ADM2-76128533B34203923268864/zones", "/zones/C03"):
        response = client.get(path)
        assert response.status_code == 503
        assert response.json()["detail"] == {
            "status": "BOUNDARY_DATA_UNAVAILABLE",
            "message": "NER administrative boundary dataset is not available."}
    assert client.get("/health").status_code == 200
    assert len(client.get("/zones").json()["features"]) == 25
    risk = client.get("/risk/current/C03")
    assert risk.status_code == 200
    assert risk.json()["risk_score"] == pytest.approx(0.7103, abs=0.0001)


def test_postgis_missing_url_is_503_without_fallback(monkeypatch):
    monkeypatch.setenv("HIERARCHY_DATA_SOURCE", "postgis")
    no_file_fallback(monkeypatch)
    with TestClient(app) as client:
        assert_safe_unavailable(client)


def test_unreachable_database_is_503_and_releases_connections(monkeypatch):
    no_file_fallback(monkeypatch)
    monkeypatch.setenv("HIERARCHY_DATA_SOURCE", "postgis")
    # Reserve an unlistening local port so this cannot accidentally reach a real DB.
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
        url = f"postgresql+psycopg://private_user:private_password@127.0.0.1:{port}/missing?connect_timeout=2"
        monkeypatch.setenv("DATABASE_URL", url)
        engine = get_postgis_engine(url)
        try:
            with TestClient(app) as client:
                response = client.get("/regions")
                assert response.status_code == 503
                assert response.json()["detail"]["status"] == "BOUNDARY_DATA_UNAVAILABLE"
                for secret in ("private_user", "private_password", url, "Traceback"):
                    assert secret not in response.text
            assert engine.pool.checkedout() == 0
        finally:
            engine.dispose()


def test_missing_schema_error_is_sanitized_and_session_exits(monkeypatch):
    import db.hierarchy_reader as reader
    no_file_fallback(monkeypatch)
    monkeypatch.setenv("HIERARCHY_DATA_SOURCE", "postgis")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://secret:password@host/db")
    exited = []
    class BrokenSession:
        def execute(self, statement):
            raise ProgrammingError("SELECT private_schema", {}, Exception("secret password"))
    @contextmanager
    def broken_scope(engine):
        try:
            yield BrokenSession()
        finally:
            exited.append(True)
    monkeypatch.setattr(reader, "session_scope", broken_scope)
    with TestClient(app) as client:
        assert_safe_unavailable(client)
    assert len(exited) == 5
