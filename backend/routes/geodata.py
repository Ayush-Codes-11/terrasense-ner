"""
geodata.py — OpenStreetMap geodata endpoints serving real or cached vector features.

Endpoints:
  GET /geodata/osm/status              — Current provenance status of OSM layers
  GET /geodata/osm/roads               — Road network GeoJSON FeatureCollection
  GET /geodata/osm/settlements         — Settlements/villages GeoJSON FeatureCollection
  GET /geodata/osm/critical-facilities — Hospitals/clinics/police GeoJSON FeatureCollection
"""
from __future__ import annotations

from fastapi import APIRouter
from backend.models.schemas import DataMeta, OSMStatusResponse
from backend.services.exposure_engine import (
    get_osm_provenance_status,
    load_exposure_layers,
)

router = APIRouter(prefix="/geodata/osm")


@router.get("/status", response_model=OSMStatusResponse)
def get_status():
    """Returns provenance status, retrieved_at timestamp, and feature counts of the OSM layer."""
    st = get_osm_provenance_status()
    return OSMStatusResponse(
        status=st["status"],
        is_real=st["is_real"],
        retrieved_at=st.get("retrieved_at"),
        source=st["source"],
        attribution=st["attribution"],
        feature_counts=st.get("feature_counts", {}),
        data_meta=DataMeta(
            data_type="REAL_OSM" if st["is_real"] else "SAMPLE_MOCK",
            source=st["source"],
            is_live=False,
            note=f"OSM layer state: {st['status']}. {st['attribution']}",
        ),
    )


@router.get("/roads")
def get_osm_roads():
    """Returns road network FeatureCollection with data_meta block."""
    roads_fc, _, _, data_type, src = load_exposure_layers()
    return {
        "type": "FeatureCollection",
        "features": roads_fc.get("features", []),
        "data_meta": {
            "data_type": data_type,
            "source": src,
            "is_live": False,
            "attribution": "© OpenStreetMap contributors" if data_type == "REAL_OSM" else "Sample fallback",
        },
    }


@router.get("/settlements")
def get_osm_settlements():
    """Returns settlements FeatureCollection with data_meta block."""
    _, settlements_fc, _, data_type, src = load_exposure_layers()
    return {
        "type": "FeatureCollection",
        "features": settlements_fc.get("features", []),
        "data_meta": {
            "data_type": data_type,
            "source": src,
            "is_live": False,
            "attribution": "© OpenStreetMap contributors" if data_type == "REAL_OSM" else "Sample fallback",
        },
    }


@router.get("/critical-facilities")
def get_osm_critical_facilities():
    """Returns critical facilities FeatureCollection with data_meta block."""
    _, _, facilities_fc, data_type, src = load_exposure_layers()
    return {
        "type": "FeatureCollection",
        "features": facilities_fc.get("features", []),
        "data_meta": {
            "data_type": data_type,
            "source": src,
            "is_live": False,
            "attribution": "© OpenStreetMap contributors" if data_type == "REAL_OSM" else "Sample fallback",
        },
    }
