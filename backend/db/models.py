"""Persistence models, separate from the existing Pydantic API models."""
from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import CheckConstraint, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


def spatial_constraints(table):
    return (
        CheckConstraint("ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry)",
                        name=f"ck_{table}_geometry_valid"),
        Index(f"ix_{table}_geometry", "geometry", postgresql_using="gist"),
    )


class Region(Base):
    __tablename__ = "regions"
    region_id: Mapped[str] = mapped_column(Text, primary_key=True)
    region_name: Mapped[str] = mapped_column(Text)
    source_metadata: Mapped[dict] = mapped_column(JSONB)


class State(Base):
    __tablename__ = "states"
    state_id: Mapped[str] = mapped_column(Text, primary_key=True)
    state_name: Mapped[str] = mapped_column(Text)
    region_id: Mapped[str] = mapped_column(ForeignKey("regions.region_id"), index=True)
    source_metadata: Mapped[dict] = mapped_column(JSONB)
    geometry: Mapped[WKBElement] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326, spatial_index=False))
    __table_args__ = spatial_constraints("states")


class District(Base):
    __tablename__ = "districts"
    district_id: Mapped[str] = mapped_column(Text, primary_key=True)
    district_name: Mapped[str] = mapped_column(Text)
    state_id: Mapped[str] = mapped_column(ForeignKey("states.state_id"), index=True)
    lgd_code: Mapped[str | None] = mapped_column(Text)
    source_feature_id: Mapped[str | None] = mapped_column(Text)
    coverage_level: Mapped[str] = mapped_column(Text)
    risk_model_status: Mapped[str] = mapped_column(Text)
    source_metadata: Mapped[dict] = mapped_column(JSONB)
    geometry: Mapped[WKBElement] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326, spatial_index=False))
    __table_args__ = (
        CheckConstraint(
            "(coverage_level = 'DISTRICT_BOUNDARY_ONLY' AND risk_model_status = 'NOT_IMPLEMENTED') "
            "OR (coverage_level = 'DETAILED_PILOT' AND "
            "risk_model_status = 'STATIC_ML_VALIDATION_PENDING')",
            name="ck_districts_status_pair"),
        *spatial_constraints("districts"),
    )


class AnalysisZone(Base):
    __tablename__ = "analysis_zones"
    zone_id: Mapped[str] = mapped_column(Text, primary_key=True)
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.district_id"), index=True)
    zone_type: Mapped[str] = mapped_column(Text)
    geometry: Mapped[WKBElement] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326, spatial_index=False))
    __table_args__ = (
        CheckConstraint("zone_type = 'PROTOTYPE_ANALYSIS_GRID'", name="ck_analysis_zones_type"),
        *spatial_constraints("analysis_zones"),
    )
