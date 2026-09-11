"""
Pydantic models and Enums for the NER spatial hierarchy.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CoverageLevel(str, Enum):
    DISTRICT_BOUNDARY_ONLY = "DISTRICT_BOUNDARY_ONLY"
    DETAILED_PILOT = "DETAILED_PILOT"


class RiskModelStatus(str, Enum):
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    STATIC_ML_VALIDATION_PENDING = "STATIC_ML_VALIDATION_PENDING"


class ZoneType(str, Enum):
    PROTOTYPE_ANALYSIS_GRID = "PROTOTYPE_ANALYSIS_GRID"


class HierarchyStatus(str, Enum):
    READY = "READY"
    BOUNDARY_DATA_UNAVAILABLE = "BOUNDARY_DATA_UNAVAILABLE"
    BOUNDARY_DATA_INVALID = "BOUNDARY_DATA_INVALID"


class Region(BaseModel):
    region_id: str
    region_name: str


class State(BaseModel):
    state_id: str
    state_name: str
    region_id: str


class District(BaseModel):
    district_id: str
    district_name: str
    state_id: str
    lgd_code: Optional[str] = None
    source_feature_id: Optional[str] = None
    coverage_level: CoverageLevel
    risk_model_status: RiskModelStatus

    model_config = ConfigDict(use_enum_values=True)


class AnalysisZoneMetadata(BaseModel):
    zone_id: str
    district_id: str
    zone_type: ZoneType

    model_config = ConfigDict(use_enum_values=True)

class RegionListResponse(BaseModel):
    count: int
    items: list[Region]

class StateListResponse(BaseModel):
    count: int
    items: list[State]

class DistrictListResponse(BaseModel):
    count: int
    items: list[District]
