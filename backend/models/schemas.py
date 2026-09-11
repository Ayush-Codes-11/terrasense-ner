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
    risk_engine: str = "prototype_scorer_active"
    data_mode: str
    phase: str
    disclaimer: str
    data_sources: Optional[Dict[str, str]] = None
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

    # Feature-level data provenance (Phase 7)
    feature_provenance: Optional[Dict[str, str]] = Field(
        default=None,
        description=(
            "Data source for each feature input. "
            "'REAL_DEM' = Copernicus GLO-30; 'SAMPLE_MOCK' = synthetic sample value."
        ),
    )

    data_meta: DataMeta


class AllZonesRiskResponse(BaseModel):
    zones: List[ZoneRisk]
    total: int
    data_meta: DataMeta


# ── Forecast / Risk Outlook ──────────────────────────────────────────────────

class HorizonWindowSchema(BaseModel):
    horizon: str                       # "now" | "24h" | "48h" | "72h"
    risk_category: str                 # "LOW" | "MODERATE" | "HIGH" | "VERY_HIGH"
    risk: str                          # Alias for backwards-compat with TS
    risk_score: float                  # prototype relative risk score [0, 1]
    score: float                       # Alias for risk_score
    mode: str = "PROTOTYPE_COMPUTED"
    input_data_type: str = "SAMPLE_MOCK"
    score_type: str = "prototype_relative_risk_score"
    is_probability: bool = False
    is_calibrated: bool = False
    computed_by: str = "prototype_scorer_v1"

    # Rainfall context responsible for this horizon
    recent_24h_rain_mm: float
    antecedent_3d_rain_mm: float
    antecedent_rain_mm: float          # Alias for backwards-compat with TS
    forecast_interval_rain_mm: Optional[float] = None

    normalized_features: Optional[Dict[str, float]] = None
    contributors: Optional[List[ContributorSchema]] = None


class ZoneForecastResponse(BaseModel):
    """
    Phase 5: Weather-linked landslide-risk outlook.
    ALL horizons (NOW, +24h, +48h, +72h) are dynamically computed by ml.prototype_scorer
    using rolling 3-day antecedent rainfall accumulation.
    """
    zone_id: str
    current: str          # current risk category
    current_score: float  # current risk score

    # Structured 4-window dictionary: "now", "24h", "48h", "72h"
    windows: Dict[str, HorizonWindowSchema]

    # Backward compatibility accessors
    now: HorizonWindowSchema
    forecast: Dict[str, HorizonWindowSchema]  # "24h", "48h", "72h"

    # Deterministic transition explanation
    risk_change_summary: str
    transition_details: List[str]

    # Feature-level data provenance (Phase 7)
    feature_provenance: Optional[Dict[str, str]] = Field(
        default=None,
        description=(
            "Data source for each feature input. "
            "'REAL_DEM' = Copernicus GLO-30; 'SAMPLE_MOCK' = synthetic sample value."
        ),
    )

    data_meta: DataMeta


# ── Weather ───────────────────────────────────────────────────────────────────

class WeatherResponse(BaseModel):
    """
    Canonical rainfall series & rolling accumulation for a zone.
    Phase 8: observed daily buckets sourced from real NASA GPM IMERG if available;
    forecast intervals remain SAMPLE_MOCK scenario.
    """
    zone_id: str
    observed_daily_mm: Dict[str, float]
    forecast_interval_mm: Dict[str, float]
    rolling_3d_accumulation_mm: Dict[str, float]
    recent_24h_mm: Dict[str, float]
    observed_provenance: Optional[str] = "SAMPLE_MOCK"
    forecast_provenance: Optional[str] = "SAMPLE_MOCK"
    observation_timestamp: Optional[str] = None
    observed_buckets: Optional[Dict[str, Any]] = None
    data_meta: DataMeta


# ── Geodata & OSM Status ──────────────────────────────────────────────────────

class OSMStatusResponse(BaseModel):
    status: str  # "OSM snapshot" | "Cached OSM" | "Sample fallback"
    is_real: bool
    retrieved_at: Optional[str] = None
    layers_retrieved_at: Optional[Dict[str, str]] = None
    dataset_description: Optional[str] = None
    source: str
    attribution: str
    feature_counts: Dict[str, int]
    data_meta: DataMeta


# ── Exposure (Phase 6) ────────────────────────────────────────────────────────

class ExposedRoadSchema(BaseModel):
    feature_id: str
    name: Optional[str] = None
    highway: str
    length_km: float
    is_motorable: bool = True
    access: Optional[str] = None
    access_restricted: bool = False
    blockage_verified: bool = False
    road_status: str = "EXPOSED_NOT_VERIFIED_BLOCKED"


class ExposedSettlementSchema(BaseModel):
    feature_id: str
    name: Optional[str] = None
    place: str
    community_id: Optional[str] = None


class ExposedFacilitySchema(BaseModel):
    feature_id: str
    name: Optional[str] = None
    category: str
    amenity: Optional[str] = None
    healthcare: Optional[str] = None
    is_whitelisted: bool = True


class ExposureSummarySchema(BaseModel):
    osm_road_segments_count: int = 0
    motorable_road_segments_count: int = 0
    motorable_road_km: float = 0.0
    total_road_km: float = 0.0
    pedestrian_road_km: float = 0.0
    track_road_km: float = 0.0
    mapped_communities: int = 0
    critical_facilities: int = 0
    roads_blocked: int = 0  # Only >0 if verified field report exists

    # Backward compatibility aliases
    roads_exposed: int = 0
    roads_exposed_km: float = 0.0
    villages_exposed: int = 0
    hospitals_exposed: int = 0


class ZoneExposureResponse(BaseModel):
    zone_id: str
    summary: ExposureSummarySchema
    roads: List[ExposedRoadSchema]
    settlements: List[ExposedSettlementSchema]
    critical_facilities: List[ExposedFacilitySchema]
    hazard_geometry: str = "SAMPLE_MOCK"
    exposure_features: str = "REAL_OSM"
    analysis_mode: str = "PROTOTYPE_MIXED_PROVENANCE"
    data_meta: DataMeta


# ── Prototype Decision-Support Priority (Phase 6) ─────────────────────────────

class PriorityContributorSchema(BaseModel):
    component: str
    display_name: str
    weight: float
    raw_value: float
    normalized_input: float
    contribution: float


class HorizonPrioritySchema(BaseModel):
    horizon: str
    priority: str
    priority_score: float
    landslide_risk_score: float
    landslide_risk_category: str
    score_type: str = "prototype_decision_support_priority"
    is_official_standard: bool = False
    is_operationally_validated: bool = False
    contributors: List[PriorityContributorSchema]


class ZonePriorityResponse(BaseModel):
    zone_id: str
    priority: str
    priority_score: float
    priority_label: str = "PROTOTYPE DECISION-SUPPORT — NOT OFFICIAL"
    windows: Dict[str, HorizonPrioritySchema]
    now: HorizonPrioritySchema
    forecast: Dict[str, HorizonPrioritySchema]  # "24h", "48h", "72h"
    explanation: str
    horizon_transitions: List[str]
    exposure_summary: Dict[str, Any]
    hazard_geometry: str = "SAMPLE_MOCK"
    exposure_features: str = "REAL_OSM"
    analysis_mode: str = "PROTOTYPE_MIXED_PROVENANCE"
    data_meta: DataMeta


# ── Error ─────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str
    data_meta: DataMeta = Field(default_factory=lambda: DataMeta())

