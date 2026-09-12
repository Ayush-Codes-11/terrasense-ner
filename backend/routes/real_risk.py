"""Real-data evidence and fusion endpoints for Phases 4-6."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services.real_risk_fusion import get_real_fusion_status, get_zone_real_fusion

router = APIRouter(prefix="/risk/real", tags=["real-risk"])


@router.get("/status")
def real_risk_status():
    return get_real_fusion_status()


@router.get("/{zone_id}")
def real_risk_for_zone(zone_id: str):
    evidence = get_zone_real_fusion(zone_id)
    if evidence is None:
        raise HTTPException(
            status_code=404,
            detail=f"Real-data evidence is unavailable for zone {zone_id.upper()}",
        )
    return evidence
