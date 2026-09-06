"""
risk_engine.py — Pluggable risk-scoring adapter service for TerraSense NER backend.

══════════════════════════════════════════════════════════════════════
Decouples backend API routes from specific model implementations.
Phase 4: Uses ml.prototype_scorer (RISK_MODEL=prototype)
Future: Can seamlessly switch to XGBoost (RISK_MODEL=xgboost) without
        changing API routes or frontend contracts.
══════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure repository root is on sys.path so ml module can be imported
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ml.prototype_scorer import score_zone as _ml_score_zone, RiskResult, Contributor

# Selected risk model adapter (defaults to 'prototype')
RISK_MODEL = os.getenv("RISK_MODEL", "prototype").lower()


def compute_zone_risk(zone_props: Dict[str, Any]) -> RiskResult:
    """
    Computes risk score and component contributions for a zone using
    raw physical features.
    
    IMPORTANT:
    Never uses precomputed 'risk_score' or 'risk_category' from GeoJSON.
    Extracts only:
      - slope (slope_deg)
      - rain_24h (rain_24h_mm)
      - rain_3d (rain_3d_mm)
      - soil_moisture (soil_moisture index)
      - rain_7d (rain_7d_mm)
      - elevation (elevation_m, pass-through metadata only)
    """
    if RISK_MODEL == "prototype":
        # Extract features from sample properties (clarified as soil_wetness_index)
        slope = float(zone_props.get("slope", 0.0))
        rain_24h = float(zone_props.get("rain_24h", 0.0))
        rain_3d = float(zone_props.get("rain_3d", 0.0))
        sw_val = zone_props.get("soil_wetness_index") if "soil_wetness_index" in zone_props else zone_props.get("soil_moisture")
        soil_wetness = float(sw_val) if sw_val is not None else 0.0
        rain_7d = float(zone_props.get("rain_7d", 0.0)) if "rain_7d" in zone_props else None
        elevation = float(zone_props.get("elevation", 0.0)) if "elevation" in zone_props else None

        return _ml_score_zone(
            slope_deg=slope,
            rain_24h_mm=rain_24h,
            rain_3d_mm=rain_3d,
            soil_wetness_index=soil_wetness,
            rain_7d_mm=rain_7d,
            elevation_m=elevation,
        )
    else:
        raise NotImplementedError(
            f"Risk model '{RISK_MODEL}' is not implemented yet. "
            "Supported models: ['prototype']."
        )
