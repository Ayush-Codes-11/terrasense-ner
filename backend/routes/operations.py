"""Phase 7-10 operational readiness and verification endpoints.

These endpoints describe what is actually configured in this checkout. They
never turn an unavailable Kafka broker, IoT feed, or live API into a fake
"online" status.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from services.forecast_loader import get_forecast_provenance_status
from services.gpm_loader import get_gpm_provenance_status
from services.real_risk_fusion import get_real_fusion_status
from services.soil_loader import get_soil_provenance_status
from services.terrain_loader import get_terrain_provenance_status

router = APIRouter(prefix="/operations", tags=["operations"])


def _parity_check() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    pairs = [
        (root / "data" / "geodata" / "ner" / "states.geojson",
         root / "backend" / "data" / "geodata" / "ner" / "states.geojson"),
        (root / "data" / "geodata" / "ner" / "districts.geojson",
         root / "backend" / "data" / "geodata" / "ner" / "districts.geojson"),
    ]
    checks = []
    for canonical, mirror in pairs:
        if not canonical.exists() or not mirror.exists():
            checks.append({"file": canonical.name, "identical": False, "reason": "missing"})
            continue
        checks.append({
            "file": canonical.name,
            "identical": hashlib.sha256(canonical.read_bytes()).digest()
            == hashlib.sha256(mirror.read_bytes()).digest(),
        })
    if all(c["identical"] for c in checks):
        status = "PASS"
    elif any(c.get("reason") == "missing" for c in checks):
        status = "UNAVAILABLE"
    else:
        status = "FAIL"
    return {
        "status": status,
        "checks": checks,
    }


@router.get("/status")
def operations_status() -> dict[str, Any]:
    fusion = get_real_fusion_status()
    return {
        "connectivity": {
            "backend_api": "ONLINE",
            "kafka": "NOT_CONFIGURED",
            "iot_sensor_gateway": "NOT_CONFIGURED",
            "live_remote_sensing": "NOT_CONFIGURED",
            "offline_field_reports": "AVAILABLE",
        },
        "data_sources": {
            "terrain": get_terrain_provenance_status(),
            "observed_rainfall": get_gpm_provenance_status(),
            "soil_wetness": get_soil_provenance_status(),
            "forecast": get_forecast_provenance_status(),
            "ground_truth": fusion["sources"]["landslide_inventory"],
            "gis": {"status": "REAL_SNAPSHOT", "source": "OpenStreetMap"},
        },
        "model_readiness": {
            "static_susceptibility": fusion["static_model_status"],
            "dynamic_trigger": fusion["dynamic_model_status"],
            "calibrated_probability": False,
        },
        "verification": _parity_check(),
        "offline_mode": {
            "field_reports": "INDEXED_DB_QUEUE",
            "sync_policy": "RETRY_WHEN_ONLINE",
            "photo_validation": "NOT_CONFIGURED",
        },
    }
