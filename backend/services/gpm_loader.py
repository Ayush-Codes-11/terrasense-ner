"""
gpm_loader.py — Cached loader for real NASA GPM IMERG observed precipitation data.

Provides in-memory caching and clean fallback for:
- Observed daily rainfall buckets (d_minus_2, d_minus_1, d0)
- NASA GPM IMERG metadata and provenance status
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DATA_DIR = _REPO_ROOT / "data" if (_REPO_ROOT / "data").exists() else _BACKEND_DIR / "data"
_WEATHER_DIR = _DATA_DIR / "real" / "weather"
_GPM_FILE = _WEATHER_DIR / "gpm_imerg_observed.json"
_META_FILE = _WEATHER_DIR / "metadata.json"


@lru_cache(maxsize=1)
def load_gpm_observed_dataset() -> Dict[str, Any]:
    """Loads and caches GPM IMERG observed precipitation dataset from JSON file."""
    if _GPM_FILE.exists():
        try:
            with open(_GPM_FILE, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "zones" in data:
                    return data
        except Exception as e:
            print(f"Warning: Could not read {_GPM_FILE}: {e}")
    return {"zones": {}, "metadata": {}}


@lru_cache(maxsize=1)
def load_gpm_metadata() -> Dict[str, Any]:
    """Loads and caches GPM IMERG metadata from JSON file."""
    if _META_FILE.exists():
        try:
            with open(_META_FILE, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            print(f"Warning: Could not read {_META_FILE}: {e}")
    return {}


def get_zone_gpm_observed(zone_id: str) -> Optional[Dict[str, Any]]:
    """Returns GPM observed rainfall for a specific zone_id, or None if unavailable."""
    dataset = load_gpm_observed_dataset()
    zones = dataset.get("zones", {})
    return zones.get(zone_id.upper())


def get_all_zones_gpm_observed() -> Dict[str, Any]:
    """Returns the full dictionary of GPM observed precipitation statistics."""
    return load_gpm_observed_dataset()


def get_gpm_provenance_status() -> Dict[str, Any]:
    """Returns overall provenance status of the GPM precipitation layer."""
    meta = load_gpm_metadata()
    dataset = load_gpm_observed_dataset()
    has_real_gpm = bool(meta and dataset.get("zones"))

    if has_real_gpm:
        return {
            "status": "REAL_GPM",
            "is_real": True,
            "source": meta.get(
                "source",
                "NASA Global Precipitation Measurement (GPM) IMERG Late Run",
            ),
            "product": meta.get(
                "product",
                "NASA GPM IMERG Late Precipitation L3 1 day 0.1° V07 (GPM_3IMERGDL)",
            ),
            "collection": meta.get("collection", "GPM_3IMERGDL"),
            "collection_version": meta.get("collection_version", "07"),
            "algorithm_generation": meta.get("algorithm_generation", "V07"),
            "granule_processing_version": meta.get("granule_processing_version", "V07C"),
            "collection_concept_id": meta.get("collection_concept_id", "C2723754859-GES_DISC"),
            "source_variable": meta.get("source_variable", "precipitation"),
            "source_unit": meta.get("source_unit", "mm/day"),
            "observation_duration": meta.get("observation_duration", "1 complete UTC day per bucket"),
            "native_spatial_resolution_deg": meta.get("native_spatial_resolution_deg", 0.1),
            "temporal_resolution": meta.get("temporal_resolution", "1 day (daily accumulation)"),
            "reference_timestamp_utc": meta.get("reference_timestamp_utc"),
            "retrieved_at_utc": meta.get("retrieved_at_utc"),
            "days": meta.get("days", {}),
            "total_zones": len(dataset.get("zones", {})),
            "unique_native_cells_count": meta.get("unique_native_cells_count", 4),
            "attribution": meta.get(
                "attribution",
                "NASA Global Precipitation Measurement (GPM) Integrated Multi-satellitE Retrievals for GPM (IMERG), archived and distributed by NASA GES DISC.",
            ),
            "notes": meta.get(
                "notes",
                "GPM IMERG estimates are satellite-derived precipitation measurements at ~0.1 deg (~10 km) native grid. Values represent recent observed precipitation triggers; future rainfall windows remain scenario-based.",
            ),
        }

    return {
        "status": "SAMPLE_MOCK",
        "is_real": False,
        "source": "Sample mock weather scenario generator",
        "product": "Synthetic pilot grid precipitation",
        "collection": "None",
        "collection_version": "None",
        "algorithm_generation": "None",
        "granule_processing_version": "None",
        "collection_concept_id": "None",
        "source_variable": "synthetic_rain",
        "source_unit": "mm",
        "observation_duration": "synthetic",
        "native_spatial_resolution_deg": "synthetic",
        "temporal_resolution": "synthetic",
        "reference_timestamp_utc": None,
        "retrieved_at_utc": None,
        "days": {},
        "total_zones": 0,
        "unique_native_cells_count": 0,
        "attribution": "TerraSense sample scenario data",
        "notes": "Real GPM data not loaded. Using fallback sample values.",
    }
