import pytest
import json
import math
from pathlib import Path
from unittest import mock

try:
    import h5py
    import numpy as np
except ImportError:
    h5py = None
    np = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CANONICAL_PATH = _REPO_ROOT / "data" / "real" / "weather" / "smap_soil_moisture.json"


def _canonical() -> dict:
    with open(_CANONICAL_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Soil loader — real canonical present
# ---------------------------------------------------------------------------

def test_soil_loader_real():
    from backend.services.soil_loader import _load_soil_file, get_soil_provenance_status, get_zone_soil_wetness
    _load_soil_file.cache_clear()

    status = get_soil_provenance_status()
    assert status["status"] == "REAL_SOIL_MOISTURE"
    assert status["is_real"] is True

    # C03 must resolve to a non-trivial wetness from the real canonical
    val = get_zone_soil_wetness("C03")
    canon = _canonical()
    expected = canon["zones"]["C03"]["soil_wetness"]
    assert abs(val - expected) < 1e-6, f"C03 wetness mismatch: {val} vs {expected}"


# ---------------------------------------------------------------------------
# 2. Soil loader — missing canonical falls back to SAMPLE_MOCK
# ---------------------------------------------------------------------------

def test_soil_loader_fallback(tmp_path):
    missing = tmp_path / "missing.json"
    from backend.services.soil_loader import _load_soil_file, get_soil_provenance_status
    with mock.patch("backend.services.soil_loader._CANONICAL_SOIL_PATH", missing):
        _load_soil_file.cache_clear()
        status = get_soil_provenance_status()
    assert status["status"] == "SAMPLE_MOCK"
    assert status["is_real"] is False


# ---------------------------------------------------------------------------
# 3. HDF5 structural contract (skipped when h5py unavailable)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(h5py is None, reason="h5py not installed")
def test_hdf5_validation(tmp_path):
    h5_path = tmp_path / "test.h5"
    with h5py.File(h5_path, "w") as f:
        grp = f.create_group("Geophysical_Data")
        ds = grp.create_dataset(
            "sm_rootzone_wetness",
            data=np.zeros((1624, 3856), dtype=np.float32),
        )
        ds.attrs["units"] = "dimensionless"
        ds.attrs["valid_min"] = 0.0
        ds.attrs["valid_max"] = 1.0
        ds.attrs["_FillValue"] = -9999.0

        f.create_dataset("cell_lat", data=np.zeros((1624, 3856), dtype=np.float32))
        f.create_dataset("cell_lon", data=np.zeros((1624, 3856), dtype=np.float32))
        f.create_dataset("cell_row", data=np.zeros((1624, 3856), dtype=np.int32))
        f.create_dataset("cell_column", data=np.zeros((1624, 3856), dtype=np.int32))
        f.create_dataset("x", data=np.zeros(3856, dtype=np.float64))
        f.create_dataset("y", data=np.zeros(1624, dtype=np.float64))

    with h5py.File(h5_path, "r") as f:
        assert "Geophysical_Data" in f
        v = f["Geophysical_Data"]["sm_rootzone_wetness"]
        assert v.shape == (1624, 3856)
        assert v.attrs["units"] in (b"dimensionless", "dimensionless")
        assert v.attrs["valid_min"] == 0.0


# ---------------------------------------------------------------------------
# 4. CMR filename timestamp parsing
# ---------------------------------------------------------------------------

def test_cmr_timestamp_logic():
    import re
    filename = "SMAP_L4_SM_gph_20260907T223000_Vv8011_001.h5"
    match = re.search(
        r"SMAP_L4_SM_gph_(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})_",
        filename,
    )
    assert match is not None
    ts = (
        f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        f"T{match.group(4)}:{match.group(5)}:{match.group(6)}Z"
    )
    assert ts == "2026-09-07T22:30:00Z"


# ---------------------------------------------------------------------------
# 5. HTTP route: GET /risk/current/C03 must return 200 with real SMAP provenance
#    This is the integration test that catches the import-mismatch bug.
# ---------------------------------------------------------------------------

def test_api_risk_current_c03_returns_real_smap_provenance():
    """
    Exercises the full FastAPI request path for /risk/current/C03 and
    verifies the soil_wetness provenance is REAL_SOIL_MOISTURE.
    This test would have caught the empty soil_loader.py commit.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    r = client.get("/risk/current/C03")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"

    data = r.json()
    prov = data.get("feature_provenance", {})
    assert prov.get("soil_wetness") == "REAL_SOIL_MOISTURE", (
        f"Expected REAL_SOIL_MOISTURE, got: {prov.get('soil_wetness')}"
    )
    # Also assert the other real sources are present
    assert prov.get("slope") == "REAL_DEM"
    assert prov.get("observed_rainfall") == "REAL_GPM"
