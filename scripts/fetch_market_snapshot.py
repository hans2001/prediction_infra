#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
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


def _fetch_and_write(source: str, limit: int, out_dir: Path, stamp: str) -> tuple[str, float]:
    start = time.perf_counter()
    if source == "kalshi":
        payload = kalshi_public.fetch_markets(limit=limit)
        write_json(out_dir / f"kalshi_markets_{stamp}.json", payload)
    elif source == "polymarket":
        payload = polymarket_public.fetch_markets(limit=limit)
        write_json(out_dir / f"polymarket_markets_{stamp}.json", payload)
    else:
        raise ValueError(f"unsupported source: {source}")
    elapsed = time.perf_counter() - start
    return source, elapsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch public market snapshots.")
    parser.add_argument("--source", choices=["kalshi", "polymarket", "all"], default="all")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--out-dir", default=str(ROOT / "data" / "raw"))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    stamp = _timestamp()

    sources: list[str]
    if args.source == "all":
        sources = ["kalshi", "polymarket"]
    else:
        sources = [args.source]

    with ThreadPoolExecutor(max_workers=len(sources)) as ex:
        futures = [ex.submit(_fetch_and_write, source, args.limit, out_dir, stamp) for source in sources]
        for fut in futures:
            source, elapsed = fut.result()
            print(f"wrote {source} snapshot at {stamp} elapsed_sec={elapsed:.3f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
