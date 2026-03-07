#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pred_infra.storage.postgres import apply_schema, connect_db, load_db_url  # noqa: E402

INSERT_SQL = """
INSERT INTO strategy_returns (timestamp, strategy, net_return, source, run_id, note)
VALUES (%(timestamp)s, %(strategy)s, %(net_return)s, %(source)s, %(run_id)s, %(note)s)
ON CONFLICT (timestamp, strategy, source, run_id)
DO UPDATE SET
    net_return = EXCLUDED.net_return,
    note = EXCLUDED.note;
"""


def load_rows(path: Path, default_source: str) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            strategy = row.get("strategy", "").strip()
            ts = row.get("timestamp", "").strip()
            net_return = row.get("net_return", "").strip()
            if not strategy or not ts or not net_return:
                continue
            rows.append(
                {
                    "timestamp": ts,
                    "strategy": strategy,
                    "net_return": float(net_return),
                    "source": row.get("source", "").strip() or default_source,
                    "run_id": row.get("run_id", "").strip(),
                    "note": row.get("note", "").strip(),
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync returns_history.csv into PostgreSQL.")
    parser.add_argument("--db-url", default="")
    parser.add_argument("--returns-csv", default=str(ROOT / "data" / "returns" / "returns_history.csv"))
    parser.add_argument("--default-source", default="paper")
    parser.add_argument("--schema", default=str(ROOT / "sql" / "001_init_postgres.sql"))
    parser.add_argument("--init-schema", action="store_true")
    args = parser.parse_args()

    rows = load_rows(Path(args.returns_csv), default_source=args.default_source)
    if not rows:
        print("no returns rows to sync")
        return 0

    db_url = load_db_url(args.db_url)
    with connect_db(db_url) as conn:
        if args.init_schema:
            apply_schema(conn, args.schema)
        with conn.cursor() as cur:
            cur.executemany(INSERT_SQL, rows)
        conn.commit()
    print(f"synced_returns_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
