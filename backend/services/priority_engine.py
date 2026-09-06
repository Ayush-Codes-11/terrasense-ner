"""
priority_engine.py — Prototype Decision-Support Priority scoring engine for TerraSense NER.

════════════════════════════════════════════════════════════════════════════════
ARCHITECTURAL SPECIFICATION:
1. FORMULA:
   priority_score =
       0.60 * landslide_risk_score
     + 0.15 * normalized_road_exposure
     + 0.15 * normalized_settlement_exposure
     + 0.10 * normalized_critical_facility_exposure
   (Sum of weights = 1.0)

2. 4-HORIZON CONSISTENCY:
   Exposure geography is static for a zone.
   Priority is computed across NOW, +24h, +48h, +72h as landslide risk changes.

3. DETERMINISTIC EXPLANATIONS:
   Rainfall is described only indirectly through the computed landslide-risk outlook.
   Uses phrases like "lie within/intersect the prototype hazard zone".

4. SCORE METADATA:
   score_type = "prototype_decision_support_priority"
   is_official_standard = False
   is_operationally_validated = False
════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.services.exposure_engine import compute_zone_exposure, ZoneExposureResult
from backend.services.priority_config import (
    WEIGHT_LANDSLIDE_RISK,
    WEIGHT_ROAD_EXPOSURE,
    WEIGHT_SETTLEMENT_EXPOSURE,
    WEIGHT_CRITICAL_FACILITY_EXPOSURE,
    REF_ROAD_EXPOSURE_KM,
    REF_SETTLEMENTS_COUNT,
    REF_CRITICAL_FACILITIES_COUNT,
    get_priority_category,
)
from backend.services.risk_forecast import compute_zone_risk_outlook, RiskOutlookResult
from backend.services.data_loader import get_zone_props


@dataclass
class PriorityContributor:
    component: str
    display_name: str
    weight: float
    raw_value: float
    normalized_input: float
    contribution: float


@dataclass
class HorizonPriorityResult:
    horizon: str
    priority: str
    priority_score: float
    landslide_risk_score: float
    landslide_risk_category: str
    score_type: str
    is_official_standard: bool
    is_operationally_validated: bool
    contributors: List[PriorityContributor]


@dataclass
class PriorityOutlookResult:
    zone_id: str
    exposure_summary: Dict[str, Any]
    now: HorizonPriorityResult
    h24: HorizonPriorityResult
    h48: HorizonPriorityResult
    h72: HorizonPriorityResult
    explanation: str
    horizon_transitions: List[str]
    hazard_geometry: str
    exposure_features: str
    analysis_mode: str
    data_source: str
    attribution: str
    note: str


def score_single_priority(
    horizon: str,
    landslide_risk_score: float,
    landslide_risk_category: str,
    road_km: float,
    settlements_count: int,
    facilities_count: int,
) -> HorizonPriorityResult:
    """
    Computes priority score and contributor breakdown for a single temporal horizon.
    """
    norm_risk = min(max(0.0, float(landslide_risk_score)), 1.0)
    norm_road = min(max(0.0, float(road_km)) / REF_ROAD_EXPOSURE_KM, 1.0)
    norm_settlements = min(max(0.0, float(settlements_count)) / REF_SETTLEMENTS_COUNT, 1.0)
    norm_facilities = min(max(0.0, float(facilities_count)) / REF_CRITICAL_FACILITIES_COUNT, 1.0)

    contrib_risk = round(WEIGHT_LANDSLIDE_RISK * norm_risk, 4)
    contrib_road = round(WEIGHT_ROAD_EXPOSURE * norm_road, 4)
    contrib_settlements = round(WEIGHT_SETTLEMENT_EXPOSURE * norm_settlements, 4)
    contrib_facilities = round(WEIGHT_CRITICAL_FACILITY_EXPOSURE * norm_facilities, 4)

    total_score = round(contrib_risk + contrib_road + contrib_settlements + contrib_facilities, 4)
    category = get_priority_category(total_score)

    contributors = [
        PriorityContributor(
            component="landslide_risk",
            display_name="Landslide risk outlook",
            weight=WEIGHT_LANDSLIDE_RISK,
            raw_value=round(landslide_risk_score, 4),
            normalized_input=round(norm_risk, 4),
            contribution=contrib_risk,
        ),
        PriorityContributor(
            component="road_exposure",
            display_name="Mapped motorable road exposure",
            weight=WEIGHT_ROAD_EXPOSURE,
            raw_value=round(road_km, 3),
            normalized_input=round(norm_road, 4),
            contribution=contrib_road,
        ),
        PriorityContributor(
            component="critical_facility_exposure",
            display_name="Critical facility proximity",
            weight=WEIGHT_CRITICAL_FACILITY_EXPOSURE,
            raw_value=float(facilities_count),
            normalized_input=round(norm_facilities, 4),
            contribution=contrib_facilities,
        ),
    ]

    # Sort contributors descending by contribution
    contributors.sort(key=lambda c: c.contribution, reverse=True)

    return HorizonPriorityResult(
        horizon=horizon,
        priority=category,
        priority_score=total_score,
        landslide_risk_score=round(landslide_risk_score, 4),
        landslide_risk_category=landslide_risk_category,
        score_type="prototype_decision_support_priority",
        is_official_standard=False,
        is_operationally_validated=False,
        contributors=contributors,
    )


def compute_zone_priority(
    zone_id: str,
    zone_props: Optional[dict] = None,
    exposure_result: Optional[ZoneExposureResult] = None,
    risk_outlook: Optional[RiskOutlookResult] = None,
) -> PriorityOutlookResult:
    """
    Computes Prototype Decision-Support Priority across all 4 horizons (NOW, +24h, +48h, +72h).
    """
    zid = zone_id.upper()

    if zone_props is None:
        zone_props = get_zone_props(zid)
        if zone_props is None:
            raise KeyError(f"Zone '{zid}' not found.")

    if exposure_result is None:
        exposure_result = compute_zone_exposure(zid)

    if risk_outlook is None:
        risk_outlook = compute_zone_risk_outlook(zone_props)

    road_km = exposure_result.motorable_road_km
    settlements = exposure_result.communities_exposed
    facilities = exposure_result.critical_facilities_exposed

    now_p = score_single_priority("now", risk_outlook.now.risk_score, risk_outlook.now.risk_category, road_km, settlements, facilities)
    h24_p = score_single_priority("24h", risk_outlook.h24.risk_score, risk_outlook.h24.risk_category, road_km, settlements, facilities)
    h48_p = score_single_priority("48h", risk_outlook.h48.risk_score, risk_outlook.h48.risk_category, road_km, settlements, facilities)
    h72_p = score_single_priority("72h", risk_outlook.h72.risk_score, risk_outlook.h72.risk_category, road_km, settlements, facilities)

    # Build deterministic explanation
    # Note: Describe rainfall only indirectly through the computed landslide-risk outlook.
    # Prefer: "lie within/intersect the prototype hazard zone"
    transitions = []

    # +24h transition
    if h24_p.priority != now_p.priority:
        verb = "rises" if h24_p.priority_score > now_p.priority_score else "eases"
        transitions.append(
            f"Priority {verb} at +24h to {h24_p.priority} (score {h24_p.priority_score:.4f}) "
            f"because the landslide-risk outlook increases to {h24_p.landslide_risk_category} ({h24_p.landslide_risk_score:.4f}) "
            f"while {road_km:.2f} km of mapped motorable roads and {facilities} critical facilities intersect the prototype hazard zone."
        )
    else:
        transitions.append(
            f"Priority remains {now_p.priority} at +24h (score {h24_p.priority_score:.4f}) "
            f"as the landslide-risk outlook holds at {h24_p.landslide_risk_category} ({h24_p.landslide_risk_score:.4f}) "
            f"while {road_km:.2f} km of mapped motorable roads and {facilities} critical facilities intersect the prototype hazard zone."
        )

    # +48h transition
    if h48_p.priority != h24_p.priority:
        verb = "rises further" if h48_p.priority_score > h24_p.priority_score else "eases"
        transitions.append(
            f"Priority {verb} at +48h to {h48_p.priority} (score {h48_p.priority_score:.4f}) "
            f"as the landslide-risk outlook shifts to {h48_p.landslide_risk_category}."
        )
    else:
        transitions.append(
            f"Priority persists at {h24_p.priority} at +48h (score {h48_p.priority_score:.4f}) "
            f"matching the elevated landslide-risk outlook ({h48_p.landslide_risk_category})."
        )

    # +72h transition
    if h72_p.priority != h48_p.priority:
        verb = "escalates" if h72_p.priority_score > h48_p.priority_score else "moderates"
        transitions.append(
            f"Priority {verb} at +72h to {h72_p.priority} (score {h72_p.priority_score:.4f}) "
            f"as the landslide-risk outlook eases to {h72_p.landslide_risk_category} ({h72_p.landslide_risk_score:.4f})."
        )
    else:
        transitions.append(
            f"Priority remains {h48_p.priority} at +72h (score {h72_p.priority_score:.4f})."
        )

    # Overall explanation summary
    peak_p = max(now_p.priority_score, h24_p.priority_score, h48_p.priority_score, h72_p.priority_score)
    peak_horiz = "NOW" if peak_p == now_p.priority_score else "+24h" if peak_p == h24_p.priority_score else "+48h" if peak_p == h48_p.priority_score else "+72h"
    summary_explanation = (
        f"Peak decision-support priority is {h24_p.priority if peak_horiz == '+24h' else now_p.priority} ({peak_p:.4f}) at {peak_horiz}, "
        f"driven by elevated landslide-risk outlook combined with {road_km:.2f} km of mapped motorable roads and "
        f"{facilities} critical facilities intersecting the prototype hazard zone."
    )

    exposure_summary = {
        "osm_road_segments_count": exposure_result.osm_road_segments_count,
        "motorable_road_segments_count": exposure_result.motorable_road_segments_count,
        "motorable_road_km": exposure_result.motorable_road_km,
        "total_road_km": exposure_result.total_road_km,
        "pedestrian_road_km": exposure_result.pedestrian_road_km,
        "track_road_km": exposure_result.track_road_km,
        "mapped_communities": exposure_result.communities_exposed,
        "critical_facilities": exposure_result.critical_facilities_exposed,
        "blockage_verified": False,
        "road_status": "EXPOSED_NOT_VERIFIED_BLOCKED",
        # Backward compatibility
        "roads_exposed_count": exposure_result.osm_road_segments_count,
        "roads_exposed_km": exposure_result.motorable_road_km,
        "settlements_exposed": exposure_result.communities_exposed,
        "critical_facilities_exposed": exposure_result.critical_facilities_exposed,
    }

    return PriorityOutlookResult(
        zone_id=zid,
        exposure_summary=exposure_summary,
        now=now_p,
        h24=h24_p,
        h48=h48_p,
        h72=h72_p,
        explanation=summary_explanation,
        horizon_transitions=transitions,
        hazard_geometry=exposure_result.hazard_geometry,
        exposure_features=exposure_result.exposure_features,
        analysis_mode=exposure_result.analysis_mode,
        data_source=exposure_result.data_source,
        attribution=exposure_result.attribution,
        note="Prototype Decision-Support Priority. Not an official government response classification.",
    )
