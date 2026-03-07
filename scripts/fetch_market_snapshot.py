#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pred_infra.collector import kalshi_public, polymarket_public  # noqa: E402


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch public market snapshots.")
    parser.add_argument("--source", choices=["kalshi", "polymarket", "all"], default="all")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--out-dir", default=str(ROOT / "data" / "raw"))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    stamp = _timestamp()

    if args.source in {"kalshi", "all"}:
        kalshi = kalshi_public.fetch_markets(limit=args.limit)
        write_json(out_dir / f"kalshi_markets_{stamp}.json", kalshi)
        print(f"wrote kalshi snapshot at {stamp}")

    if args.source in {"polymarket", "all"}:
        polymarket = polymarket_public.fetch_markets(limit=args.limit)
        write_json(out_dir / f"polymarket_markets_{stamp}.json", polymarket)
        print(f"wrote polymarket snapshot at {stamp}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
