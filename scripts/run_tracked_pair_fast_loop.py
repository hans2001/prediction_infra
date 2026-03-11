#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pred_infra.strategy.cross_venue import load_pair_map_from_inputs  # noqa: E402
from pred_infra.strategy.cross_venue_parity import (  # noqa: E402
    VenueCostModel,
    evaluate_cross_venue_binary_locks,
    summarize_binary_lock_results,
)
from pred_infra.strategy.fast_execution import (  # noqa: E402
    ExecutionPolicy,
    select_execution_candidates,
    simulate_execution_on_next_snapshot,
    summarize_paper_execution,
)
from pred_infra.strategy.fast_loop_reporting import (  # noqa: E402
    append_csv,
    build_execution_candidate_rows,
    build_paper_execution_rows,
    build_returns_rows,
)
from pred_infra.strategy.pair_lock_watcher import (  # noqa: E402
    append_jsonl,
    build_pair_lock_opportunity_rows,
    build_pair_lock_watcher_event,
    build_pair_lock_watcher_status,
    write_json,
)
from pred_infra.strategy.triage_selection import filter_pair_map_by_pair_ids, select_pair_ids_from_triage_report  # noqa: E402


def load_quote_rows(path: Path) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            row = json.loads(text)
            rows[str(row["pair_id"])] = row
    return rows


def build_eval_rows(rows: dict[str, dict[str, object]]) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    kalshi_rows: dict[str, dict[str, object]] = {}
    polymarket_rows: dict[str, dict[str, object]] = {}
    for row in rows.values():
        kalshi_rows[str(row["kalshi_market_id"])] = {
            "yes_ask": row.get("kalshi_yes_ask"),
            "no_ask": row.get("kalshi_no_ask"),
            "yes_bid": row.get("kalshi_yes_bid"),
            "no_bid": row.get("kalshi_no_bid"),
            "yes_ask_size": row.get("kalshi_yes_ask_size"),
            "no_ask_size": row.get("kalshi_no_ask_size"),
        }
        polymarket_rows[str(row["polymarket_market_id"])] = {
            "yes_ask": row.get("polymarket_yes_ask"),
            "no_ask": row.get("polymarket_no_ask"),
            "yes_bid": row.get("polymarket_yes_bid"),
            "no_bid": row.get("polymarket_no_bid"),
            "yes_ask_size": row.get("polymarket_yes_ask_size"),
            "no_ask_size": row.get("polymarket_no_ask_size"),
        }
    return kalshi_rows, polymarket_rows


