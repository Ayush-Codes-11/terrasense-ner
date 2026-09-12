# Phase 3 PostGIS foundation

This directory defines the persistence contract for the validated NER
hierarchy. It is intentionally additive: the current FastAPI prototype still
reads the checked-in GeoJSON files, and no database connection is required to
run existing tests or the demo.

## Schema

Apply [`migrations/001_ner_hierarchy.sql`](./migrations/001_ner_hierarchy.sql)
to a PostgreSQL database with PostGIS enabled. It creates:

- `terrasense.regions` — the dissolved `NER` region boundary.
- `terrasense.states` — the eight Northeast states.
- `terrasense.districts` — the 119 district boundaries and optional LGD code.

All geometries are constrained to `MultiPolygon` with SRID 4326, validated by
PostGIS, and indexed with GiST. Foreign keys enforce:

```text
regions -> states -> districts
```

`source_feature_id` is unique at each administrative level. `lgd_code` remains
nullable because the selected geometry source did not provide verified LGD
codes; the schema does not invent them.

## Reproducible seed generation

From the repository root:

```powershell
py backend/scripts/generate_ner_postgis_seed.py
```

The script reads the canonical files under `data/geodata/ner/`, validates the
hierarchy, and writes `backend/db/seeds/ner_hierarchy.sql`. The generated SQL
uses parameter-free `ST_GeomFromGeoJSON(..., 4326)` expressions and
`ON CONFLICT ... DO UPDATE`, so reruns are deterministic and safe for an
already-created schema. The seed file is generated locally and ignored by
Git because it contains large geometry literals.

This is a data-loading utility, not a live database client. Production
integration should run the migration and seed through the team's chosen
PostgreSQL deployment process, then switch the API loader deliberately.
