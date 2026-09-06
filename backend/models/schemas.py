"""
Pydantic v2 schemas for all TerraSense API responses.

RULE: Every response touching risk data must carry a DataMeta object.
      data_type must be "SAMPLE_MOCK" while real data is not connected.
      is_live must be False in sample mode.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ── Shared ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DataMeta(BaseModel):
    data_type: str = "SAMPLE_MOCK"
    source: str = "TerraSense demo dataset"
    timestamp: str = Field(default_factory=_now_iso)
    is_live: bool = False
    note: Optional[str] = None


SAMPLE_META = DataMeta(
    data_type="SAMPLE_MOCK",
    source="TerraSense demo dataset v0.1",
    is_live=False,
    note="All values are fabricated for UI/API testing. Phase 5 connects real data.",
)


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    data_mode: str
    version: str
    disclaimer: str
    endpoints: List[str]


# ── Zones / GeoJSON pass-through ──────────────────────────────────────────────

class ZonesResponse(BaseModel):
    """Wraps the full GeoJSON FeatureCollection with API metadata."""
    type: str = "FeatureCollection"
    feature_count: int
    data_meta: DataMeta
    features: list  # raw GeoJSON feature list


# ── Current Risk ──────────────────────────────────────────────────────────────

class ZoneRisk(BaseModel):
    zone_id: str
    risk_category: str
    risk_score: float
    slope: float
    elevation: float
    soil_moisture: float
    rain_24h: float
    rain_3d: float
    rain_7d: float
    data_meta: DataMeta


class AllZonesRiskResponse(BaseModel):
    zones: List[ZoneRisk]
    total: int
    data_meta: DataMeta


# ── Forecast ─────────────────────────────────────────────────────────────────

class ForecastWindow(BaseModel):
    risk: str
    risk_score: float
    antecedent_rain_mm: float


class ZoneForecastResponse(BaseModel):
    """
    Matches the TypeScript ZoneForecast interface in frontend/src/types/index.ts.
    antecedent_rain_mm values are pre-computed in the sample dataset.
    Phase 4 backend will compute these dynamically from the rainfall accumulator.
    """
    zone_id: str
    current: str          # maps to ZoneForecast.current in TS
    current_score: float
    forecast: Dict[str, ForecastWindow]  # keys: "24h", "48h", "72h"
    data_meta: DataMeta


# ── Weather ───────────────────────────────────────────────────────────────────

class WeatherResponse(BaseModel):
    """
    Rainfall inputs for a zone. All values SAMPLE_MOCK in Phase 3.
    Phase 5+ replaces with real IMD/GPM observations.
    """
    zone_id: str
    rain_24h_mm: float
    rain_3d_mm: float
    rain_7d_mm: float
    forecast_24h_mm: float
    forecast_48h_mm: float
    forecast_72h_mm: float
    antecedent_24h_mm: float   # observed_24h + forecast_24h
    antecedent_48h_mm: float
    antecedent_72h_mm: float
    data_meta: DataMeta


# ── Error ─────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str
    data_meta: DataMeta = Field(default_factory=lambda: DataMeta())
