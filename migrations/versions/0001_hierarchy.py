"""Phase 3A hierarchy persistence; independent of runtime model imports."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry

revision = "0001_hierarchy"
down_revision = None
branch_labels = None
depends_on = None


def geometry_column():
    return sa.Column("geometry", Geometry("MULTIPOLYGON", srid=4326, spatial_index=False),
                     nullable=False)


def geometry_check(table):
    return sa.CheckConstraint("ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry)",
                              name=f"ck_{table}_geometry_valid")


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public")
    op.create_table(
        "regions",
        sa.Column("region_id", sa.Text(), primary_key=True),
        sa.Column("region_name", sa.Text(), nullable=False),
        sa.Column("source_metadata", JSONB(), nullable=False),
    )
    op.create_table(
        "states",
        sa.Column("state_id", sa.Text(), primary_key=True),
        sa.Column("state_name", sa.Text(), nullable=False),
        sa.Column("region_id", sa.Text(), sa.ForeignKey("regions.region_id"), nullable=False),
        sa.Column("source_metadata", JSONB(), nullable=False),
        geometry_column(), geometry_check("states"),
    )
    op.create_table(
        "districts",
        sa.Column("district_id", sa.Text(), primary_key=True),
        sa.Column("district_name", sa.Text(), nullable=False),
        sa.Column("state_id", sa.Text(), sa.ForeignKey("states.state_id"), nullable=False),
        sa.Column("lgd_code", sa.Text(), nullable=True),
        sa.Column("source_feature_id", sa.Text(), nullable=True),
        sa.Column("coverage_level", sa.Text(), nullable=False),
        sa.Column("risk_model_status", sa.Text(), nullable=False),
        sa.Column("source_metadata", JSONB(), nullable=False),
        geometry_column(), geometry_check("districts"),
        sa.CheckConstraint(
            "(coverage_level = 'DISTRICT_BOUNDARY_ONLY' AND risk_model_status = 'NOT_IMPLEMENTED') "
            "OR (coverage_level = 'DETAILED_PILOT' AND "
            "risk_model_status = 'STATIC_ML_VALIDATION_PENDING')",
            name="ck_districts_status_pair"),
    )
    op.create_table(
        "analysis_zones",
        sa.Column("zone_id", sa.Text(), primary_key=True),
        sa.Column("district_id", sa.Text(), sa.ForeignKey("districts.district_id"), nullable=False),
        sa.Column("zone_type", sa.Text(), nullable=False),
        geometry_column(), geometry_check("analysis_zones"),
        sa.CheckConstraint("zone_type = 'PROTOTYPE_ANALYSIS_GRID'", name="ck_analysis_zones_type"),
    )
    for table, parent in [("states", "region_id"), ("districts", "state_id"),
                          ("analysis_zones", "district_id")]:
        op.create_index(f"ix_{table}_{parent}", table, [parent])
        op.create_index(f"ix_{table}_geometry", table, ["geometry"], postgresql_using="gist")


def downgrade():
    for table in ("analysis_zones", "districts", "states", "regions"):
        op.drop_table(table)
    # PostGIS may be shared by other applications; leave the extension installed.
