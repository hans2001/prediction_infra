#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

DEFAULT_HEADER = ["timestamp", "strategy", "net_return", "source", "run_id", "note"]


def ensure_history_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=DEFAULT_HEADER)
            writer.writeheader()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def normalize_row(row: dict[str, str], default_source: str) -> dict[str, str]:
    normalized = {
        "timestamp": row.get("timestamp", "").strip(),
        "strategy": row.get("strategy", "").strip(),
        "net_return": row.get("net_return", "").strip(),
        "source": row.get("source", "").strip() or default_source,
        "run_id": row.get("run_id", "").strip(),
        "note": row.get("note", "").strip(),
    }
    if not normalized["timestamp"] or not normalized["strategy"] or not normalized["net_return"]:
        raise ValueError("each row requires timestamp,strategy,net_return")
    float(normalized["net_return"])
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert strategy returns into returns history.")
    parser.add_argument("--input-csv", required=True, help="csv with timestamp,strategy,net_return")
    parser.add_argument("--history", default="data/returns/returns_history.csv")
    parser.add_argument("--default-source", default="paper")
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    history_path = Path(args.history)

    ensure_history_file(history_path)
    existing_rows = read_rows(history_path)
    existing_keys = {(r["timestamp"], r["strategy"], r.get("source", "")) for r in existing_rows}

    incoming_rows = read_rows(input_path)
    accepted: list[dict[str, str]] = []
    for row in incoming_rows:
        normalized = normalize_row(row, args.default_source)
        key = (normalized["timestamp"], normalized["strategy"], normalized["source"])
        if key in existing_keys:
            continue
        existing_keys.add(key)
        accepted.append(normalized)

    if accepted:
        all_rows = existing_rows + accepted
        all_rows.sort(key=lambda r: (r["timestamp"], r["strategy"], r["source"]))
        with history_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=DEFAULT_HEADER)
            writer.writeheader()
            writer.writerows(all_rows)

    print(f"input_rows={len(incoming_rows)}")
    print(f"inserted_rows={len(accepted)}")
    print(f"history={history_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
