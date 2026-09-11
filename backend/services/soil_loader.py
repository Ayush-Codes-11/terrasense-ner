"""
soil_loader.py - Phase 1C: Canonical soil moisture data loader.
Reads the transaction-safe SMAP L4 JSON or falls back to SAMPLE_MOCK.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DATA_DIR = _REPO_ROOT / "data" if (_REPO_ROOT / "data").exists() else _BACKEND_DIR / "data"

_CANONICAL_SOIL_PATH = _DATA_DIR / "real" / "weather" / "smap_soil_moisture.json"
_SAMPLE_WEATHER_PATH = _DATA_DIR / "sample" / "sample_weather.json"


@lru_cache(maxsize=1)
def _load_soil_file() -> Optional[Dict[str, Any]]:
    if not _CANONICAL_SOIL_PATH.exists():
        return None
    try:
        with open(_CANONICAL_SOIL_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("metadata", {}).get("is_real") is True:
                return data
    except Exception:
        pass
    return None


@lru_cache(maxsize=1)
def _load_sample_weather() -> Dict[str, Any]:
    if not _SAMPLE_WEATHER_PATH.exists():
        return {}
    try:
        with open(_SAMPLE_WEATHER_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_soil_provenance_status() -> Dict[str, Any]:
    """Returns the provenance metadata for the active soil moisture source."""
    data = _load_soil_file()
    if data:
        meta = data.get("metadata", {})
        return {
            "status": meta.get("data_type", "REAL_SOIL_MOISTURE"),
            "source": meta.get("source_data_origin", "NASA_NSIDC_SMAP"),
            "dataset": meta.get("dataset", "SPL4SMGP"),
            "version": meta.get("version", "8"),
            "variable": meta.get("variable", "sm_rootzone_wetness"),
            "freshness_status": meta.get("freshness_status", "LATEST_AVAILABLE"),
            "age_hours": meta.get("product_age_hours"),
            "representative_time_utc": meta.get("representative_time_utc"),
            "is_real": True,
            "is_live": False,
        }
    return {
        "status": "SAMPLE_MOCK",
        "source": "TerraSense Synthetic",
        "freshness_status": "MOCK",
        "is_real": False,
        "is_live": False,
    }


def get_zone_soil_wetness(zone_id: str) -> float:
    """
    Returns the real SMAP sm_rootzone_wetness (0.0 - 1.0) for the given zone.
    Falls back to SAMPLE_MOCK if canonical data is missing or invalid.
    """
    zid = zone_id.upper()
    data = _load_soil_file()

    if data:
        zones = data.get("zones", {})
        if zid in zones:
            z_data = zones[zid]
            if z_data.get("provenance") == "REAL_SOIL_MOISTURE":
                val = z_data.get("soil_wetness")
                if val is not None:
                    return float(val)

    # Fallback to synthetic sample
    sample = _load_sample_weather()
    if zid in sample:
        sw = sample[zid].get("soil_wetness_index", sample[zid].get("soil_moisture", 0.0))
        return float(sw)

    return 0.0
