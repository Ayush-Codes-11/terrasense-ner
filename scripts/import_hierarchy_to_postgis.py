"""Run from any directory; canonical files are resolved from this repository."""
import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from dotenv import load_dotenv
from db.import_hierarchy import import_records, load_records, validate_database
from db.session import create_db_engine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate source mapping without a DB")
    mode.add_argument("--validate-only", action="store_true", help="Check DB parity without writing")
    args = parser.parse_args()
    records = load_records()
    if args.dry_run:
        print(json.dumps({"source_counts": {k: len(v) for k, v in records.items()},
                          "database_accessed": False}, indent=2))
        return
    load_dotenv(REPO_ROOT / ".env", override=False)
    engine = create_db_engine()
    try:
        with engine.begin() as connection:
            if args.validate_only:
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                report = validate_database(connection, records)
            else:
                report = import_records(connection, records)
        print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
