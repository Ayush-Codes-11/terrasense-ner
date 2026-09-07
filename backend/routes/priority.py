"""
priority.py — Prototype Decision-Support Priority routes for TerraSense NER.

Endpoints:
  GET /priority/{zone_id} — Computes 4-horizon priority outlook and transparent factor breakdown.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from models.schemas import (
    DataMeta,
    HorizonPrioritySchema,
    PriorityContributorSchema,
    ZonePriorityResponse,
)
from services.priority_engine import compute_zone_priority, HorizonPriorityResult

router = APIRouter(prefix="/priority")


def _horizon_to_schema(h: HorizonPriorityResult) -> HorizonPrioritySchema:
    return HorizonPrioritySchema(
        horizon=h.horizon,
        priority=h.priority,
        priority_score=round(h.priority_score, 4),
        landslide_risk_score=round(h.landslide_risk_score, 4),
        landslide_risk_category=h.landslide_risk_category,
        score_type=h.score_type,
        is_official_standard=h.is_official_standard,
        is_operationally_validated=h.is_operationally_validated,
        contributors=[
            PriorityContributorSchema(
                component=c.component,
                display_name=c.display_name,
                weight=c.weight,
                raw_value=round(c.raw_value, 4),
                normalized_input=round(c.normalized_input, 4),
                contribution=round(c.contribution, 4),
            )
            for c in h.contributors
        ],
    )


@router.get("/{zone_id}", response_model=ZonePriorityResponse)
def get_zone_priority_endpoint(zone_id: str):
    """
    Returns Prototype Decision-Support Priority for a zone across all 4 horizons
    (NOW, +24h, +48h, +72h) with exposure and risk contributors.
    """
    zid = zone_id.upper()
    try:
        res = compute_zone_priority(zid)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zid}' not found. Valid IDs are A01–E05.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Priority calculation error: {exc}")

    now_win = _horizon_to_schema(res.now)
    h24_win = _horizon_to_schema(res.h24)
    h48_win = _horizon_to_schema(res.h48)
    h72_win = _horizon_to_schema(res.h72)

    windows = {
        "now": now_win,
        "24h": h24_win,
        "48h": h48_win,
        "72h": h72_win,
    }

    forecast = {
        "24h": h24_win,
        "48h": h48_win,
        "72h": h72_win,
    }

    return ZonePriorityResponse(
        zone_id=zid,
        priority=res.now.priority,
        priority_score=round(res.now.priority_score, 4),
        priority_label="PROTOTYPE DECISION-SUPPORT — NOT OFFICIAL",
        windows=windows,
        now=now_win,
        forecast=forecast,
        explanation=res.explanation,
        horizon_transitions=res.horizon_transitions,
        exposure_summary=res.exposure_summary,
        hazard_geometry=res.hazard_geometry,
        exposure_features=res.exposure_features,
        analysis_mode=res.analysis_mode,
        data_meta=DataMeta(
            data_type=res.exposure_features,
            source=res.data_source,
            is_live=False,
            note=res.note,
        ),
    )
