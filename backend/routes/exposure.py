"""
exposure.py — Exposure routes for TerraSense NER.

Endpoints:
  GET /exposure/{zone_id} — Computes road, settlement, and facility exposure for a zone.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from backend.models.schemas import (
    DataMeta,
    ExposedFacilitySchema,
    ExposedRoadSchema,
    ExposedSettlementSchema,
    ExposureSummarySchema,
    ZoneExposureResponse,
)
from backend.services.exposure_engine import compute_zone_exposure

router = APIRouter(prefix="/exposure")


@router.get("/{zone_id}", response_model=ZoneExposureResponse)
def get_zone_exposure_endpoint(zone_id: str):
    """
    Returns infrastructure exposure (roads, settlements, critical facilities)
    inside the specified hazard zone polygon.
    Roads are clipped to the zone polygon and measured geodesically.
    """
    zid = zone_id.upper()
    try:
        res = compute_zone_exposure(zid)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zid}' not found in pilot grid geometry.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Exposure calculation error: {exc}")

    summary = ExposureSummarySchema(
        roads_exposed=res.road_feature_count,
        roads_exposed_km=res.road_length_km,
        villages_exposed=res.settlements_exposed,
        hospitals_exposed=res.critical_facilities_exposed,
        roads_blocked=0,  # Never inferred; verified field reports only
    )

    roads = [
        ExposedRoadSchema(
            feature_id=r.feature_id,
            name=r.name,
            highway=r.highway,
            length_km=r.length_km,
            blockage_verified=r.blockage_verified,
            road_status=r.road_status,
        )
        for r in res.exposed_roads
    ]

    settlements = [
        ExposedSettlementSchema(
            feature_id=s.feature_id,
            name=s.name,
            place=s.place,
        )
        for s in res.exposed_settlements
    ]

    facilities = [
        ExposedFacilitySchema(
            feature_id=f.feature_id,
            name=f.name,
            category=f.category,
        )
        for f in res.exposed_facilities
    ]

    return ZoneExposureResponse(
        zone_id=zid,
        summary=summary,
        roads=roads,
        settlements=settlements,
        critical_facilities=facilities,
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
