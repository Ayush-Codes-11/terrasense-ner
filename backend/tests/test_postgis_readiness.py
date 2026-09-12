from types import SimpleNamespace
import os
from pathlib import Path
import subprocess
import sys

import pytest
from db import readiness
from db.import_hierarchy import DatasetValidationError


def test_readiness_rejects_missing_extension():
    connection = SimpleNamespace(scalar=lambda query: 0)
    with pytest.raises(DatasetValidationError, match='extension'):
        readiness.check_readiness(connection)


def test_readiness_rejects_stale_revision(monkeypatch):
    connection = SimpleNamespace(scalar=lambda query: 1, info={})
    monkeypatch.setattr(readiness.MigrationContext, 'configure',
                        lambda *a, **k: SimpleNamespace(get_current_heads=lambda: ('stale',)))
    with pytest.raises(DatasetValidationError, match='revision'):
        readiness.check_readiness(connection)


@pytest.mark.parametrize("url", [None, "postgresql://private_user:private_password@host/db"])
def test_readiness_cli_configuration_is_sanitized(url):
    env = os.environ.copy()
    env.pop('DATABASE_URL', None)
    if url is not None:
        env['DATABASE_URL'] = url
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run([sys.executable, str(root / 'scripts/check_postgis_readiness.py')],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert result.stdout == ''
    assert result.stderr.startswith('PostGIS readiness failed:')
    assert 'Traceback' not in result.stderr
    assert 'private_user' not in result.stderr
    assert 'private_password' not in result.stderr
    assert 'postgresql://' not in result.stderr
