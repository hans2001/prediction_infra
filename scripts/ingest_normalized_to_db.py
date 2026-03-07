#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pred_infra.storage.postgres import apply_schema, connect_db, load_db_url  # noqa: E402

INSERT_SQL = """
INSERT INTO market_snapshots (
    source, snapshot_ts, market_id, event_id, title, status, close_time, updated_time,
    yes_bid, yes_ask, no_bid, no_ask, yes_price, no_price, last_price, liquidity, volume, raw_file
) VALUES (
    %(source)s, %(snapshot_ts)s, %(market_id)s, %(event_id)s, %(title)s, %(status)s, %(close_time)s, %(updated_time)s,
    %(yes_bid)s, %(yes_ask)s, %(no_bid)s, %(no_ask)s, %(yes_price)s, %(no_price)s, %(last_price)s, %(liquidity)s, %(volume)s, %(raw_file)s
)
ON CONFLICT (source, snapshot_ts, market_id)
DO UPDATE SET
    event_id = EXCLUDED.event_id,
    title = EXCLUDED.title,
    status = EXCLUDED.status,
    close_time = EXCLUDED.close_time,
    updated_time = EXCLUDED.updated_time,
    yes_bid = EXCLUDED.yes_bid,
    yes_ask = EXCLUDED.yes_ask,
    no_bid = EXCLUDED.no_bid,
    no_ask = EXCLUDED.no_ask,
    yes_price = EXCLUDED.yes_price,
    no_price = EXCLUDED.no_price,
    last_price = EXCLUDED.last_price,
    liquidity = EXCLUDED.liquidity,
    volume = EXCLUDED.volume,
    raw_file = EXCLUDED.raw_file;
"""


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest normalized jsonl snapshots into PostgreSQL.")
    parser.add_argument("--db-url", default="")
    parser.add_argument("--normalized-dir", default=str(ROOT / "data" / "normalized"))
    parser.add_argument("--schema", default=str(ROOT / "sql" / "001_init_postgres.sql"))
    parser.add_argument("--init-schema", action="store_true")
    args = parser.parse_args()

    files = sorted(Path(args.normalized_dir).glob("*.jsonl"))
    if not files:
        print("no normalized files found")
        return 1

    db_url = load_db_url(args.db_url)
    inserted = 0
    with connect_db(db_url) as conn:
        if args.init_schema:
            apply_schema(conn, args.schema)
        with conn.cursor() as cur:
            for path in files:
                rows = load_jsonl(path)
                if not rows:
                    continue
                cur.executemany(INSERT_SQL, rows)
                inserted += len(rows)
        conn.commit()

    print(f"ingested_rows={inserted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
