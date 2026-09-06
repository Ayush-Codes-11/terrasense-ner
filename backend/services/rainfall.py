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
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DATA_DIR = _REPO_ROOT / "data" if (_REPO_ROOT / "data").exists() else _BACKEND_DIR / "data"
_SAMPLE_WEATHER_PATH = _DATA_DIR / "sample" / "sample_weather.json"


try:
    from services.gpm_loader import get_zone_gpm_observed
except ImportError:
    try:
        from backend.services.gpm_loader import get_zone_gpm_observed
    except ImportError:
        def get_zone_gpm_observed(z: str):
            return None


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
    observed_provenance: str = "SAMPLE_MOCK"
    forecast_provenance: str = "SAMPLE_MOCK"
    observation_timestamp: Optional[str] = None
    observed_buckets_meta: Optional[Dict[str, Any]] = None


@lru_cache(maxsize=1)
def _load_sample_weather_file() -> dict:
    if not _SAMPLE_WEATHER_PATH.exists():
        raise FileNotFoundError(f"Sample weather file not found at {_SAMPLE_WEATHER_PATH}")
    with open(_SAMPLE_WEATHER_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_rainfall_series(zone_id: str) -> RainfallSeries:
    """
    Retrieves canonical rainfall observations and forecast intervals for a zone.

    Phase 8:
    - Observed daily buckets (D-2, D-1, D0) are sourced from REAL NASA GPM IMERG
      via services.gpm_loader if available.
    - Future forecast intervals (+24h, +48h, +72h) remain SAMPLE_MOCK scenarios.
    - If GPM data is unavailable or invalid, falls back gracefully to SAMPLE_FALLBACK.
    """
    zid = zone_id.upper()
    weather_dict = _load_sample_weather_file()

    if zid not in weather_dict:
        raise KeyError(f"Zone '{zid}' not found in canonical sample weather database.")

    raw = weather_dict[zid]
    obs_raw = raw.get("observed_daily_mm", {})
    fcst_raw = raw.get("forecast_interval_mm", {})

    # Validation of forecast intervals (always present)
    for key in ["0_24h", "24_48h", "48_72h"]:
        if key not in fcst_raw or fcst_raw[key] is None:
            raise ValueError(f"Missing required forecast rainfall interval '{key}' for zone {zid}")
        if float(fcst_raw[key]) < 0:
            raise ValueError(f"Negative forecast rainfall for interval '{key}' in zone {zid}: {fcst_raw[key]}")

    forecast = ForecastIntervalRainfall(
        interval_0_24h=float(fcst_raw["0_24h"]),
        interval_24_48h=float(fcst_raw["24_48h"]),
        interval_48_72h=float(fcst_raw["48_72h"]),
    )

    # Check for Real GPM IMERG observations
    try:
        from backend.services.gpm_loader import get_gpm_provenance_status
        prov_status = get_gpm_provenance_status()
    except ImportError:
        prov_status = {"status": "SAMPLE_MOCK"}

    gpm_data = get_zone_gpm_observed(zid) if callable(get_zone_gpm_observed) else None

    if gpm_data and "observed_daily_mm" in gpm_data:
        gpm_obs = gpm_data["observed_daily_mm"]
        d2 = float(gpm_obs["d_minus_2"])
        d1 = float(gpm_obs["d_minus_1"])
        d0 = float(gpm_obs["d0"])

        for k, v in [("d_minus_2", d2), ("d_minus_1", d1), ("d0", d0)]:
            if v < 0 or not math.isfinite(v):
                raise ValueError(f"Invalid real GPM rainfall for '{k}' in zone {zid}: {v}")

        observed = ObservedRainfall(d_minus_2=d2, d_minus_1=d1, d0=d0)
        observed_prov = prov_status.get("status", "SAMPLE_MOCK")
        data_type = observed_prov
        obs_buckets_meta = gpm_data.get("observed_buckets")
        obs_timestamp = gpm_data.get("observed_buckets", {}).get("d0", {}).get("window_end_utc")
        source = prov_status.get("source", "NASA GPM IMERG")
        note = (
            f"Observed rainfall from {source}. "
            "Future forecast intervals are SAMPLE_MOCK scenario."
        )
    else:
        # Fallback to sample weather
        for key in ["d_minus_2", "d_minus_1", "d0"]:
            if key not in obs_raw or obs_raw[key] is None:
                raise ValueError(f"Missing required observed rainfall bucket '{key}' for zone {zid}")
            if float(obs_raw[key]) < 0:
                raise ValueError(f"Negative observed rainfall for bucket '{key}' in zone {zid}: {obs_raw[key]}")

        observed = ObservedRainfall(
            d_minus_2=float(obs_raw["d_minus_2"]),
            d_minus_1=float(obs_raw["d_minus_1"]),
            d0=float(obs_raw["d0"]),
        )
        observed_prov = "SAMPLE_MOCK"
        data_type = raw.get("data_type", "SAMPLE_MOCK")
        obs_buckets_meta = None
        obs_timestamp = None
        source = raw.get("data_meta", {}).get("source", "TerraSense Synthetic Scenario Weather Generator")
        note = "SAMPLE_FALLBACK: Real GPM data not loaded. Using sample mock rainfall."

    return RainfallSeries(
        zone_id=zid,
        observed_daily_mm=observed,
        forecast_interval_mm=forecast,
        data_type=data_type,
        is_live=False,
        source=source,
        note=note,
        observed_provenance=observed_prov,
        forecast_provenance="SAMPLE_MOCK",
        observation_timestamp=obs_timestamp,
        observed_buckets_meta=obs_buckets_meta,
    )
