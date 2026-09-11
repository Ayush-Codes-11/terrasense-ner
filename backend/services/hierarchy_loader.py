"""
Loads spatial hierarchy boundaries from GeoJSON data.
Handles missing data gracefully without silent mocks.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Any

from pydantic import ValidationError

from models.hierarchy import (
    CoverageLevel,
    District,
    HierarchyStatus,
    Region,
    RiskModelStatus,
    State,
)

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DEFAULT_HIERARCHY_DIR = _REPO_ROOT / "data" / "geodata" / "ner"

class HierarchyDataError(Exception):
    """Raised when the hierarchy data is malformed or invalid."""
    pass


class HierarchyLoader:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or _DEFAULT_HIERARCHY_DIR

        self.available: bool = False
        self.status: HierarchyStatus = HierarchyStatus.BOUNDARY_DATA_UNAVAILABLE

        self.regions: Dict[str, Region] = {}
        self.states: Dict[str, State] = {}
        self.districts: Dict[str, District] = {}

        self.state_features: Dict[str, dict] = {}
        self.district_features: Dict[str, dict] = {}

        self._pilot_district_id: Optional[str] = None

        self._load()

    def _load(self):
        meta_path = self.data_dir / "metadata.json"
        states_path = self.data_dir / "states.geojson"
        districts_path = self.data_dir / "districts.geojson"

        meta_exists = meta_path.exists()
        states_exists = states_path.exists()
        districts_exists = districts_path.exists()

        if not meta_exists and not states_exists and not districts_exists:
            self.status = HierarchyStatus.BOUNDARY_DATA_UNAVAILABLE
            self.available = False
            return

        if not (meta_exists and states_exists and districts_exists):
            self.status = HierarchyStatus.BOUNDARY_DATA_INVALID
            self.available = False
            raise HierarchyDataError("Partial hierarchy dataset found. All three files must be present.")

        try:
            self._parse_metadata(meta_path)
            self._parse_states(states_path)
            self._parse_districts(districts_path)

            # Post-validate pilot_district_id
            if self._pilot_district_id and self._pilot_district_id not in self.districts:
                raise HierarchyDataError(f"pilot_district_id '{self._pilot_district_id}' is not a loaded district.")

            self.status = HierarchyStatus.READY
            self.available = True
        except Exception as e:
            self.status = HierarchyStatus.BOUNDARY_DATA_INVALID
            self.available = False
            if isinstance(e, HierarchyDataError):
                raise
            raise HierarchyDataError(f"Malformed hierarchy data: {str(e)}")

    def _parse_metadata(self, meta_path: Path):
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._pilot_district_id = data.get("pilot_district_id")

        for r_data in data.get("regions", []):
            try:
                region = Region(**r_data)
            except ValidationError as e:
                raise HierarchyDataError(f"Invalid region data: {e}")
            if region.region_id in self.regions:
                raise HierarchyDataError(f"Duplicate region ID: {region.region_id}")
            self.regions[region.region_id] = region

    def _parse_states(self, states_path: Path):
        with open(states_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for feature in data.get("features", []):
            props = feature.get("properties", {})
            if "state_id" not in props:
                raise HierarchyDataError("State feature missing state_id")

            state_id = props["state_id"]
            if state_id in self.states:
                raise HierarchyDataError(f"Duplicate state ID: {state_id}")

            region_id = props.get("region_id")
            if region_id not in self.regions:
                raise HierarchyDataError(f"State {state_id} references nonexistent region {region_id}")

            geom = feature.get("geometry")
            if not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
                raise HierarchyDataError(f"State {state_id} has invalid or missing geometry.")

            try:
                state = State(
                    state_id=state_id,
                    state_name=props.get("state_name", ""),
                    region_id=region_id
                )
            except ValidationError as e:
                raise HierarchyDataError(f"Invalid state data: {e}")

            self.states[state_id] = state
            self.state_features[state_id] = feature

    def _parse_districts(self, districts_path: Path):
        with open(districts_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for feature in data.get("features", []):
            props = feature.get("properties", {})
            if "district_id" not in props:
                raise HierarchyDataError("District feature missing district_id")

            district_id = props["district_id"]
            if district_id in self.districts:
                raise HierarchyDataError(f"Duplicate district ID: {district_id}")

            state_id = props.get("state_id")
            if state_id not in self.states:
                raise HierarchyDataError(f"District {district_id} references nonexistent state {state_id}")

            geom = feature.get("geometry")
            if not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
                raise HierarchyDataError(f"District {district_id} has invalid or missing geometry.")

            district_name = props.get("district_name", "")

            # Default to boundary only
            coverage = CoverageLevel.DISTRICT_BOUNDARY_ONLY
            risk_status = RiskModelStatus.NOT_IMPLEMENTED

            # Check explicit pilot district assignment
            if self._pilot_district_id == district_id:
                coverage = CoverageLevel.DETAILED_PILOT
                risk_status = RiskModelStatus.STATIC_ML_VALIDATION_PENDING

            try:
                district = District(
                    district_id=district_id,
                    district_name=district_name,
                    state_id=state_id,
                    lgd_code=props.get("lgd_code"),
                    source_feature_id=props.get("source_feature_id"),
                    coverage_level=coverage,
                    risk_model_status=risk_status
                )
            except ValidationError as e:
                raise HierarchyDataError(f"Invalid district data: {e}")

            self.districts[district_id] = district
            self.district_features[district_id] = feature