def persist_return_rows(
    return_rows: list[dict[str, object]],
    *,
    returns_out: Path,
    history_csv: str,
) -> None:
    if not return_rows:
        return
    columns = ["timestamp", "strategy", "net_return", "source", "run_id", "note"]
    append_csv(returns_out, columns, return_rows)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", suffix=".csv", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        append_csv(tmp_path, columns, return_rows)
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "upsert_returns_history.py"),
                "--input-csv",
                str(tmp_path),
                "--history",
                history_csv,
            ],
            check=True,
        )
    finally:
        tmp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a tracked-pair fast quote loop and emit strict binary-lock candidates.")
    parser.add_argument("--pair-map", default="")
    parser.add_argument("--contract-ontology", default="")
    parser.add_argument("--triage-report", default="")
    parser.add_argument("--top-n", type=int, default=0)
    parser.add_argument(
        "--allowed-recommendations",
        default="start_paper_tracking,collect_more_paper_evidence,eligible_for_paper_review",
    )
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run until externally stopped. If set, --iterations is ignored.",
    )
    parser.add_argument("--sleep-sec", type=float, default=5.0)
    parser.add_argument("--kalshi-buy-slippage", type=float, default=0.001)
    parser.add_argument("--polymarket-buy-slippage", type=float, default=0.001)
    parser.add_argument("--min-size", type=float, default=10.0)
    parser.add_argument("--max-total-cost", type=float, default=0.999)
    parser.add_argument("--min-size-survival-ratio", type=float, default=0.6)
    parser.add_argument("--max-polymarket-book-age-sec", type=float, default=20.0)
    parser.add_argument("--quotes-dir", default=str(ROOT / "data" / "quotes"))
    parser.add_argument("--reports-dir", default=str(ROOT / "data" / "reports"))
    parser.add_argument("--candidate-ledger", default=str(ROOT / "data" / "reports" / "tracked_pair_candidates.csv"))
    parser.add_argument("--paper-ledger", default=str(ROOT / "data" / "reports" / "tracked_pair_paper_execution.csv"))
    parser.add_argument("--returns-out", default=str(ROOT / "data" / "returns" / "tracked_pair_fast_loop_returns.csv"))
    parser.add_argument("--history-csv", default=str(ROOT / "data" / "returns" / "returns_history.csv"))
    parser.add_argument("--watcher-status-file", default=str(ROOT / "data" / "reports" / "pair_lock_watcher_status.json"))
    parser.add_argument("--watcher-events-file", default=str(ROOT / "data" / "reports" / "pair_lock_watcher_events.jsonl"))
    parser.add_argument(
        "--watcher-opportunities-file",
        default=str(ROOT / "data" / "reports" / "pair_lock_watcher_opportunities.jsonl"),
    )
    args = parser.parse_args()

    pair_map = load_pair_map_from_inputs(pair_map_path=args.pair_map, contract_ontology_path=args.contract_ontology)
    if args.triage_report:
        selected_pair_ids = set(
            select_pair_ids_from_triage_report(
                Path(args.triage_report),
                top_n=args.top_n,
                allowed_recommendations={item.strip() for item in args.allowed_recommendations.split(",") if item.strip()},
            )
        )
        pair_map = filter_pair_map_by_pair_ids(pair_map, selected_pair_ids)
        if not pair_map:
            raise SystemExit(f"no pair ids selected from triage report {args.triage_report}")
    pair_source_path = (
        args.contract_ontology
        if args.contract_ontology
        else (str(ROOT / "configs" / "contract_ontology.csv") if not args.pair_map else args.pair_map)
    )
    quotes_dir = Path(args.quotes_dir)
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    candidate_ledger = Path(args.candidate_ledger)
    paper_ledger = Path(args.paper_ledger)
    returns_out = Path(args.returns_out)
    watcher_status_file = Path(args.watcher_status_file)
    watcher_events_file = Path(args.watcher_events_file)
    watcher_opportunities_file = Path(args.watcher_opportunities_file)
    execution_policy = ExecutionPolicy(
        min_size=args.min_size,
        max_total_cost=args.max_total_cost,
        min_size_survival_ratio=args.min_size_survival_ratio,
        max_polymarket_book_age_sec=args.max_polymarket_book_age_sec,
    )
    pending_candidates = []
    idx = 0
    while True:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        generated_at_utc = datetime.now(UTC).isoformat()
        quotes_path = quotes_dir / f"tracked_pair_quotes_{stamp}.jsonl"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "fetch_tracked_pair_quotes.py"),
                *(
                    ["--contract-ontology", args.contract_ontology]
                    if args.contract_ontology or not args.pair_map
                    else ["--pair-map", args.pair_map]
                ),
                *(["--triage-report", args.triage_report] if args.triage_report else []),
                *(["--top-n", str(args.top_n)] if args.triage_report and args.top_n > 0 else []),
                *(
                    ["--allowed-recommendations", args.allowed_recommendations]
                    if args.triage_report and args.allowed_recommendations
                    else []
                ),
                "--out",
                str(quotes_path),
            ],
            check=True,
        )

        quote_rows = load_quote_rows(quotes_path)
        kalshi_rows, polymarket_rows = build_eval_rows(quote_rows)
        results = evaluate_cross_venue_binary_locks(
            pair_map,
            kalshi_rows,
            polymarket_rows,
            kalshi_costs=VenueCostModel(buy_slippage=args.kalshi_buy_slippage),
            polymarket_costs=VenueCostModel(buy_slippage=args.polymarket_buy_slippage),
        )
        execution_candidates = select_execution_candidates(results, quote_rows, execution_policy)
        paper_results = simulate_execution_on_next_snapshot(
            pending_candidates,
            quote_rows,
            kalshi_costs=VenueCostModel(buy_slippage=args.kalshi_buy_slippage),
            polymarket_costs=VenueCostModel(buy_slippage=args.polymarket_buy_slippage),
            policy=execution_policy,
        )
        candidate_rows = build_execution_candidate_rows(
            execution_candidates,
            run_id=stamp,
            generated_at_utc=generated_at_utc,
            quote_snapshot=str(quotes_path),
        )
        paper_rows = build_paper_execution_rows(
            paper_results,
            run_id=stamp,
            generated_at_utc=generated_at_utc,
            quote_snapshot=str(quotes_path),
        )
        return_rows = build_returns_rows(
            paper_results,
            timestamp_utc=generated_at_utc,
            run_id=stamp,
        )
        append_csv(
            candidate_ledger,
            [
                "run_id",
                "generated_at_utc",
                "quote_snapshot",
                "pair_id",
                "label",
                "buy_yes_venue",
                "buy_no_venue",
                "expected_total_cost",
                "expected_net_edge",
                "min_size_available",
            ],
            candidate_rows,
        )
        append_csv(
            paper_ledger,
            [
                "run_id",
                "generated_at_utc",
                "quote_snapshot",
                "pair_id",
                "label",
                "status",
                "reason",
                "expected_total_cost",
                "realized_total_cost",
                "expected_net_edge",
                "realized_net_edge",
                "min_size_available",
                "realized_min_size",
            ],
            paper_rows,
        )
        persist_return_rows(return_rows, returns_out=returns_out, history_csv=args.history_csv)
        report = {
            "generated_at_utc": generated_at_utc,
            "pair_source_path": pair_source_path,
            "quote_snapshot": str(quotes_path),
            "loop_mode": "continuous" if args.continuous else "bounded",
            "iteration_index": idx + 1,
            "summary": summarize_binary_lock_results(results),
            "execution_policy": asdict(execution_policy),
            "execution_candidates": [asdict(item) for item in execution_candidates],
            "paper_execution_summary": summarize_paper_execution(paper_results),
            "paper_execution_results": [asdict(item) for item in paper_results],
            "candidate_ledger": str(candidate_ledger),
            "paper_ledger": str(paper_ledger),
            "returns_rows_written_this_iteration": len(return_rows),
            "results": [asdict(result) for result in results],
        }
        report_path = reports_dir / f"tracked_pair_fast_loop_{stamp}.json"
        report_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        watcher_status = build_pair_lock_watcher_status(
            run_id=stamp,
            generated_at_utc=generated_at_utc,
            interval_seconds=args.sleep_sec,
            triage_report=args.triage_report,
            quote_snapshot=str(quotes_path),
            candidate_count=len(execution_candidates),
            provable_lock_count=int(report["summary"].get("provable_lock_count", 0)),
            best_lock_edge=report["summary"].get("best_net_edge"),
            execution_candidates=execution_candidates,
            paper_results=paper_results,
        )
        write_json(watcher_status_file, watcher_status)
        append_jsonl(
            watcher_events_file,
            build_pair_lock_watcher_event(
                run_id=stamp,
                generated_at_utc=generated_at_utc,
                quote_snapshot=str(quotes_path),
                triage_report=args.triage_report,
                summary=report["summary"],
                execution_candidates=execution_candidates,
                paper_results=paper_results,
            ),
        )
        for row in build_pair_lock_opportunity_rows(
            results,
            run_id=stamp,
            generated_at_utc=generated_at_utc,
            quote_snapshot=str(quotes_path),
        ):
            append_jsonl(watcher_opportunities_file, row)
        if args.continuous:
            print(f"iteration={idx + 1}/continuous quote_snapshot={quotes_path} report={report_path}")
        else:
            print(f"iteration={idx + 1}/{args.iterations} quote_snapshot={quotes_path} report={report_path}")
        pending_candidates = execution_candidates
        idx += 1

        if not args.continuous and idx >= args.iterations:
            break

        time.sleep(args.sleep_sec)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
