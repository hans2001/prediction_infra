#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pred_infra.collector.normalize import normalize_kalshi_payload, normalize_polymarket_payload  # noqa: E402

STAMP_RE = re.compile(r"_(\d{8}T\d{6}Z)\.json$")


def parse_snapshot_ts_from_name(path: Path) -> str:
    match = STAMP_RE.search(path.name)
    if not match:
        return datetime.now(UTC).isoformat()
    stamp = match.group(1)
    parsed = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    return parsed.isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True))
            f.write("\n")


def normalize_file(path: Path) -> tuple[list[dict[str, Any]], str]:
    payload = load_json(path)
    snapshot_ts = parse_snapshot_ts_from_name(path)
    if path.name.startswith("kalshi_"):
        return normalize_kalshi_payload(payload, snapshot_ts=snapshot_ts, raw_file=path.name), "kalshi"
    if path.name.startswith("polymarket_"):
        return normalize_polymarket_payload(payload, snapshot_ts=snapshot_ts, raw_file=path.name), "polymarket"
    return [], "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize raw snapshots into a common JSONL schema.")
    parser.add_argument("--raw-dir", default=str(ROOT / "data" / "raw"))
    parser.add_argument("--out-dir", default=str(ROOT / "data" / "normalized"))
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir)
    files = sorted(raw_dir.glob("*_markets_*.json"))
    if not files:
        print("no raw snapshot files found")
        return 1

    total_rows = 0
    for path in files:
        rows, source = normalize_file(path)
        if source == "unknown":
            continue
        out_path = out_dir / f"{path.stem}.jsonl"
        write_jsonl(out_path, rows)
        total_rows += len(rows)
        print(f"normalized {len(rows)} rows from {path.name} -> {out_path.name}")

    print(f"done normalized_rows={total_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
