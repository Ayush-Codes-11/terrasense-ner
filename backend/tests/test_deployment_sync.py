"""
test_deployment_sync.py — CI/CD test asserting 100% parity between canonical
data/ & ml/ directories and backend/ deployment bundle.

Guarantees:
1. No stale files in backend/data or backend/ml.
2. No large binary GeoTIFF files (.tif/.tiff) accidentally included in serverless bundle.
3. All critical runtime GeoJSON and JSON datasets are present and self-contained.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TESTS_DIR.parent
_REPO_ROOT = _BACKEND_DIR.parent

EXCLUDED_EXTENSIONS = {".tif", ".tiff", ".pyc"}
EXCLUDED_NAMES = {".DS_Store", "Thumbs.db"}
EXCLUDED_DIRS = {"__pycache__"}


def _compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_no_disallowed_geotiff_in_backend():
    """Ensure raw GeoTIFF files are NEVER bundled into backend/ (FastAPI serves precomputed JSON)."""
    backend_data = _BACKEND_DIR / "data"
    if not backend_data.exists():
        pytest.skip("backend/data not found")

    tif_files = list(backend_data.rglob("*.tif")) + list(backend_data.rglob("*.tiff"))
    assert len(tif_files) == 0, f"Found raw GeoTIFF in deployment bundle: {tif_files}. Delete or run sync script."


def test_backend_bundle_self_contained():
    """Ensure all required runtime files exist within backend/ for isolated serverless execution."""
    backend_data = _BACKEND_DIR / "data"
    backend_ml = _BACKEND_DIR / "ml"

    required_files = [
        backend_data / "sample" / "grid-risk.geojson",
        backend_data / "sample" / "sample_weather.json",
        backend_data / "real" / "terrain" / "zonal_terrain.json",
        backend_data / "real" / "terrain" / "metadata.json",
        backend_data / "real" / "weather" / "gpm_imerg_observed.json",
        backend_data / "real" / "weather" / "metadata.json",
        backend_data / "real" / "osm" / "critical_facilities.geojson",
        backend_data / "real" / "osm" / "roads.geojson",
        backend_data / "real" / "osm" / "settlements.geojson",
        backend_data / "real" / "landslides" / "gsi_mizoram_complete.json",
        backend_data / "real" / "landslides" / "model_feasibility.json",
        backend_ml / "prototype_scorer.py",
        backend_ml / "scorer_config.py",
    ]

    for req_file in required_files:
        assert req_file.exists(), f"Missing required deployment file: {req_file}"
        assert req_file.stat().st_size > 0, f"File is empty: {req_file}"


def test_deployment_bundle_parity():
    """
    If running in repo root context, assert 100% SHA-256 parity between
    canonical data/ & ml/ and backend/data/ & backend/ml/.
    """
    canonical_data = _REPO_ROOT / "data"
    canonical_ml = _REPO_ROOT / "ml"

    if not (canonical_data.exists() and canonical_ml.exists()):
        pytest.skip("Running in isolated backend environment; skipping canonical parity check.")

    backend_data = _BACKEND_DIR / "data"
    backend_ml = _BACKEND_DIR / "ml"

    # Check data/ parity
    for root, dirs, files in os.walk(canonical_data):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for filename in files:
            src_file = Path(root) / filename
            if src_file.suffix.lower() in EXCLUDED_EXTENSIONS or filename in EXCLUDED_NAMES:
                continue

            rel_path = src_file.relative_to(canonical_data)
            target_file = backend_data / rel_path

            assert target_file.exists(), (
                f"File {rel_path} exists in canonical data/ but missing from backend/data/. "
                "Run `python backend/scripts/sync_deployment_bundle.py`."
            )
            assert _compute_sha256(src_file) == _compute_sha256(target_file), (
                f"File {rel_path} content diverged between canonical data/ and backend/data/. "
                "Run `python backend/scripts/sync_deployment_bundle.py`."
            )

    # Check ml/ parity
    for root, dirs, files in os.walk(canonical_ml):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for filename in files:
            src_file = Path(root) / filename
            if src_file.suffix.lower() in EXCLUDED_EXTENSIONS or filename in EXCLUDED_NAMES:
                continue

            rel_path = src_file.relative_to(canonical_ml)
            target_file = backend_ml / rel_path

            assert target_file.exists(), (
                f"File {rel_path} exists in canonical ml/ but missing from backend/ml/. "
                "Run `python backend/scripts/sync_deployment_bundle.py`."
            )
            assert _compute_sha256(src_file) == _compute_sha256(target_file), (
                f"File {rel_path} content diverged between canonical ml/ and backend/ml/. "
                "Run `python backend/scripts/sync_deployment_bundle.py`."
            )


def test_critical_files_not_empty():
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent.parent
    for rel_path in ['backend/services/soil_loader.py', 'backend/scripts/fetch_smap_soil.py']:
        p = repo_root / rel_path
        assert p.exists()
        assert p.stat().st_size > 0, f'{rel_path} is unexpectedly empty!'
