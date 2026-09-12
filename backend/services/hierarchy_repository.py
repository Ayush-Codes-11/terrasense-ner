"""The small read surface consumed by hierarchy routes; no database imports."""
from typing import Mapping, Protocol

from models.hierarchy import AnalysisZoneMetadata, District, HierarchyStatus, Region, State
from services.analysis_zone_service import AnalysisZoneService
from services.hierarchy_loader import HierarchyLoader


class HierarchyReadRepository(Protocol):
    available: bool
    status: HierarchyStatus
    regions: Mapping[str, Region]
    states: Mapping[str, State]
    districts: Mapping[str, District]

    def get_district_zones(self, district_id: str) -> list[AnalysisZoneMetadata]: ...
    def get_geometry(self, collection: str, feature_id: str) -> dict: ...
    def get_zone(self, zone_id: str) -> AnalysisZoneMetadata | None: ...


class HierarchyUnavailableError(Exception):
    """Operational database failure; details must not reach API responses."""


class HierarchyConfigurationError(ValueError):
    pass


class FileHierarchyRepository:
    """Adapt the canonical loader and zone service without rewriting either."""
    def __init__(self, loader: HierarchyLoader):
        self._loader = loader
        self.available = loader.available
        self.status = loader.status
        self.regions = loader.regions
        self.states = loader.states
        self.districts = loader.districts
        self._zones = AnalysisZoneService(loader)

    def get_district_zones(self, district_id):
        return self._zones.get_district_zones(district_id)

    def get_zone(self, zone_id):
        return self._zones.get_zone(zone_id)

    def get_geometry(self, collection, feature_id):
        features = self._loader.state_features if collection == "states" else self._loader.district_features
        return features[feature_id]["geometry"]
