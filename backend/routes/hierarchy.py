"""
Read-only hierarchy API for regions, states, and districts.
"""
from fastapi import APIRouter, Depends, HTTPException

from models.hierarchy import (
    HierarchyStatus,
    Region, State, District,
    RegionListResponse, StateListResponse, DistrictListResponse,
    DistrictZonesResponse, AnalysisZoneMetadata, CoverageLevel
)
from services.hierarchy_loader import HierarchyLoader, HierarchyDataError
from services.hierarchy_repository import (
    FileHierarchyRepository, HierarchyReadRepository,
    HierarchyConfigurationError, HierarchyUnavailableError,
)
from services.hierarchy_source import select_hierarchy_reader

router = APIRouter(tags=["Hierarchy"])

def get_hierarchy_loader():
    # Keep this dependency name so existing fixture overrides remain compatible.
    try:
        return select_hierarchy_reader()
    except HierarchyConfigurationError as error:
        raise HTTPException(status_code=503, detail={
            "status": "BOUNDARY_DATA_UNAVAILABLE", "message": str(error)}) from None
    except HierarchyUnavailableError:
        raise HTTPException(status_code=503, detail={
            "status": "BOUNDARY_DATA_UNAVAILABLE",
            "message": "NER administrative boundary dataset is not available."}) from None
    except HierarchyDataError:
        raise HTTPException(status_code=503, detail={
            "status": "BOUNDARY_DATA_INVALID",
            "message": "NER administrative boundary dataset failed validation."}) from None

def ensure_hierarchy_ready(loader = Depends(get_hierarchy_loader)) -> HierarchyReadRepository:
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
    return FileHierarchyRepository(loader) if isinstance(loader, HierarchyLoader) else loader

@router.get("/regions", response_model=RegionListResponse)
def get_regions(loader: HierarchyReadRepository = Depends(ensure_hierarchy_ready)):
    regions = sorted(loader.regions.values(), key=lambda r: r.region_name)
    return RegionListResponse(count=len(regions), items=regions)

@router.get("/regions/{region_id}/states", response_model=StateListResponse)
def get_region_states(region_id: str, loader: HierarchyReadRepository = Depends(ensure_hierarchy_ready)):
    if region_id not in loader.regions:
        raise HTTPException(status_code=404, detail="Region not found")
    states = [s for s in loader.states.values() if s.region_id == region_id]
    states.sort(key=lambda s: s.state_name)
    return StateListResponse(count=len(states), items=states)

@router.get("/states", response_model=StateListResponse)
def get_states(loader: HierarchyReadRepository = Depends(ensure_hierarchy_ready)):
    states = sorted(loader.states.values(), key=lambda s: s.state_name)
    return StateListResponse(count=len(states), items=states)

@router.get("/states/{state_id}", response_model=State)
def get_state(state_id: str, loader: HierarchyReadRepository = Depends(ensure_hierarchy_ready)):
    if state_id not in loader.states:
        raise HTTPException(status_code=404, detail="State not found")
    return loader.states[state_id]

@router.get("/states/{state_id}/districts", response_model=DistrictListResponse)
def get_state_districts(state_id: str, loader: HierarchyReadRepository = Depends(ensure_hierarchy_ready)):
    if state_id not in loader.states:
        raise HTTPException(status_code=404, detail="State not found")
    districts = [d for d in loader.districts.values() if d.state_id == state_id]
    districts.sort(key=lambda d: d.district_name)
    return DistrictListResponse(count=len(districts), items=districts)

@router.get("/districts/{district_id}", response_model=District)
def get_district(district_id: str, loader: HierarchyReadRepository = Depends(ensure_hierarchy_ready)):
    if district_id not in loader.districts:
        raise HTTPException(status_code=404, detail="District not found")
    return loader.districts[district_id]


@router.get('/districts/{district_id}/zones', response_model=DistrictZonesResponse)
def get_district_zones(district_id: str, loader: HierarchyReadRepository = Depends(ensure_hierarchy_ready)):
    if district_id not in loader.districts:
        raise HTTPException(status_code=404, detail='District not found')
    zones = loader.get_district_zones(district_id)
    district = loader.districts[district_id]
    return DistrictZonesResponse(
        district_id=district.district_id,
        district_name=district.district_name,
        coverage_level=district.coverage_level,
        risk_model_status=district.risk_model_status,
        detailed_zone_model_available=(district.coverage_level == CoverageLevel.DETAILED_PILOT),
        count=len(zones),
        items=zones
    )

@router.get('/zones/{zone_id}', response_model=AnalysisZoneMetadata)
def get_zone(zone_id: str, loader: HierarchyReadRepository = Depends(ensure_hierarchy_ready)):
    zone = loader.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail='Zone not found')
    return zone
