"""
Pydantic v2 schemas for all TerraSense API responses.

RULE: Every response touching risk data must carry a DataMeta object.
      data_type must be "SAMPLE_MOCK" while real data is not connected.
      is_live must be False in sample mode.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
    note="All input values are SAMPLE_MOCK for UI/API testing. Phase 5 connects real data.",
)


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    data_mode: str
    risk_engine: str = "prototype_scorer_active"
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

class ContributorSchema(BaseModel):
    feature: str
    contribution: float
    component: Optional[str] = None
    display_name: Optional[str] = None
    normalized_input: Optional[float] = None
    weight: Optional[float] = None


class NormalizedFeatures(BaseModel):
    """
    Normalized feature inputs in range [0.0, 1.0].
    These represent scaled physical inputs (raw_value / reference, capped at 1.0),
    NOT the final weighted contributions.
    """
    terrain: float
    recent_rainfall: float
    antecedent_rainfall: float
    soil_wetness: float


class ZoneRisk(BaseModel):
    zone_id: str
    risk_category: str
    risk_score: float   # Kept for backward compatibility
    score: float        # Explicit prototype risk score [0, 1]
    score_type: str = "prototype_relative_risk_score"
    is_probability: bool = False
    is_calibrated: bool = False
    computed_by: str = "prototype_scorer_v1"

    slope: float
    elevation: float
    soil_moisture: float
    soil_wetness_index: float
    soil_wetness_note: str = "SAMPLE_MOCK normalized index [0.0, 1.0] (not a real SMAP observation)"
    rain_24h: float
    rain_3d: float
    rain_7d: Optional[float] = None

    # Nested normalized inputs (raw / reference capped at 1.0)
    normalized_features: NormalizedFeatures

    # Sorted by absolute contribution descending (actual weighted contributions)
    contributors: Optional[List[ContributorSchema]] = None

    data_meta: DataMeta


class AllZonesRiskResponse(BaseModel):
    zones: List[ZoneRisk]
    total: int
    data_meta: DataMeta


# ── Forecast ─────────────────────────────────────────────────────────────────

class NowWindow(BaseModel):
    risk: str
    risk_score: float
    mode: str = "PROTOTYPE_COMPUTED"
    score_type: str = "prototype_relative_risk_score"
    is_probability: bool = False
    is_calibrated: bool = False
    computed_by: str = "prototype_scorer_v1"


class ForecastWindow(BaseModel):
    risk: str
    risk_score: float
    antecedent_rain_mm: float
    mode: str = "SAMPLE_MOCK"
    phase: str = "Phase 5 pending"


class ZoneForecastResponse(BaseModel):
    """
    NOW is computed dynamically by ml.prototype_scorer.
    +24h, +48h, +72h windows are marked SAMPLE_MOCK (Phase 5 pending).
    """
    zone_id: str
    current: str          # maps to ZoneForecast.current in TS
    current_score: float  # maps to ZoneForecast.current_score in TS
    now: NowWindow
    forecast: Dict[str, ForecastWindow]  # keys: "24h", "48h", "72h"
    data_meta: DataMeta


# ── Weather ───────────────────────────────────────────────────────────────────

class WeatherResponse(BaseModel):
    """
    Rainfall inputs for a zone. All values SAMPLE_MOCK in Phase 3/4.
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
