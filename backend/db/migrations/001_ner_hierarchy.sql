-- TerraSense Phase 3 PostGIS foundation.
-- Apply with psql against a database that has PostGIS installed.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS terrasense;

CREATE TABLE IF NOT EXISTS terrasense.regions (
    region_id text PRIMARY KEY,
    region_name text NOT NULL,
    source text NOT NULL,
    source_version text NOT NULL,
    geometry geometry(MultiPolygon, 4326) NOT NULL,
    CONSTRAINT regions_geometry_valid CHECK (ST_IsValid(geometry))
);

CREATE TABLE IF NOT EXISTS terrasense.states (
    state_id text PRIMARY KEY,
    state_name text NOT NULL UNIQUE,
    region_id text NOT NULL REFERENCES terrasense.regions(region_id),
    source_feature_id text NOT NULL UNIQUE,
    source text NOT NULL,
    source_version text NOT NULL,
    geometry geometry(MultiPolygon, 4326) NOT NULL,
    CONSTRAINT states_geometry_valid CHECK (ST_IsValid(geometry))
);

CREATE TABLE IF NOT EXISTS terrasense.districts (
    district_id text PRIMARY KEY,
    district_name text NOT NULL,
    state_id text NOT NULL REFERENCES terrasense.states(state_id),
    lgd_code text,
    source_feature_id text NOT NULL UNIQUE,
    source text NOT NULL,
    source_version text NOT NULL,
    geometry geometry(MultiPolygon, 4326) NOT NULL,
    CONSTRAINT districts_geometry_valid CHECK (ST_IsValid(geometry)),
    CONSTRAINT districts_lgd_code_nonempty CHECK (
        lgd_code IS NULL OR length(trim(lgd_code)) > 0
    )
);

CREATE INDEX IF NOT EXISTS regions_geometry_gix
    ON terrasense.regions USING gist (geometry);
CREATE INDEX IF NOT EXISTS states_region_idx
    ON terrasense.states (region_id);
CREATE INDEX IF NOT EXISTS states_geometry_gix
    ON terrasense.states USING gist (geometry);
CREATE INDEX IF NOT EXISTS districts_state_idx
    ON terrasense.districts (state_id);
CREATE INDEX IF NOT EXISTS districts_lgd_code_idx
    ON terrasense.districts (lgd_code)
    WHERE lgd_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS districts_geometry_gix
    ON terrasense.districts USING gist (geometry);
