"""Explicit read-only deployment readiness check; exit nonzero on failure."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def main():
    engine = None
    try:
        from db.hierarchy_reader import get_postgis_engine
        from db.readiness import check_readiness
        from db.session import database_url

        engine = get_postgis_engine(database_url())
        with engine.connect() as connection, connection.begin():
            connection.exec_driver_sql(
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            report = check_readiness(connection)
        print(json.dumps(report, sort_keys=True))
        return 0
    except Exception:
        # Do not print driver exceptions, SQL, credentials, or connection URLs.
        print("PostGIS readiness failed: check DB configuration, connectivity, "
              "extension, migration revision, and canonical import.", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
