#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> float:
    print(f"+ {' '.join(cmd)}")
    start = time.perf_counter()
    subprocess.run(cmd, cwd=cwd, check=True)
    return time.perf_counter() - start


def has_returns_rows(path: Path) -> bool:
    if not path.exists():
        return False
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for _ in reader:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run daily pred-infra pipeline.")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--snapshot-limit", type=int, default=100)
    parser.add_argument("--max-age-hours", type=float, default=24.0)
    parser.add_argument("--returns-history", default="data/returns/returns_history.csv")
    parser.add_argument("--gates", default="configs/stat_validation_gates.example.json")
    parser.add_argument("--focus-strategy", default="mm_v1")
    parser.add_argument("--n-trials", type=int, default=5000)
    parser.add_argument("--pbo-splits", type=int, default=200)
    parser.add_argument("--db-write", action="store_true", help="sync normalized/returns data to PostgreSQL")
    parser.add_argument("--db-url", default="", help="optional DATABASE_URL override")
    parser.add_argument("--db-init-schema", action="store_true", help="apply schema before ingest")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    reports = root / "data" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    timings: dict[str, float] = {}

    timings["fetch"] = run(
        [
            "python3",
            "scripts/fetch_market_snapshot.py",
            "--source",
            "all",
            "--limit",
            str(args.snapshot_limit),
        ],
        cwd=root,
    )
    timings["normalize"] = run(["python3", "scripts/normalize_snapshots.py"], cwd=root)
    timings["integrity"] = run(
        [
            "python3",
            "scripts/build_integrity_report.py",
            "--max-age-hours",
            str(args.max_age_hours),
        ],
        cwd=root,
    )
    if args.db_write:
        db_cmd = [
            "python3",
            "scripts/ingest_normalized_to_db.py",
            "--normalized-dir",
            "data/normalized",
        ]
        if args.db_url:
            db_cmd += ["--db-url", args.db_url]
        if args.db_init_schema:
            db_cmd.append("--init-schema")
        timings["db_ingest_snapshots"] = run(db_cmd, cwd=root)

    history_path = root / args.returns_history
    if has_returns_rows(history_path):
        timings["probability_report"] = run(
            [
                "python3",
                "scripts/probability_report.py",
                "--returns",
                str(history_path),
                "--focus-strategy",
                args.focus_strategy,
                "--n-trials",
                str(args.n_trials),
                "--pbo-splits",
                str(args.pbo_splits),
                "--out",
                str(reports / f"probability_report_{stamp}.json"),
            ],
            cwd=root,
        )
        timings["validate_strategy"] = run(
            [
                "python3",
                "scripts/validate_strategy.py",
                "--returns",
                str(history_path),
                "--gates",
                args.gates,
                "--focus-strategy",
                args.focus_strategy,
                "--n-trials",
                str(args.n_trials),
                "--pbo-splits",
                str(args.pbo_splits),
                "--out",
                str(reports / f"validation_report_{stamp}.json"),
            ],
            cwd=root,
        )
        if args.db_write:
            returns_cmd = [
                "python3",
                "scripts/sync_returns_to_db.py",
                "--returns-csv",
                str(history_path),
            ]
            if args.db_url:
                returns_cmd += ["--db-url", args.db_url]
            if args.db_init_schema:
                returns_cmd.append("--init-schema")
            timings["db_sync_returns"] = run(returns_cmd, cwd=root)
    else:
        print(f"skip strategy validation (returns history empty or missing): {history_path}")

    metrics = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "timings_sec": timings,
        "total_sec": sum(timings.values()),
    }
    metrics_path = reports / "pipeline_metrics.jsonl"
    with metrics_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(metrics, ensure_ascii=True))
        f.write("\n")
    print(f"wrote {metrics_path}")
    print("daily_pipeline=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
