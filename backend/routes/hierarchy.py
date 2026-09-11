"""Read-only Northeast Region -> state -> district hierarchy endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services.ner_hierarchy import (
    get_district,
    get_districts_for_state,
    get_state,
    load_districts,
    load_region,
    load_states,
)

router = APIRouter(prefix="/hierarchy", tags=["hierarchy"])


@router.get("/region")
def get_region():
    """Return the dissolved Northeast Region boundary."""
    return load_region()


@router.get("/states")
def get_states():
    """Return the eight Northeast state boundaries."""
    return load_states()


@router.get("/states/{state_id}")
def get_state_by_id(state_id: str):
    """Return one state boundary and its district count."""
    feature = get_state(state_id)
    if feature is None:
        raise HTTPException(status_code=404, detail=f"State not found: {state_id}")
    state = dict(feature)
    state["district_count"] = len(get_districts_for_state(state_id))
    return state


@router.get("/states/{state_id}/districts")
def get_state_districts(state_id: str):
    """Return all districts belonging to one Northeast state."""
    if get_state(state_id) is None:
        raise HTTPException(status_code=404, detail=f"State not found: {state_id}")
    return {
        "type": "FeatureCollection",
        "features": get_districts_for_state(state_id),
    }


@router.get("/districts")
def get_districts():
    """Return all 119 Northeast district boundaries."""
    return load_districts()


@router.get("/districts/{district_id}")
def get_district_by_id(district_id: str):
    """Return one district boundary."""
    feature = get_district(district_id)
    if feature is None:
        raise HTTPException(status_code=404, detail=f"District not found: {district_id}")
    return feature

