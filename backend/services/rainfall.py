"""
rainfall.py — Canonical weather and rainfall data adapter service for TerraSense NER.

════════════════════════════════════════════════════════════════════════════════
REAL-DATA GUARDRAILS FOR FUTURE WEATHER ADAPTERS (PHASE 5+ DOCUMENTATION):
════════════════════════════════════════════════════════════════════════════════
1. NASA GPM IMERG:
   - GPM IMERG provides near-real-time and calibrated PAST / RECENT precipitation
     estimates (e.g. Early/Late/Final runs), NOT future weather predictions.
   - Future adapter role: GPM -> observed_daily_mm (recent past).
   - NEVER feed GPM into future forecast intervals (+24h/+48h/+72h).
   - Spatial resolution is coarse relative to terrain: ~0.1 deg (~10 km).
     Multiple fine TerraSense terrain cells will therefore share the same GPM value.
   - NEVER interpolate coarse GPM pixels into unique 30m readings to imply false precision.

2. IMD (India Meteorological Department):
   - Future adapter role: IMD GFS/NCUM operational forecasts -> future rainfall intervals.
   - IMD historical 0.25 deg daily gridded rainfall -> historical calibration/training.
   - IMD operational API access may require credentials or experience downtime;
     future adapters must support resilient failure/fallback rather than assuming anonymous access.

3. NASA SMAP L4:
   - SMAP provides ~9 km 3-hourly surface and root-zone soil moisture estimates.
   - It is a regional environmental covariate, NOT an in-situ sensor measurement
     for every individual 30m hillside cell.
   - Multiple fine cells share the same SMAP value. Do not integrate SMAP until Phase 6+.

4. MULTI-SCALE RESOLUTION DISCIPLINE:
   - Terrain features (slope, aspect) are fine (~30m from SRTM/Copernicus DEM).
   - Meteorological & soil features (IMD/GPM/SMAP) are coarse (10-25 km).
   - NEVER upsample coarse atmospheric data and present it as independently measured
     fine-scale hyper-local weather.
════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DATA_DIR = _REPO_ROOT / "data" if (_REPO_ROOT / "data").exists() else _BACKEND_DIR / "data"
_SAMPLE_WEATHER_PATH = _DATA_DIR / "sample" / "sample_weather.json"


@dataclass
class ObservedRainfall:
    d_minus_2: float   # Rainfall observed 2 days ago (mm)
    d_minus_1: float   # Rainfall observed yesterday (mm)
    d0: float          # Rainfall observed in the most recent 24h (mm)


@dataclass
class ForecastIntervalRainfall:
    interval_0_24h: float   # Forecast rainfall in interval [NOW, +24h] (mm)
    interval_24_48h: float  # Forecast rainfall in interval [+24h, +48h] (mm)
    interval_48_72h: float  # Forecast rainfall in interval [+48h, +72h] (mm)


@dataclass
class RainfallSeries:
    zone_id: str
    observed_daily_mm: ObservedRainfall
    forecast_interval_mm: ForecastIntervalRainfall
    data_type: str
    is_live: bool
    source: str
    note: str


@lru_cache(maxsize=1)
def _load_sample_weather_file() -> dict:
    if not _SAMPLE_WEATHER_PATH.exists():
        raise FileNotFoundError(f"Sample weather file not found at {_SAMPLE_WEATHER_PATH}")
    with open(_SAMPLE_WEATHER_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_rainfall_series(zone_id: str) -> RainfallSeries:
    """
    Retrieves canonical rainfall observations and forecast intervals for a zone.

    data/sample/sample_weather.json is the sole authoritative SAMPLE_MOCK weather scenario dataset.
    This canonical rainfall adapter NEVER derives runtime values from legacy forecast_24h,
    forecast_48h, forecast_72h, forecast_risk_*, or forecast_score_* GeoJSON fields.
    Future phases will swap this data source for IMD/GPM adapters without altering
    the RainfallSeries interface or accumulator contracts.
    """
    zid = zone_id.upper()
    weather_dict = _load_sample_weather_file()

    if zid not in weather_dict:
        raise KeyError(f"Zone '{zid}' not found in canonical sample weather database.")

    raw = weather_dict[zid]
    obs_raw = raw.get("observed_daily_mm", {})
    fcst_raw = raw.get("forecast_interval_mm", {})

    # Validation: ensure non-null and non-negative
    for key in ["d_minus_2", "d_minus_1", "d0"]:
        if key not in obs_raw or obs_raw[key] is None:
            raise ValueError(f"Missing required observed rainfall bucket '{key}' for zone {zid}")
        if float(obs_raw[key]) < 0:
            raise ValueError(f"Negative observed rainfall for bucket '{key}' in zone {zid}: {obs_raw[key]}")

    for key in ["0_24h", "24_48h", "48_72h"]:
        if key not in fcst_raw or fcst_raw[key] is None:
            raise ValueError(f"Missing required forecast rainfall interval '{key}' for zone {zid}")
        if float(fcst_raw[key]) < 0:
            raise ValueError(f"Negative forecast rainfall for interval '{key}' in zone {zid}: {fcst_raw[key]}")

    observed = ObservedRainfall(
        d_minus_2=float(obs_raw["d_minus_2"]),
        d_minus_1=float(obs_raw["d_minus_1"]),
        d0=float(obs_raw["d0"]),
    )

    forecast = ForecastIntervalRainfall(
        interval_0_24h=float(fcst_raw["0_24h"]),
        interval_24_48h=float(fcst_raw["24_48h"]),
        interval_48_72h=float(fcst_raw["48_72h"]),
    )

    meta = raw.get("data_meta", {})

    return RainfallSeries(
        zone_id=zid,
        observed_daily_mm=observed,
        forecast_interval_mm=forecast,
        data_type=raw.get("data_type", "SAMPLE_MOCK"),
        is_live=meta.get("is_live", False),
        source=meta.get("source", "TerraSense Synthetic Scenario Weather Generator"),
        note=meta.get("note", "SAMPLE_MOCK non-overlapping rainfall data. Not real weather predictions."),
    )
