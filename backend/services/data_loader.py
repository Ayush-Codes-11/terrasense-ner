"""
data_loader.py — loads sample GeoJSON from the canonical data/sample/ directory.

The canonical data source is data/sample/ at the repo root.
This module resolves the path relative to its own location so it works
regardless of the working directory uvicorn is started from.

Phase 5: swap _SAMPLE_DIR references to real OSM/SRTM sources per layer.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

# backend/services/data_loader.py → backend/services → backend → repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SAMPLE_DIR = _REPO_ROOT / "data" / "sample"


def _load_json(name: str) -> dict:
    path = _SAMPLE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Sample file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_grid_risk() -> dict:
    """Load and cache the risk grid GeoJSON FeatureCollection."""
    return _load_json("grid-risk.geojson")


@lru_cache(maxsize=1)
def load_roads() -> dict:
    return _load_json("roads.geojson")


@lru_cache(maxsize=1)
def load_villages() -> dict:
    return _load_json("villages.geojson")


@lru_cache(maxsize=1)
def load_hospitals() -> dict:
    return _load_json("hospitals.geojson")


def get_all_zone_props() -> list[dict]:
    """Return property dicts for all 25 zones."""
    fc = load_grid_risk()
    return [f["properties"] for f in fc["features"] if f.get("type") == "Feature"]


def get_zone_props(zone_id: str) -> Optional[dict]:
    """Return properties for a single zone, or None if not found."""
    zid = zone_id.upper()
    for props in get_all_zone_props():
        if props.get("zone_id") == zid:
            return props
    return None
