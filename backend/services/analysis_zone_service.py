from __future__ import annotations
from typing import Optional

from models.hierarchy import CoverageLevel, AnalysisZoneMetadata, ZoneType
from services.hierarchy_loader import HierarchyLoader
from services.data_loader import get_all_zone_props

class AnalysisZoneService:
    def __init__(self, hierarchy_loader: HierarchyLoader):
        self.hierarchy_loader = hierarchy_loader

    def get_district_zones(self, district_id: str) -> list[AnalysisZoneMetadata]:
        """Return the analysis zones for a given district. Only populated for pilot districts."""
        district = self.hierarchy_loader.districts.get(district_id)
        if not district:
            return []

        if district.coverage_level != CoverageLevel.DETAILED_PILOT:
            return []

        # Get zones from canonical prototype grid
        props_list = get_all_zone_props()
        zones = []
        for props in props_list:
            zid = props.get("zone_id")
            if zid:
                zones.append(AnalysisZoneMetadata(
                    zone_id=zid,
                    district_id=district_id,
                    zone_type=ZoneType.PROTOTYPE_ANALYSIS_GRID
                ))
        zones.sort(key=lambda z: z.zone_id)
        return zones

    def get_zone(self, zone_id: str) -> Optional[AnalysisZoneMetadata]:
        """Return metadata for a specific analysis zone."""
        # Find which district is the pilot
        pilot_district_id = None
        for d in self.hierarchy_loader.districts.values():
            if d.coverage_level == CoverageLevel.DETAILED_PILOT:
                pilot_district_id = d.district_id
                break

        if not pilot_district_id:
            return None

        props_list = get_all_zone_props()
        for props in props_list:
            if props.get("zone_id") == zone_id.upper():
                return AnalysisZoneMetadata(
                    zone_id=zone_id.upper(),
                    district_id=pilot_district_id,
                    zone_type=ZoneType.PROTOTYPE_ANALYSIS_GRID
                )
        return None
