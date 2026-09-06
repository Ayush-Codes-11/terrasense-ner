"""
GET /weather/{zone_id} — canonical rainfall observations and forecast intervals for a zone.

Phase 5: Served via backend/services/rainfall.py and backend/services/rainfall_accumulator.py.
Outputs non-overlapping observed days, forecast intervals, and rolling antecedent accumulation.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from models.schemas import DataMeta, WeatherResponse
from services.rainfall import get_rainfall_series
from services.rainfall_accumulator import compute_zone_rolling_rainfall

router = APIRouter(prefix="/weather")


@router.get("/{zone_id}", response_model=WeatherResponse)
def get_zone_weather(zone_id: str):
    """
    Returns canonical rainfall observations, non-overlapping forecast intervals,
    and rolling 3-day antecedent accumulation for a zone.
    """
    zid = zone_id.upper()
    try:
        series = get_rainfall_series(zid)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zid}' not found. Valid IDs are A01–E05.",
        )

    rolling = compute_zone_rolling_rainfall(series)

    return WeatherResponse(
        zone_id=zid,
        observed_daily_mm={
            "d_minus_2": series.observed_daily_mm.d_minus_2,
            "d_minus_1": series.observed_daily_mm.d_minus_1,
            "d0": series.observed_daily_mm.d0,
        },
        forecast_interval_mm={
            "0_24h": series.forecast_interval_mm.interval_0_24h,
            "24_48h": series.forecast_interval_mm.interval_24_48h,
            "48_72h": series.forecast_interval_mm.interval_48_72h,
        },
        rolling_3d_accumulation_mm={
            "now": rolling.now.antecedent_3d_mm,
            "24h": rolling.h24.antecedent_3d_mm,
            "48h": rolling.h48.antecedent_3d_mm,
            "72h": rolling.h72.antecedent_3d_mm,
        },
        recent_24h_mm={
            "now": rolling.now.recent_24h_mm,
            "24h": rolling.h24.recent_24h_mm,
            "48h": rolling.h48.recent_24h_mm,
            "72h": rolling.h72.recent_24h_mm,
        },
        data_meta=DataMeta(
            data_type=series.data_type,
            source=series.source,
            is_live=series.is_live,
            note=series.note,
        ),
    )
