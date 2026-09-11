"""Integration contract for the committed 2021 ADM2 prototype dataset.

The district count does not imply current administrative-list reconciliation.
"""

from models.hierarchy import CoverageLevel, HierarchyStatus, RiskModelStatus, ZoneType
from services.analysis_zone_service import AnalysisZoneService
from services.hierarchy_loader import HierarchyLoader


def test_production_ner_hierarchy_and_pilot_zones():
    loader = HierarchyLoader()
    assert loader.status == HierarchyStatus.READY
    assert loader.available is True
    assert set(loader.regions) == {"NER"}
    assert len(loader.states) == 8
    assert len(loader.districts) == 119
    assert set(loader.states) == {
        "IN-AR", "IN-AS", "IN-MN", "IN-ML", "IN-MZ", "IN-NL", "IN-SK", "IN-TR"
    }
    assert len(loader.state_features) == 8
    assert all(
        feature["properties"]["region_id"] == "NER"
        for feature in loader.state_features.values()
    )

    pilot_id = "IND-ADM2-76128533B34203923268864"
    pilot = loader.districts[pilot_id]
    assert pilot.district_name == "Aizawl"
    assert pilot.state_id == "IN-MZ"
    assert pilot.lgd_code is None
    assert pilot.coverage_level == CoverageLevel.DETAILED_PILOT
    assert pilot.risk_model_status == RiskModelStatus.STATIC_ML_VALIDATION_PENDING
    for district_id, district in loader.districts.items():
        if district_id != pilot_id:
            assert district.coverage_level == CoverageLevel.DISTRICT_BOUNDARY_ONLY
            assert district.risk_model_status == RiskModelStatus.NOT_IMPLEMENTED

    zones = AnalysisZoneService(loader).get_district_zones(pilot_id)
    assert len(zones) == 25
    zone_ids = {zone.zone_id for zone in zones}
    assert len(zone_ids) == 25
    assert "C03" in zone_ids
    assert all(zone.district_id == pilot_id for zone in zones)
    assert all(zone.zone_type == ZoneType.PROTOTYPE_ANALYSIS_GRID for zone in zones)
