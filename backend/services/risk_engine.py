"""
risk_engine.py — Pluggable risk-scoring adapter service for TerraSense NER backend.

══════════════════════════════════════════════════════════════════════
Decouples backend API routes from specific model implementations.
Phase 4: Uses ml.prototype_scorer (RISK_MODEL=prototype)
Phase 7: slope and elevation sourced from Copernicus GLO-30 REAL_DEM.
Future: Can seamlessly switch to XGBoost (RISK_MODEL=xgboost) without
        changing API routes or frontend contracts.
══════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure repository root and backend directory are on sys.path so ml module can be imported
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
for _p in (str(_REPO_ROOT), str(_BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ml.prototype_scorer import score_zone as _ml_score_zone, RiskResult, Contributor

# Selected risk model adapter (defaults to 'prototype')
RISK_MODEL = os.getenv("RISK_MODEL", "prototype").lower()


def compute_zone_risk(zone_props: Dict[str, Any]) -> RiskResult:
    """
    Computes risk score and component contributions for a zone using
    raw physical features.

    Phase 7: slope and elevation are sourced from the real Copernicus GLO-30
    DEM via terrain_loader. GeoJSON props are used only as fallback if terrain
    data is not yet available for the zone.

    IMPORTANT:
    Never uses precomputed 'risk_score' or 'risk_category' from GeoJSON.
    Extracts only:
      - slope_deg      — from terrain_loader (REAL_DEM) or GeoJSON fallback
      - elevation_m    — from terrain_loader (REAL_DEM) or GeoJSON fallback
      - rain_24h       — SAMPLE_MOCK
      - rain_3d        — SAMPLE_MOCK
      - soil_wetness   — SAMPLE_MOCK
      - rain_7d        — SAMPLE_MOCK (optional)
    """
    if RISK_MODEL == "prototype":
        from backend.services.terrain_loader import get_zone_terrain

        zone_id = str(zone_props.get("zone_id", "")).upper()
        terrain = get_zone_terrain(zone_id) if zone_id else None

        # ── Terrain features: prefer REAL_DEM, fall back to GeoJSON props ──
        if terrain:
            slope = float(terrain["mean_slope_deg"])
            elevation = float(terrain["mean_elevation_m"])
            slope_provenance = "REAL_DEM"
            elev_provenance = "REAL_DEM"
        else:
            slope = float(zone_props.get("slope", 0.0))
            elevation = float(zone_props.get("elevation", 0.0)) if "elevation" in zone_props else None
            slope_provenance = "SAMPLE_MOCK"
            elev_provenance = "SAMPLE_MOCK"

        # ── Rainfall / soil: always SAMPLE_MOCK in Phase 7 ──
        rain_24h = float(zone_props.get("rain_24h", 0.0))
        rain_3d = float(zone_props.get("rain_3d", 0.0))
        sw_val = zone_props.get("soil_wetness_index") if "soil_wetness_index" in zone_props else zone_props.get("soil_moisture")
        soil_wetness = float(sw_val) if sw_val is not None else 0.0
        rain_7d = float(zone_props.get("rain_7d", 0.0)) if "rain_7d" in zone_props else None

        result = _ml_score_zone(
            slope_deg=slope,
            rain_24h_mm=rain_24h,
            rain_3d_mm=rain_3d,
            soil_wetness_index=soil_wetness,
            rain_7d_mm=rain_7d,
            elevation_m=elevation,
        )

        # Attach feature provenance so routes can expose it
        result.feature_provenance = {
            "slope": slope_provenance,
            "elevation": elev_provenance,
            "rainfall": "SAMPLE_MOCK",
            "soil_wetness": "SAMPLE_MOCK",
        }
        result.used_slope_deg = slope
        result.used_elevation_m = elevation

        return result
    else:
        raise NotImplementedError(
            f"Risk model '{RISK_MODEL}' is not implemented yet. "
            "Supported models: ['prototype']."
        )
