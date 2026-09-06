"""
priority_config.py — Weights, normalization references, and boundaries for
Prototype Decision-Support Priority scoring.

════════════════════════════════════════════════════════════════════════════════
CRITICAL ARCHITECTURAL DISCLAIMER:
- This is a PROTOTYPE DECISION-SUPPORT model for research and interface demonstration.
- It is NOT an official disaster-management priority standard.
- The normalization references (3.0 km roads, 3 settlements, 2 critical facilities)
  are HEURISTIC PROTOTYPE REFERENCE VALUES, NOT operationally validated
  warning/evacuation thresholds.
════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from typing import Dict, Tuple

# Component weights (sum to 1.0)
WEIGHT_LANDSLIDE_RISK: float = 0.60
WEIGHT_ROAD_EXPOSURE: float = 0.15
WEIGHT_SETTLEMENT_EXPOSURE: float = 0.15
WEIGHT_CRITICAL_FACILITY_EXPOSURE: float = 0.10

# Prototype normalization reference values (heuristic demo parameters)
REF_ROAD_EXPOSURE_KM: float = 3.0
REF_SETTLEMENTS_COUNT: float = 3.0
REF_CRITICAL_FACILITIES_COUNT: float = 2.0

# Priority category boundaries: [lower, upper) except VERY_HIGH which is [0.75, 1.0]
PRIORITY_BANDS: Dict[str, Tuple[float, float]] = {
    "LOW": (0.0, 0.25),
    "MODERATE": (0.25, 0.50),
    "HIGH": (0.50, 0.75),
    "VERY_HIGH": (0.75, 1.0001),
}


def get_priority_category(score: float) -> str:
    """Classifies a priority score [0.0, 1.0] into a prototype priority category."""
    clamped = max(0.0, min(1.0, float(score)))
    for cat, (low, high) in PRIORITY_BANDS.items():
        if low <= clamped < high or (cat == "VERY_HIGH" and clamped >= 0.75):
            return cat
    return "VERY_HIGH" if clamped >= 0.75 else "LOW"
