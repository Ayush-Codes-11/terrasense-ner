# Phase 3A: PostgreSQL + PostGIS foundation

Phase 3A introduces the PostGIS persistence layer. Runtime hierarchy APIs still
use the validated file-backed Phase 2 loader. The FastAPI app does not import
`db`, connect at startup, or require `DATABASE_URL`. Database cutover is deferred.

## Architecture and data contract

- Synchronous SQLAlchemy 2.x, GeoAlchemy2, psycopg 3, and Alembic. Optional database
  dependencies live in `backend/requirements-db.txt`; development requirements
  include them, while Vercel runtime requirements remain unchanged.
- `regions` → `states` → `districts` → `analysis_zones`, with text primary keys,
  non-null foreign keys, and indexes on each foreign key.
- States, districts, and zones use `geometry(MultiPolygon,4326)`, GiST indexes,
  and non-null/valid/nonempty geometry constraints. A source Polygon is wrapped
  in a MultiPolygon without modifying ring order or coordinates. No repair,
  simplification, reprojection, or source rewriting occurs.
- Region JSONB metadata preserves the complete canonical metadata, including the
  `2026-09-11` LGD comparison date and unresolved CAPTCHA/session status. State and
  district JSONB metadata preserve their source, release, license, vintage, and
  original feature properties (including source feature IDs).
- State boundaries are the committed 2011 ADM1 dataset. District boundaries are
  the committed **2021 ADM2 prototype dataset**, not a fully current 2026
  administrative list. LGD codes are never guessed.
- Expected counts: 1 region, 8 states, 119 districts, 25 prototype analysis zones.
  District counts: IN-AR 25, IN-AS 33, IN-MN 16, IN-ML 11, IN-MZ 11,
  IN-NL 11, IN-SK 4, IN-TR 8.
- Aizawl is `IND-ADM2-76128533B34203923268864`, under IN-MZ, with null LGD code,
  `DETAILED_PILOT` / `STATIC_ML_VALIDATION_PENDING`. All 25 A01–E05 zones reference
  it and remain `PROTOTYPE_ANALYSIS_GRID`. Other districts remain
  `DISTRICT_BOUNDARY_ONLY` / `NOT_IMPLEMENTED`.

## Local setup

Run from the repository root using an activated Python virtual environment:

```powershell
python -m pip install -r backend/requirements-dev.txt
docker compose up -d --wait
$env:DATABASE_URL = "postgresql+psycopg://terrasense:terrasense@localhost:5432/terrasense"
python -m alembic upgrade head
python scripts/import_hierarchy_to_postgis.py
python scripts/import_hierarchy_to_postgis.py --validate-only
```

On POSIX shells use `export DATABASE_URL='...'`. Compose provides only PostGIS,
binds to localhost, and retains a named volume. The version tag is
`postgis/postgis:16-3.5` (PostgreSQL 16). Credentials shown here are local defaults
only; do not use them in production. `docker compose down` stops the service
without removing its data volume. Docker/PostgreSQL are not installed by this repo.

An existing PostgreSQL server with PostGIS available can be used instead. The
migration role must be able to create tables and enable PostGIS in `public`.
Schema creation belongs to Alembic, not the importer. Downgrade removes these four
tables and retains the potentially shared PostGIS extension.

Set `DATABASE_URL` explicitly for Alembic. The importer also supports the root
`.env` file without overriding already exported values. Configuration rejects
drivers other than `postgresql+psycopg` and does not initialize an engine at import.

## Import and validation

The importer reads only the committed root metadata, states, districts, and
`data/sample/grid-risk.geojson`; no network requests occur. It validates counts,
IDs, Aizawl, and geometry before connecting. Rows are sorted by primary key and
upserted in parent-first order in one transaction. A second import updates the
same keys and cannot create duplicates. It does not delete unexpected records;
parity validation rejects them and rolls the entire import back.

Before commit, validation compares every scalar/metadata field and every geometry
coordinate with the source. SQL checks include `ST_IsValid`, `ST_IsEmpty`,
`ST_SRID`, duplicate IDs, orphan foreign keys, and per-state district counts.
Invalid source or DB features are reported by ID; nothing is silently repaired.
`--validate-only` uses a read-only transaction.

Offline commands (no server needed):

```powershell
python scripts/import_hierarchy_to_postgis.py --dry-run
# DATABASE_URL is required to select the offline dialect, but no connection occurs.
python -m alembic upgrade head --sql
$env:PYTHONPATH = "backend"
python -m pytest ml/tests backend/tests -v --tb=short
```

Live tests are opt-in; a missing URL causes an explicit skip, not a connection
attempt. Use a development/test database where temporary schema creation is allowed:

```powershell
$env:POSTGIS_TEST_DATABASE_URL = $env:DATABASE_URL
python -m pytest backend/tests/test_postgis_integration.py -v --tb=short
```

Live tests migrate an isolated random schema inside a transaction, import twice,
validate spatial/scalar parity, exercise PK/FK/geometry constraints, and check
downgrade/re-upgrade. Teardown rolls back the schema and test data. An explicitly
configured but unreachable server fails the tests rather than silently skipping.

The separate `PostGIS Foundation` workflow provisions a health-checked service,
migrates and imports twice, validates, and runs the live tests. The existing
backend/parity and frontend CI workflow is unchanged. Offline SQL generation does
not prove live migration success; live tests must pass before database cutover.

References: [SQLAlchemy PostgreSQL upserts](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#insert-on-conflict-upsert),
[GeoAlchemy geometry types](https://geoalchemy-2.readthedocs.io/en/latest/types.html),
[Alembic offline migrations](https://alembic.sqlalchemy.org/en/latest/offline.html),
[PostGIS Docker images](https://github.com/postgis/docker-postgis).
