#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pred_infra.storage.postgres import load_db_url, prepare_runtime_db_url  # noqa: E402
from pred_infra.storage.runtime_state import (  # noqa: E402
    count_pipeline_metrics,
    fetch_latest_pipeline_run,
    fetch_recent_pipeline_metrics,
    reconcile_stale_running_run,
)

ET = ZoneInfo("America/New_York")

try:
    import psycopg
except ModuleNotFoundError:  # pragma: no cover - optional dependency behavior
    psycopg = None


def latest_file(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern))
    return matches[-1] if matches else None


def read_json(path: Path | None) -> dict[str, object]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def format_et(value: object) -> str:
    if not isinstance(value, str) or not value:
        return "n/a"
    return datetime.fromisoformat(value).astimezone(ET).isoformat()


def summarize_returns_history(path: Path) -> tuple[int, dict[str, int]]:
    if not path.exists():
        return 0, {}
    total = 0
    strategy_counts: dict[str, int] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("source", "").strip() == "bootstrap_example":
                continue
            strategy = row.get("strategy", "").strip()
            if not strategy:
                continue
            total += 1
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
    return total, dict(sorted(strategy_counts.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Print current pred-infra pipeline status.")
    parser.add_argument("--reports-dir", default=str(ROOT / "data" / "reports"))
    parser.add_argument("--returns-history", default=str(ROOT / "data" / "returns" / "returns_history.csv"))
    parser.add_argument("--db-url", default="", help="runtime-state DATABASE_URL override")
    parser.add_argument("--db-path", default="", help="deprecated local SQLite status DB override")
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    returns_history_path = Path(args.returns_history)
    sqlite_db_path = reports_dir / "pipeline_state.db"
    try:
        db_url = load_db_url(args.db_url)
    except ValueError:
        db_url = ""
    runtime_warning = ""
    if db_url:
        db_url, runtime_warning = prepare_runtime_db_url(ROOT, db_url)
    db_path = Path(args.db_path) if args.db_path else sqlite_db_path
    reconciled_run = None
    try:
        status = fetch_latest_pipeline_run(db_url=db_url, db_path=db_path)
        reconciled_run = reconcile_stale_running_run(db_url=db_url, db_path=db_path)
        if reconciled_run is not None:
            status = reconciled_run
        recent_metrics = fetch_recent_pipeline_metrics(1, db_url=db_url, db_path=db_path)
        metric_count = count_pipeline_metrics(db_url=db_url, db_path=db_path)
        runtime_backend = "postgres" if db_url else "sqlite"
    except (ModuleNotFoundError, OSError, RuntimeError) as exc:
        db_url = ""
        status = fetch_latest_pipeline_run(db_path=db_path)
        reconciled_run = reconcile_stale_running_run(db_path=db_path)
        if reconciled_run is not None:
            status = reconciled_run
        recent_metrics = fetch_recent_pipeline_metrics(1, db_path=db_path)
        metric_count = count_pipeline_metrics(db_path=db_path)
        runtime_backend = "sqlite"
        runtime_warning = runtime_warning or f"runtime_state_db_fallback=sqlite reason={type(exc).__name__}: {exc}"
    except Exception as exc:
        if psycopg is not None and isinstance(exc, psycopg.Error):
            db_url = ""
            status = fetch_latest_pipeline_run(db_path=db_path)
            reconciled_run = reconcile_stale_running_run(db_path=db_path)
            if reconciled_run is not None:
                status = reconciled_run
            recent_metrics = fetch_recent_pipeline_metrics(1, db_path=db_path)
            metric_count = count_pipeline_metrics(db_path=db_path)
            runtime_backend = "sqlite"
            runtime_warning = runtime_warning or f"runtime_state_db_fallback=sqlite reason={type(exc).__name__}: {exc}"
        else:
            raise
    probability_path = latest_file(reports_dir, "probability_report_*.json")
    validation_path = latest_file(reports_dir, "validation_report_*.json")
    leaderboard_path = latest_file(reports_dir, "strategy_leaderboard_*.json")
    probability = read_json(probability_path)
    validation = read_json(validation_path)
    leaderboard = read_json(leaderboard_path)
    leaderboard_rows = leaderboard.get("rows", []) if isinstance(leaderboard, dict) else []
    top_row = leaderboard_rows[0] if isinstance(leaderboard_rows, list) and leaderboard_rows else {}
    total_paper_observations, strategy_counts = summarize_returns_history(returns_history_path)

    now = datetime.now(UTC)
    last_success_raw = status.get("last_success_at_utc")
    expected_interval = int(status.get("expected_interval_minutes", 15) or 15)
    next_expected = None
    if isinstance(last_success_raw, str) and last_success_raw:
        next_expected = datetime.fromisoformat(last_success_raw) + timedelta(minutes=expected_interval)

    print(f"status={status.get('status', 'unknown')}")
    print(f"run_id={status.get('run_id', 'n/a')}")
    print(f"current_step={status.get('current_step') or 'idle'}")
    print("display_timezone=America/New_York")
    print(f"last_success_at_utc={last_success_raw or 'n/a'}")
    print(f"last_success_at_et={format_et(last_success_raw)}")
    print(f"last_failure_at_utc={status.get('last_failure_at_utc') or 'n/a'}")
    print(f"last_failure_at_et={format_et(status.get('last_failure_at_utc'))}")
    print(f"last_output_line={status.get('last_output_line') or 'n/a'}")
    print(f"total_sec={status.get('total_sec', 'n/a')}")
    if next_expected is not None:
        print(f"next_expected_run_utc={next_expected.isoformat()}")
        print(f"next_expected_run_et={next_expected.astimezone(ET).isoformat()}")
        print(f"seconds_until_next_expected={int((next_expected - now).total_seconds())}")
    else:
        print("next_expected_run_utc=n/a")
        print("next_expected_run_et=n/a")
        print("seconds_until_next_expected=n/a")
    print(f"latest_probability_report={probability_path or 'n/a'}")
    print(f"latest_validation_report={validation_path or 'n/a'}")
    print(f"latest_strategy_leaderboard={leaderboard_path or 'n/a'}")
    print(f"focus_strategy={probability.get('focus_strategy', 'n/a')}")
    print(f"focus_observations={probability.get('focus_observations', 'n/a')}")
    print(f"p_profit={probability.get('p_profit', 'n/a')}")
    print(f"go_live_candidate={validation.get('go_live_candidate', 'n/a')}")
    failed_rules = validation.get("failed_rules", [])
    print(f"failed_rules={'; '.join(failed_rules) if failed_rules else 'none'}")
    print(f"leader_strategy={top_row.get('strategy', 'n/a') if isinstance(top_row, dict) else 'n/a'}")
    print(f"leader_reject_stage={top_row.get('reject_stage', 'n/a') if isinstance(top_row, dict) else 'n/a'}")
    print(f"leader_mean_return={top_row.get('mean_return', 'n/a') if isinstance(top_row, dict) else 'n/a'}")
    print(f"total_paper_observations={total_paper_observations}")
    print(f"strategy_observation_counts={json.dumps(strategy_counts, ensure_ascii=True)}")
    print(f"metrics_tail={json.dumps(recent_metrics[0], ensure_ascii=True) if recent_metrics else 'missing'}")
    print(f"runtime_state_backend={runtime_backend}")
    print(f"runtime_state_db_url={'configured' if db_url else 'n/a'}")
    print(f"runtime_state_db_path={db_path}")
    print(f"db_latest_run_id={status.get('run_id', 'n/a')}")
    print(f"db_latest_status={status.get('status', 'n/a')}")
    print(f"db_metric_rows={metric_count}")
    print(f"returns_history={returns_history_path}")
    if runtime_warning:
        print(runtime_warning)
    if reconciled_run is not None:
        print(f"runtime_state_reconciled_run_id={reconciled_run['run_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
