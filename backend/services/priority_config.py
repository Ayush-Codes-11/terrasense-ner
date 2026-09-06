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

# Whitelist sets for highway classes
MOTORABLE_HIGHWAY_CLASSES = {
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "residential",
    "unclassified",
    "service",
    "living_street",
}
TRACK_HIGHWAY_CLASSES = {"track"}
EXCLUDED_HIGHWAY_CLASSES = {
    "steps",
    "pedestrian",
    "footway",
    "path",
    "cycleway",
    "corridor",
    "construction",
    "proposed",
}

# Whitelist sets for critical facilities
FACILITY_WHITELIST_AMENITIES = {"hospital", "clinic", "police", "fire_station"}
FACILITY_WHITELIST_HEALTHCARE = {"hospital", "clinic"}

# Prototype component weights for Phase 6 (sum to 1.0)
# Documented as prototype heuristic weights selected based on current data reliability,
# NOT operational emergency-management weights.
# Note: Mapped communities/localities are retained as an exposure context metric only
# and not used in the priority formula due to sparse mapping across the pilot area.
WEIGHT_LANDSLIDE_RISK: float = 0.65
WEIGHT_ROAD_EXPOSURE: float = 0.20
WEIGHT_CRITICAL_FACILITY_EXPOSURE: float = 0.15
WEIGHT_SETTLEMENT_EXPOSURE: float = 0.0

# Prototype relative-normalization references derived from pilot exposure distribution (~P90).
# Explicitly dataset-relative prototype normalization parameters, NOT scientific or government emergency thresholds.
# - Motorable road km: P90 is ~38.22 km (was 3.0 km which saturated 88% of zones).
# - Critical facilities: P90 is 3.0 facilities (was 2.0 which saturated 20% of zones).
REF_ROAD_EXPOSURE_KM: float = 38.0
REF_SETTLEMENTS_COUNT: float = 1.0  # Context metric only
REF_CRITICAL_FACILITIES_COUNT: float = 3.0

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
