"""
terrain_loader.py — Cached loader for real DEM zonal terrain statistics.

Provides in-memory caching and clean fallback for:
- Zonal terrain statistics (mean slope, elevation, aspect)
- Raster and dataset provenance metadata
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DATA_DIR = _REPO_ROOT / "data" if (_REPO_ROOT / "data").exists() else _BACKEND_DIR / "data"
_TERRAIN_DIR = _DATA_DIR / "real" / "terrain"
_ZONAL_FILE = _TERRAIN_DIR / "zonal_terrain.json"
_META_FILE = _TERRAIN_DIR / "metadata.json"


@lru_cache(maxsize=1)
def load_zonal_terrain_dataset() -> Dict[str, Any]:
    """Loads and caches zonal terrain statistics from JSON file."""
    if _ZONAL_FILE.exists():
        try:
            with open(_ZONAL_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not read {_ZONAL_FILE}: {e}")
    return {"zones": {}, "total_zones": 0}


@lru_cache(maxsize=1)
def load_terrain_metadata() -> Dict[str, Any]:
    """Loads and caches DEM raster metadata from JSON file."""
    if _META_FILE.exists():
        try:
            with open(_META_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not read {_META_FILE}: {e}")
    return {}


def get_zone_terrain(zone_id: str) -> Optional[Dict[str, Any]]:
    """Returns zonal terrain statistics for a specific zone_id, or None if unavailable."""
    dataset = load_zonal_terrain_dataset()
    zones = dataset.get("zones", {})
    return zones.get(zone_id.upper())


def get_all_zones_terrain() -> Dict[str, Any]:
    """Returns the full dictionary of zonal terrain statistics."""
    return load_zonal_terrain_dataset()


def get_terrain_provenance_status() -> Dict[str, Any]:
    """Returns overall provenance status of the terrain layer."""
    meta = load_terrain_metadata()
    dataset = load_zonal_terrain_dataset()
    has_real_dem = bool(meta and dataset.get("zones"))

    if has_real_dem:
        return {
            "status": "REAL_DEM",
            "is_real": True,
            "source": meta.get(
                "source",
                "Copernicus DEM GLO-30 Public — distributed via AWS Open Data/Sinergise",
            ),
            "product": meta.get("product", "Copernicus GLO-30 DSM"),
            "resolution": meta.get("spatial_resolution", "30m"),
            "crs": meta.get("crs", "EPSG:4326"),
            "processing_crs": "EPSG:32646 (UTM Zone 46N)",
            "retrieved_at": meta.get("retrieved_at"),
            "total_zones": dataset.get("total_zones", len(dataset.get("zones", {}))),
            "attribution": meta.get(
                "attribution",
                "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved. Distributed via AWS Open Data/Sinergise.",
            ),
            "notes": (
                "Terrain slope and elevation derived from 30 m DEM. "
                "Notice: 30 m terrain resolution does NOT imply 30 m resolution for environmental data "
                "(rainfall ~10 km, soil moisture ~9 km)."
            ),
        }
    return {
        "status": "SAMPLE_MOCK",
        "is_real": False,
        "source": "Sample mock terrain attributes",
        "product": "Synthetic pilot grid properties",
        "resolution": "synthetic",
        "crs": "EPSG:4326",
        "processing_crs": "None",
        "retrieved_at": None,
        "total_zones": 0,
        "attribution": "TerraSense sample data",
        "notes": "Real DEM not loaded. Using fallback sample values.",
    }
