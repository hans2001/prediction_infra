#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from datetime import UTC, datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@dataclass
class PairSummary:
    pair_id: str
    candidate_cycles: int = 0
    fill_count: int = 0
    opportunity_count: int = 0
    return_rows: int = 0
    avg_edge: float = 0.0
    avg_return: float = 0.0
    max_edge: float = 0.0
    min_total_cost: float | None = None
    first_timestamp_utc: str = ""
    last_timestamp_utc: str = ""
    snapshots_seen: int = 0
    unique_quote_states: int = 0
    effective_state_runs: int = 0
    effective_execution_runs: int = 0
    effective_fill_runs: int = 0
    effective_miss_runs: int = 0
    effective_return_runs: int = 0
    avg_effective_return: float = 0.0
    recommendation: str = ""
    recommendation_reason: str = ""


def parse_note(note: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    for raw_part in note.split(";"):
        part = raw_part.strip()
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        payload[key.strip()] = value.strip()
    return payload


def accumulate_event_metrics(events_path: Path) -> tuple[dict[str, PairSummary], int]:
    summaries: dict[str, PairSummary] = {}
    cycle_count = 0
    with events_path.open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            row = json.loads(text)
            cycle_count += 1
            for candidate in row.get("execution_candidates", []):
                pair_id = str(candidate["pair_id"])
                summary = summaries.setdefault(pair_id, PairSummary(pair_id=pair_id))
                summary.candidate_cycles += 1
                timestamp = str(row.get("timestamp_utc") or "")
                if not summary.first_timestamp_utc:
                    summary.first_timestamp_utc = timestamp
                summary.last_timestamp_utc = timestamp
            for filled in row.get("filled_results", []):
                pair_id = str(filled["pair_id"])
                summary = summaries.setdefault(pair_id, PairSummary(pair_id=pair_id))
                summary.fill_count += 1
    return summaries, cycle_count


def accumulate_opportunity_metrics(opportunities_path: Path, summaries: dict[str, PairSummary]) -> None:
    edge_sums: dict[str, float] = defaultdict(float)
    with opportunities_path.open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            row = json.loads(text)
            pair_id = str(row["pair_id"])
            summary = summaries.setdefault(pair_id, PairSummary(pair_id=pair_id))
            summary.opportunity_count += 1
            edge = float(row.get("net_edge", 0.0) or 0.0)
            edge_sums[pair_id] += edge
            summary.max_edge = max(summary.max_edge, edge)
            total_cost = float(row.get("total_cost", 0.0) or 0.0)
            summary.min_total_cost = total_cost if summary.min_total_cost is None else min(summary.min_total_cost, total_cost)
    for pair_id, summary in summaries.items():
        if summary.opportunity_count > 0:
            summary.avg_edge = edge_sums[pair_id] / summary.opportunity_count


def accumulate_return_metrics(returns_path: Path, summaries: dict[str, PairSummary]) -> None:
    return_sums: dict[str, float] = defaultdict(float)
    with returns_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            note = parse_note(row.get("note", ""))
            pair_id = note.get("pair_id", "").strip()
            if not pair_id:
                continue
            summary = summaries.setdefault(pair_id, PairSummary(pair_id=pair_id))
            summary.return_rows += 1
            return_sums[pair_id] += float(row.get("net_return", 0.0) or 0.0)
    for pair_id, summary in summaries.items():
        if summary.return_rows > 0:
            summary.avg_return = return_sums[pair_id] / summary.return_rows


def quote_state_key(row: dict[str, object]) -> tuple[object, ...]:
    return (
        row.get("kalshi_yes_bid"),
        row.get("kalshi_yes_ask"),
        row.get("kalshi_no_bid"),
        row.get("kalshi_no_ask"),
        row.get("polymarket_yes_bid"),
        row.get("polymarket_yes_ask"),
        row.get("polymarket_no_bid"),
        row.get("polymarket_no_ask"),
        row.get("kalshi_yes_ask_size"),
        row.get("kalshi_no_ask_size"),
        row.get("polymarket_yes_ask_size"),
        row.get("polymarket_no_ask_size"),
    )


def accumulate_quote_state_metrics(
    quotes_dir: Path,
    summaries: dict[str, PairSummary],
) -> dict[str, dict[str, int]]:
    quote_states: dict[str, set[tuple[object, ...]]] = defaultdict(set)
    previous_state: dict[str, tuple[object, ...] | None] = {}
    run_ids: dict[str, int] = defaultdict(int)
    snapshot_pair_runs: dict[str, dict[str, int]] = {}
    for quote_path in sorted(quotes_dir.glob("tracked_pair_quotes_*.jsonl")):
        snapshot_pair_runs[quote_path.name] = {}
        with quote_path.open("r", encoding="utf-8") as f:
            for line in f:
                text = line.strip()
                if not text:
                    continue
                row = json.loads(text)
                pair_id = str(row.get("pair_id", ""))
                if not pair_id:
                    continue
                summary = summaries.setdefault(pair_id, PairSummary(pair_id=pair_id))
                summary.snapshots_seen += 1
                state = quote_state_key(row)
                quote_states[pair_id].add(state)
                if previous_state.get(pair_id) != state:
                    run_ids[pair_id] += 1
                    previous_state[pair_id] = state
                snapshot_pair_runs[quote_path.name][pair_id] = run_ids[pair_id]
    for pair_id, summary in summaries.items():
        summary.unique_quote_states = len(quote_states[pair_id])
        summary.effective_state_runs = run_ids[pair_id]
    return snapshot_pair_runs


def accumulate_effective_execution_metrics(
    paper_ledger_path: Path,
    snapshot_pair_runs: dict[str, dict[str, int]],
    summaries: dict[str, PairSummary],
) -> None:
    executed_runs: dict[str, set[int]] = defaultdict(set)
    filled_runs: dict[str, set[int]] = defaultdict(set)
    missed_runs: dict[str, set[int]] = defaultdict(set)
    if not paper_ledger_path.exists():
        return
    with paper_ledger_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pair_id = str(row.get("pair_id") or "")
            if not pair_id:
                continue
            quote_snapshot = os.path.basename(str(row.get("quote_snapshot") or ""))
            run_id = snapshot_pair_runs.get(quote_snapshot, {}).get(pair_id)
            if run_id is None:
                continue
            summaries.setdefault(pair_id, PairSummary(pair_id=pair_id))
            executed_runs[pair_id].add(run_id)
            status = str(row.get("status") or "")
            if status == "filled":
                filled_runs[pair_id].add(run_id)
            else:
                missed_runs[pair_id].add(run_id)
    for pair_id, summary in summaries.items():
        summary.effective_execution_runs = len(executed_runs[pair_id])
        summary.effective_fill_runs = len(filled_runs[pair_id])
        summary.effective_miss_runs = len(missed_runs[pair_id])


def accumulate_effective_return_metrics(
    returns_path: Path,
    snapshot_pair_runs: dict[str, dict[str, int]],
    summaries: dict[str, PairSummary],
) -> None:
    run_return_sums: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    run_return_counts: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    with returns_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            note = parse_note(row.get("note", ""))
            pair_id = note.get("pair_id", "").strip()
            if not pair_id:
                continue
            run_id = str(row.get("run_id") or "").strip()
            quote_snapshot = f"tracked_pair_quotes_{run_id}.jsonl"
            effective_run_id = snapshot_pair_runs.get(quote_snapshot, {}).get(pair_id)
            if effective_run_id is None:
                continue
            summaries.setdefault(pair_id, PairSummary(pair_id=pair_id))
            run_return_sums[pair_id][effective_run_id] += float(row.get("net_return", 0.0) or 0.0)
            run_return_counts[pair_id][effective_run_id] += 1
    for pair_id, summary in summaries.items():
        run_means = [
            run_return_sums[pair_id][run_id] / run_return_counts[pair_id][run_id]
            for run_id in sorted(run_return_sums[pair_id])
            if run_return_counts[pair_id][run_id] > 0
        ]
        summary.effective_return_runs = len(run_means)
        if run_means:
            summary.avg_effective_return = sum(run_means) / len(run_means)


def classify(summary: PairSummary) -> tuple[str, str]:
    effective_fill_rate = (
        summary.effective_fill_runs / summary.effective_execution_runs if summary.effective_execution_runs else 0.0
    )
    if summary.effective_execution_runs == 0 and summary.effective_return_runs <= 1:
        return "drop_from_shortlist", "no current fast-loop support"
    if summary.effective_return_runs > 0 and summary.avg_effective_return <= 0.0:
        return "drop_from_shortlist", "non-positive realized average return after deduping repeated states"
    if summary.effective_fill_runs >= 25 and effective_fill_rate >= 0.85 and summary.avg_effective_return > 0.0:
        if summary.unique_quote_states <= 3 and summary.snapshots_seen >= 50:
            return "review_mapping_or_staleness", "persistent edge with very low quote-state variation"
        return "keep_tracking", "persistent candidate with strong deduped fill survival"
    if summary.effective_fill_runs >= 8 and effective_fill_rate >= 0.75 and summary.avg_effective_return > 0.0:
        return "collect_more_data", "promising after deduping repeated states, but still thin"
    return "drop_from_shortlist", "too little support relative to active shortlist pressure"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize pair-lock fast-loop evidence by pair.")
    parser.add_argument("--source-triage", default=str(ROOT / "data" / "reports" / "cross_venue_pair_lock_triage.json"))
    parser.add_argument("--events", default=str(ROOT / "data" / "reports" / "pair_lock_watcher_events.jsonl"))
    parser.add_argument("--opportunities", default=str(ROOT / "data" / "reports" / "pair_lock_watcher_opportunities.jsonl"))
    parser.add_argument("--returns", default=str(ROOT / "data" / "returns" / "tracked_pair_fast_loop_returns.csv"))
    parser.add_argument("--quotes-dir", default=str(ROOT / "data" / "quotes"))
    parser.add_argument(
        "--paper-ledger",
        default=str(ROOT / "data" / "reports" / "tracked_pair_paper_execution.csv"),
    )
    parser.add_argument("--out-json", default=str(ROOT / "data" / "reports" / "pair_lock_fast_loop_analysis.json"))
    parser.add_argument("--out-csv", default=str(ROOT / "data" / "reports" / "pair_lock_fast_loop_pair_summary.csv"))
    parser.add_argument(
        "--quote-diagnostics",
        default=str(ROOT / "data" / "reports" / "pair_lock_quote_diagnostics.json"),
    )
    parser.add_argument(
        "--refined-triage-out",
        default=str(ROOT / "data" / "reports" / "cross_venue_pair_lock_triage_refined.json"),
    )
    parser.add_argument("--scout-top-n", type=int, default=3)
    parser.add_argument(
        "--scout-out",
        default=str(ROOT / "data" / "reports" / "cross_venue_pair_lock_scout_candidates.json"),
    )
    parser.add_argument("--max-active-pairs", type=int, default=2)
    args = parser.parse_args()

    source_triage_path = Path(args.source_triage)
    events_path = Path(args.events)
    opportunities_path = Path(args.opportunities)
    returns_path = Path(args.returns)
    quotes_dir = Path(args.quotes_dir)
    paper_ledger_path = Path(args.paper_ledger)
    out_json = Path(args.out_json)
    out_csv = Path(args.out_csv)
    quote_diagnostics_path = Path(args.quote_diagnostics)
    refined_triage_out = Path(args.refined_triage_out)
    scout_out = Path(args.scout_out)

    summaries, cycle_count = accumulate_event_metrics(events_path)
    accumulate_opportunity_metrics(opportunities_path, summaries)
    accumulate_return_metrics(returns_path, summaries)
    snapshot_pair_runs = accumulate_quote_state_metrics(quotes_dir, summaries)
    accumulate_effective_execution_metrics(paper_ledger_path, snapshot_pair_runs, summaries)
    accumulate_effective_return_metrics(returns_path, snapshot_pair_runs, summaries)
    quote_diagnostics: dict[str, dict[str, object]] = {}
    if quote_diagnostics_path.exists():
        payload = json.loads(quote_diagnostics_path.read_text(encoding="utf-8"))
        for row in payload.get("pair_rows", []):
            if isinstance(row, dict) and row.get("pair_id"):
                quote_diagnostics[str(row["pair_id"])] = row

    rows = []
    for summary in summaries.values():
        summary.recommendation, summary.recommendation_reason = classify(summary)
        row = asdict(summary)
        row["fill_rate"] = summary.fill_count / summary.candidate_cycles if summary.candidate_cycles else 0.0
        row["effective_fill_rate"] = (
            summary.effective_fill_runs / summary.effective_execution_runs if summary.effective_execution_runs else 0.0
        )
        diagnostics = quote_diagnostics.get(summary.pair_id, {})
        row["quote_stale_risk"] = diagnostics.get("stale_risk", "")
        row["quote_stale_reason"] = diagnostics.get("stale_reason", "")
        row["quote_longest_identical_state_run"] = diagnostics.get("longest_identical_state_run", 0)
        row["quote_max_same_book_timestamp_run"] = diagnostics.get("max_consecutive_same_book_timestamp", 0)
        if diagnostics.get("stale_risk") == "review_now":
            row["recommendation"] = "review_mapping_or_staleness"
            row["recommendation_reason"] = f"quote diagnostics flagged review_now: {diagnostics.get('stale_reason', 'unknown')}"
        rows.append(row)
    rows.sort(
        key=lambda row: (
            row["effective_fill_runs"],
            row["effective_execution_runs"],
            row["avg_effective_return"],
            row["fill_count"],
            row["candidate_cycles"],
        ),
        reverse=True,
    )

    total_fills = sum(row["fill_count"] for row in rows)
    total_effective_fills = sum(row["effective_fill_runs"] for row in rows)
    dominant_pair = rows[0]["pair_id"] if rows else ""
    dominant_fill_share = (rows[0]["fill_count"] / total_fills) if rows and total_fills else 0.0
    dominant_effective_fill_share = (rows[0]["effective_fill_runs"] / total_effective_fills) if rows and total_effective_fills else 0.0
    keep_pairs = [row["pair_id"] for row in rows if row["recommendation"] == "keep_tracking"]
    active_keep_pairs = keep_pairs[: args.max_active_pairs] if args.max_active_pairs > 0 else keep_pairs
    collect_pairs = [row["pair_id"] for row in rows if row["recommendation"] == "collect_more_data"]
    drop_pairs = [row["pair_id"] for row in rows if row["recommendation"] == "drop_from_shortlist"]
    review_pairs = [row["pair_id"] for row in rows if row["recommendation"] == "review_mapping_or_staleness"]
    payload = {
        "generated_from": {
            "source_triage": str(source_triage_path),
            "events": str(events_path),
            "opportunities": str(opportunities_path),
            "returns": str(returns_path),
            "quotes_dir": str(quotes_dir),
        },
        "summary": {
            "total_cycles": cycle_count,
            "tracked_pairs": len(rows),
            "total_fills": total_fills,
            "total_effective_fills": total_effective_fills,
            "dominant_pair_id": dominant_pair,
            "dominant_fill_share": dominant_fill_share,
            "dominant_effective_fill_share": dominant_effective_fill_share,
            "active_pair_count": len(active_keep_pairs),
        },
        "recommended_keep_pairs": keep_pairs,
        "recommended_active_pairs": active_keep_pairs,
        "recommended_collect_more_pairs": collect_pairs,
        "recommended_review_pairs": review_pairs,
        "recommended_drop_pairs": drop_pairs,
        "pair_rows": rows,
    }
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["pair_id"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    if source_triage_path.exists():
        source_triage = json.loads(source_triage_path.read_text(encoding="utf-8"))
        selected_candidates = source_triage.get("selected_candidates", [])
        if isinstance(selected_candidates, list):
            selected_by_id = {str(row.get("pair_id")): row for row in selected_candidates if isinstance(row, dict)}
            refined_candidates = []
            for pair_id in active_keep_pairs:
                source_row = dict(selected_by_id.get(pair_id, {"pair_id": pair_id}))
                source_row["recommendation"] = "start_paper_tracking"
                source_row["analysis_recommendation"] = "keep_tracking"
                source_row["analysis_source"] = str(out_json)
                refined_candidates.append(source_row)
            refined_payload = dict(source_triage)
            refined_payload["generated_at_utc"] = datetime.now(UTC).isoformat()
            refined_payload["analysis_report"] = str(out_json)
            refined_payload["selected_candidates"] = refined_candidates
            refined_payload["top_n"] = len(refined_candidates)
            refined_payload["logged_rows"] = len(refined_candidates)
            refined_triage_out.write_text(json.dumps(refined_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            scout_candidates = []
            for row in selected_candidates:
                if not isinstance(row, dict):
                    continue
                pair_id = str(row.get("pair_id") or "")
                recommendation = str(row.get("recommendation") or "")
                if not pair_id or pair_id in active_keep_pairs:
                    continue
                if recommendation not in {
                    "start_paper_tracking",
                    "collect_more_paper_evidence",
                    "eligible_for_paper_review",
                }:
                    continue
                scout_row = dict(row)
                scout_row["analysis_recommendation"] = "scout_sweep"
                scout_row["analysis_source"] = str(out_json)
                scout_candidates.append(scout_row)

            scout_candidates.sort(
                key=lambda row: (
                    1 if str(row.get("recommendation")) == "start_paper_tracking" else 0,
                    float(row.get("best_lock_edge") or 0.0),
                    float(row.get("mean_abs_mid_gap") or 0.0),
                ),
                reverse=True,
            )
            scout_payload = {
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "source_triage": str(source_triage_path),
                "analysis_report": str(out_json),
                "scout_top_n": args.scout_top_n,
                "selected_candidates": scout_candidates[: args.scout_top_n],
            }
            scout_out.write_text(json.dumps(scout_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
