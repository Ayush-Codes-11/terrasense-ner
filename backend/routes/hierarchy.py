"""
Read-only hierarchy API for regions, states, and districts.
"""
from fastapi import APIRouter, Depends, HTTPException
from functools import lru_cache

from models.hierarchy import (
    HierarchyStatus,
    Region, State, District,
    RegionListResponse, StateListResponse, DistrictListResponse
)
from services.hierarchy_loader import HierarchyLoader, HierarchyDataError

router = APIRouter(tags=["Hierarchy"])

@lru_cache()
def get_hierarchy_loader() -> HierarchyLoader:
    # Production instantiation; tests will override this dependency.
    # The loader is cached once per backend process. If administrative
    # files are added/replaced, the backend requires a restart.
    try:
        return HierarchyLoader()
    except HierarchyDataError:
        # Create an empty dummy loader that reports INVALID, so FastAPI doesn't crash
        loader = HierarchyLoader.__new__(HierarchyLoader)
        loader.available = False
        loader.status = HierarchyStatus.BOUNDARY_DATA_INVALID
        return loader

def ensure_hierarchy_ready(loader: HierarchyLoader = Depends(get_hierarchy_loader)) -> HierarchyLoader:
    if loader.status == HierarchyStatus.BOUNDARY_DATA_UNAVAILABLE:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "BOUNDARY_DATA_UNAVAILABLE",
                "message": "NER administrative boundary dataset is not available."
            }
        )
    if loader.status == HierarchyStatus.BOUNDARY_DATA_INVALID:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "BOUNDARY_DATA_INVALID",
                "message": "NER administrative boundary dataset failed validation."
            }
        )
    return loader

@router.get("/regions", response_model=RegionListResponse)
def get_regions(loader: HierarchyLoader = Depends(ensure_hierarchy_ready)):
    regions = sorted(loader.regions.values(), key=lambda r: r.region_name)
    return RegionListResponse(count=len(regions), items=regions)

@router.get("/regions/{region_id}/states", response_model=StateListResponse)
def get_region_states(region_id: str, loader: HierarchyLoader = Depends(ensure_hierarchy_ready)):
    if region_id not in loader.regions:
        raise HTTPException(status_code=404, detail="Region not found")
    states = [s for s in loader.states.values() if s.region_id == region_id]
    states.sort(key=lambda s: s.state_name)
    return StateListResponse(count=len(states), items=states)

@router.get("/states", response_model=StateListResponse)
def get_states(loader: HierarchyLoader = Depends(ensure_hierarchy_ready)):
    states = sorted(loader.states.values(), key=lambda s: s.state_name)
    return StateListResponse(count=len(states), items=states)

@router.get("/states/{state_id}", response_model=State)
def get_state(state_id: str, loader: HierarchyLoader = Depends(ensure_hierarchy_ready)):
    if state_id not in loader.states:
        raise HTTPException(status_code=404, detail="State not found")
    return loader.states[state_id]

@router.get("/states/{state_id}/districts", response_model=DistrictListResponse)
def get_state_districts(state_id: str, loader: HierarchyLoader = Depends(ensure_hierarchy_ready)):
    if state_id not in loader.states:
        raise HTTPException(status_code=404, detail="State not found")
    districts = [d for d in loader.districts.values() if d.state_id == state_id]
    districts.sort(key=lambda d: d.district_name)
    return DistrictListResponse(count=len(districts), items=districts)

@router.get("/districts/{district_id}", response_model=District)
def get_district(district_id: str, loader: HierarchyLoader = Depends(ensure_hierarchy_ready)):
    if district_id not in loader.districts:
        raise HTTPException(status_code=404, detail="District not found")
    return loader.districts[district_id]
