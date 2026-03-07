#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pred_infra.storage.postgres import apply_schema, connect_db, load_db_url  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize PostgreSQL schema for pred-infra.")
    parser.add_argument("--db-url", default="")
    parser.add_argument("--schema", default=str(ROOT / "sql" / "001_init_postgres.sql"))
    args = parser.parse_args()

    db_url = load_db_url(args.db_url)
    with connect_db(db_url) as conn:
        apply_schema(conn, args.schema)
    print("postgres_schema_init=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
