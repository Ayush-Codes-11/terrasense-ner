"""
rainfall_accumulator.py — Rolling antecedent rainfall accumulation engine.

══════════════════════════════════════════════════════════════════════
SCIENTIFIC FORMULATION:
The 3-day antecedent window must roll forward strictly with time.
Do NOT calculate 'current_3day_rain + forecast_rain' — older rainfall
must exit the 3-day rolling window as new rainfall enters.

Using:
  D-2 : Rainfall observed 2 days ago
  D-1 : Rainfall observed yesterday
  D0  : Rainfall observed in the most recent 24h
  F1  : Forecast rainfall for interval [0, 24h]
  F2  : Forecast rainfall for interval [24h, 48h]
  F3  : Forecast rainfall for interval [48h, 72h]

Rolling Horizons:
  NOW:
    recent_24h    = D0
    antecedent_3d = D-2 + D-1 + D0
    forecast_rain = None (observed horizon)

  +24h:
    recent_24h    = F1
    antecedent_3d = D-1 + D0 + F1   (D-2 rolls out)
    forecast_rain = F1

  +48h:
    recent_24h    = F2
    antecedent_3d = D0 + F1 + F2    (D-1 rolls out)
    forecast_rain = F2

  +72h:
    recent_24h    = F3
    antecedent_3d = F1 + F2 + F3    (D0 rolls out)
    forecast_rain = F3
══════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional
from services.rainfall import RainfallSeries


@dataclass
class HorizonRainfall:
    horizon: str                       # "now" | "24h" | "48h" | "72h"
    recent_24h_mm: float              # 24h rainfall effective in this window
    antecedent_3d_mm: float           # Rolling 3-day accumulation
    forecast_interval_rain_mm: Optional[float]  # None for "now", interval value for future


@dataclass
class RollingAccumulationResult:
    zone_id: str
    now: HorizonRainfall
    h24: HorizonRainfall
    h48: HorizonRainfall
    h72: HorizonRainfall


def calculate_rolling_accumulation(
    d_minus_2: float,
    d_minus_1: float,
    d0: float,
    f1: float,
    f2: float,
    f3: float,
    zone_id: str = "UNKNOWN",
) -> RollingAccumulationResult:
    """
    Computes rolling 3-day antecedent rainfall and 24h rainfall for all 4 horizons.

    Raises
    ------
    ValueError : If any rainfall input is None, NaN/inf, or negative.
    """
    inputs = {
        "d_minus_2": d_minus_2,
        "d_minus_1": d_minus_1,
        "d0": d0,
        "f1": f1,
        "f2": f2,
        "f3": f3,
    }

    for name, val in inputs.items():
        if val is None:
            raise ValueError(f"Missing required rainfall input '{name}'")
        if not math.isfinite(val):
            raise ValueError(f"Non-finite rainfall input '{name}': {val}")
        if val < 0.0:
            raise ValueError(
                f"Physically invalid negative rainfall for '{name}': {val} mm. "
                "Rainfall must be non-negative."
            )

    # ── 1. NOW ───────────────────────────────────────────────────────────────
    now_recent = round(d0, 2)
    now_antecedent = round(d_minus_2 + d_minus_1 + d0, 2)

    # ── 2. +24h (D-2 drops out, F1 enters) ───────────────────────────────────
    h24_recent = round(f1, 2)
    h24_antecedent = round(d_minus_1 + d0 + f1, 2)

    # ── 3. +48h (D-1 drops out, F2 enters) ───────────────────────────────────
    h48_recent = round(f2, 2)
    h48_antecedent = round(d0 + f1 + f2, 2)

    # ── 4. +72h (D0 drops out, F3 enters) ────────────────────────────────────
    h72_recent = round(f3, 2)
    h72_antecedent = round(f1 + f2 + f3, 2)

    return RollingAccumulationResult(
        zone_id=zone_id,
        now=HorizonRainfall(
            horizon="now",
            recent_24h_mm=now_recent,
            antecedent_3d_mm=now_antecedent,
            forecast_interval_rain_mm=None,
        ),
        h24=HorizonRainfall(
            horizon="24h",
            recent_24h_mm=h24_recent,
            antecedent_3d_mm=h24_antecedent,
            forecast_interval_rain_mm=h24_recent,
        ),
        h48=HorizonRainfall(
            horizon="48h",
            recent_24h_mm=h48_recent,
            antecedent_3d_mm=h48_antecedent,
            forecast_interval_rain_mm=h48_recent,
        ),
        h72=HorizonRainfall(
            horizon="72h",
            recent_24h_mm=h72_recent,
            antecedent_3d_mm=h72_antecedent,
            forecast_interval_rain_mm=h72_recent,
        ),
    )


def compute_zone_rolling_rainfall(series: RainfallSeries) -> RollingAccumulationResult:
    """Helper accepting a RainfallSeries object."""
    return calculate_rolling_accumulation(
        d_minus_2=series.observed_daily_mm.d_minus_2,
        d_minus_1=series.observed_daily_mm.d_minus_1,
        d0=series.observed_daily_mm.d0,
        f1=series.forecast_interval_mm.interval_0_24h,
        f2=series.forecast_interval_mm.interval_24_48h,
        f3=series.forecast_interval_mm.interval_48_72h,
        zone_id=series.zone_id,
    )
