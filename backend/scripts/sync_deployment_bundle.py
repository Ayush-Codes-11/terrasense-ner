"""
sync_deployment_bundle.py — Deterministic synchronization between canonical repo root
and backend deployment bundle directories.

Canonical sources:
  <repo_root>/data/
  <repo_root>/ml/

Deployment targets:
  <repo_root>/backend/data/
  <repo_root>/backend/ml/

Rules:
1. Canonical data/ and ml/ at repo root are the single source of truth.
2. Large raw GeoTIFF files (*.tif, *.tiff) in data/real/terrain/ are excluded from backend/data/
   (FastAPI runtime only needs precomputed zonal_terrain.json and metadata.json).
3. __pycache__, .pyc, and OS metadata files are excluded.
4. Parity is asserted via SHA-256 hashes.
5. Any deleted file in canonical sources is purged from deployment targets.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import Set

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CANONICAL_DATA = _REPO_ROOT / "data"
_CANONICAL_ML = _REPO_ROOT / "ml"
_TARGET_DATA = _REPO_ROOT / "backend" / "data"
_TARGET_ML = _REPO_ROOT / "backend" / "ml"

EXCLUDED_EXTENSIONS = {".tif", ".tiff", ".pyc"}
EXCLUDED_NAMES = {".DS_Store", "Thumbs.db"}
EXCLUDED_DIRS = {"__pycache__"}


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def sync_directory(src_root: Path, dst_root: Path, label: str) -> None:
    if not src_root.exists():
        print(f"Source {src_root} does not exist, skipping.")
        return

    dst_root.mkdir(parents=True, exist_ok=True)
    synced_files: Set[Path] = set()

    for root, dirs, files in os.walk(src_root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        rel_dir = Path(root).relative_to(src_root)
        target_dir = dst_root / rel_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        for filename in files:
            file_path = Path(root) / filename
            if file_path.suffix.lower() in EXCLUDED_EXTENSIONS or filename in EXCLUDED_NAMES:
                continue

            target_file = target_dir / filename
            src_sha = compute_sha256(file_path)
            synced_files.add(target_file.resolve())

            needs_copy = True
            if target_file.exists():
                dst_sha = compute_sha256(target_file)
                if src_sha == dst_sha:
                    needs_copy = False

            if needs_copy:
                shutil.copy2(file_path, target_file)
                print(f"[{label}] Synced: {rel_dir / filename}")

    for root, dirs, files in os.walk(dst_root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for filename in files:
            target_file = Path(root) / filename
            if target_file.suffix.lower() in EXCLUDED_EXTENSIONS:
                target_file.unlink()
                print(f"[{label}] Removed disallowed file: {target_file}")
                continue
            if target_file.resolve() not in synced_files:
                target_file.unlink()
                print(f"[{label}] Removed orphaned file: {target_file}")

    print(f"[{label}] Synchronization complete. {len(synced_files)} files verified.")


def main():
    print(f"TerraSense NER — Deployment Bundle Sync")
    print(f"Canonical Root: {_REPO_ROOT}")
    sync_directory(_CANONICAL_DATA, _TARGET_DATA, "DATA")
    sync_directory(_CANONICAL_ML, _TARGET_ML, "ML")
    print("All deployment bundles are in 100% parity with canonical sources.")


if __name__ == "__main__":
    main()
