"""Read-only, request-local snapshots. No session survives construction."""
import json
from functools import lru_cache

from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from db import models as tables
from db.session import create_db_engine, database_url, session_scope
from models.hierarchy import AnalysisZoneMetadata, CoverageLevel, District, HierarchyStatus, Region, State
from services.hierarchy_loader import HierarchyDataError
from services.hierarchy_repository import HierarchyUnavailableError


@lru_cache(maxsize=8)
def get_postgis_engine(url):
    # Only connection pools are cached. Runtime configuration changes need a restart.
    parsed = database_url(url)
    if "connect_timeout" not in parsed.query:
        parsed = parsed.update_query_dict({"connect_timeout": "5"})
    return create_db_engine(parsed)


class PostGISHierarchyReader:
    def __init__(self, engine, *, include_geometry=False):
        self.available = False
        self.status = HierarchyStatus.BOUNDARY_DATA_UNAVAILABLE
        self.regions = {}
        self.states = {}
        self.districts = {}
        self.zones = {}
        # Geometry is loaded only for explicit GeoJSON requests or parity checks.
        self.geometries = {}
        self.geometry_srids = {}
        try:
            with session_scope(engine) as session:
                session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
                for model, domain, destination, key in (
                    (tables.Region, Region, self.regions, "region_id"),
                    (tables.State, State, self.states, "state_id"),
                    (tables.District, District, self.districts, "district_id"),
                    (tables.AnalysisZone, AnalysisZoneMetadata, self.zones, "zone_id"),
                ):
                    # Select only the existing response fields, in stable primary-key order.
                    columns = [getattr(model, name) for name in domain.model_fields]
                    rows = session.execute(select(*columns).order_by(getattr(model, key))).mappings()
                    for row in rows:
                        destination[row[key]] = domain(**row)
                    if include_geometry and model is not tables.Region:
                        # Explicit precision avoids ST_AsGeoJSON's default 9-decimal reduction.
                        rows = session.execute(select(
                            getattr(model, key), func.ST_AsGeoJSON(model.geometry, 17, 0),
                            func.ST_SRID(model.geometry)).order_by(getattr(model, key)))
                        self.geometries[model.__tablename__] = {}
                        self.geometry_srids[model.__tablename__] = {}
                        for feature_id, geometry, srid in rows:
                            self.geometries[model.__tablename__][feature_id] = (
                                json.loads(geometry) if geometry is not None else None)
                            self.geometry_srids[model.__tablename__][feature_id] = srid
                self._validate_relations()
        except SQLAlchemyError:
            raise HierarchyUnavailableError("PostGIS hierarchy is unavailable.") from None
        except ValidationError:
            raise HierarchyDataError("PostGIS hierarchy data failed validation.") from None
        self.available = True
        self.status = HierarchyStatus.READY

    def _validate_relations(self):
        if not self.regions and not self.states and not self.districts and not self.zones:
            raise HierarchyUnavailableError("PostGIS hierarchy has not been imported.")
        if not self.regions or not self.states or not self.districts:
            raise HierarchyDataError("Partial PostGIS hierarchy dataset.")
        if any(s.region_id not in self.regions for s in self.states.values()):
            raise HierarchyDataError("Orphan PostGIS state.")
        if any(d.state_id not in self.states for d in self.districts.values()):
            raise HierarchyDataError("Orphan PostGIS district.")
        for zone in self.zones.values():
            district = self.districts.get(zone.district_id)
            if district is None or district.coverage_level != CoverageLevel.DETAILED_PILOT:
                raise HierarchyDataError("Invalid PostGIS zone binding.")

    def get_district_zones(self, district_id):
        district = self.districts.get(district_id)
        if district is None or district.coverage_level != CoverageLevel.DETAILED_PILOT:
            return []
        return sorted((z for z in self.zones.values() if z.district_id == district_id),
                      key=lambda zone: zone.zone_id)

    def get_zone(self, zone_id):
        return self.zones.get(zone_id.upper())

    def get_geometry(self, collection, feature_id):
        return self.geometries[collection][feature_id]
