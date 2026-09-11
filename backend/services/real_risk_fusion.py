"""Real-data evidence and transparent fusion for the Aizawl pilot.

This module deliberately does not claim calibrated probability or trained ML.
The public GSI inventory has no event timestamps, so dynamic trigger linkage
cannot be validated. It combines real source observations into an auditable
decision-support index and reports provenance for every component.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from shapely.geometry import Point, shape

from services.forecast_loader import get_forecast_provenance_status, get_zone_forecast
from services.gpm_loader import get_gpm_provenance_status, get_zone_gpm_observed
from services.gsi_inventory import get_all_mizoram_records
from services.soil_loader import get_soil_provenance_status, get_zone_soil_wetness
from services.terrain_loader import get_terrain_provenance_status, get_zone_terrain


def _load_grid() -> list[dict[str, Any]]:
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    path = root / "data" / "sample" / "grid-risk.geojson"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)["features"]


def _record_point(record: dict[str, Any]) -> Point | None:
    attributes = record.get("attributes", {})
    geometry = record.get("geometry", {})
    lat = attributes.get("latitude") or attributes.get("u_lat") or geometry.get("y")
    lon = attributes.get("longitude") or attributes.get("u_long") or geometry.get("x")
    try:
        return Point(float(lon), float(lat))
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=1)
def _gsi_counts_by_zone() -> dict[str, int]:
    counts = {feature["properties"]["zone_id"]: 0 for feature in _load_grid()}
    zone_shapes = [
        (feature["properties"]["zone_id"], shape(feature["geometry"]))
        for feature in _load_grid()
    ]
    for record in get_all_mizoram_records():
        point = _record_point(record)
        if point is None:
            continue
        for zone_id, polygon in zone_shapes:
            if polygon.covers(point):
                counts[zone_id] += 1
                break
    return counts


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


def _real_or_missing(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_real_fusion_status() -> dict[str, Any]:
    return {
        "static_model_status": "NOT_TRAINED",
        "dynamic_model_status": "NOT_VALIDATED",
        "score_semantics": "transparent_relative_decision_support_index",
        "is_probability": False,
        "is_calibrated": False,
        "sources": {
            "terrain": get_terrain_provenance_status(),
            "observed_rainfall": get_gpm_provenance_status(),
            "soil_wetness": get_soil_provenance_status(),
            "forecast": get_forecast_provenance_status(),
            "landslide_inventory": {
                "source": "GSI BhooSanket Landslide_Public",
                "records": len(get_all_mizoram_records()),
                "date_linked_events": 0,
                "status": "REAL_SPATIAL_INVENTORY_NO_EVENT_DATES",
            },
        },
    }


def get_zone_real_fusion(zone_id: str) -> dict[str, Any] | None:
    zid = zone_id.upper()
    terrain = get_zone_terrain(zid)
    gpm = get_zone_gpm_observed(zid)
    forecast = get_zone_forecast(zid)
    if terrain is None or gpm is None:
        return None

    slope = _real_or_missing(terrain.get("mean_slope_deg")) or 0.0
    elevation_range = _real_or_missing(terrain.get("elevation_range_m")) or 0.0
    observed_24h = _real_or_missing(gpm.get("recent_24h_mm")) or 0.0
    observed_3d = _real_or_missing(gpm.get("antecedent_3d_mm")) or 0.0
    soil = get_zone_soil_wetness(zid)
    forecast_24h = _real_or_missing(
        (forecast or {}).get("forecast_interval_mm", {}).get("0_24h")
    ) or 0.0
    inventory_count = _gsi_counts_by_zone().get(zid, 0)

    # Transparent, non-calibrated indices. These are not probabilities.
    terrain_index = _bounded((slope / 40.0) * 0.75 + (elevation_range / 1000.0) * 0.25)
    inventory_index = _bounded(inventory_count / 10.0)
    static_index = _bounded(terrain_index * 0.7 + inventory_index * 0.3)
    trigger_index = _bounded(
        (observed_24h / 70.0) * 0.35
        + (observed_3d / 150.0) * 0.35
        + soil * 0.2
        + (forecast_24h / 70.0) * 0.1
    )
    fusion_index = _bounded(static_index * 0.6 + trigger_index * 0.4)

    return {
        "zone_id": zid,
        "static_susceptibility": {
            "score": round(static_index, 4),
            "model_status": "TRANSPARENT_HEURISTIC_NOT_ML",
            "terrain_index": round(terrain_index, 4),
            "inventory_count": inventory_count,
            "inventory_index": round(inventory_index, 4),
        },
        "dynamic_trigger": {
            "score": round(trigger_index, 4),
            "model_status": "NOT_VALIDATED_NO_EVENT_DATES",
            "observed_24h_mm": observed_24h,
            "observed_3d_mm": observed_3d,
            "forecast_24h_mm": forecast_24h,
            "soil_wetness": soil,
        },
        "fusion": {
            "score": round(fusion_index, 4),
            "score_type": "transparent_relative_decision_support_index",
            "is_probability": False,
            "is_calibrated": False,
            "weights": {"static_susceptibility": 0.6, "dynamic_trigger": 0.4},
        },
        "provenance": {
            "terrain": "REAL_DEM",
            "observed_rainfall": gpm.get("data_type", "REAL_GPM"),
            "soil_wetness": get_soil_provenance_status().get("status"),
            "forecast": (forecast or {}).get("data_type", "REAL_FORECAST"),
            "landslide_inventory": "REAL_GSI_SPATIAL_INVENTORY",
        },
    }
