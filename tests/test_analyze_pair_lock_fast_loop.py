from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_analyze_pair_lock_fast_loop_uses_effective_runs_for_active_shortlist(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_triage = tmp_path / "cross_venue_pair_lock_triage.json"
    events_path = tmp_path / "pair_lock_watcher_events.jsonl"
    opportunities_path = tmp_path / "pair_lock_watcher_opportunities.jsonl"
    returns_path = tmp_path / "tracked_pair_fast_loop_returns.csv"
    quotes_dir = tmp_path / "quotes"
    paper_ledger_path = tmp_path / "tracked_pair_paper_execution.csv"
    out_json = tmp_path / "pair_lock_fast_loop_analysis.json"
    out_csv = tmp_path / "pair_lock_fast_loop_pair_summary.csv"
    refined_triage_out = tmp_path / "cross_venue_pair_lock_triage_refined.json"
    scout_out = tmp_path / "cross_venue_pair_lock_scout_candidates.json"

    selected_candidates = [
        {"pair_id": "pair_alpha", "recommendation": "start_paper_tracking", "best_lock_edge": 0.01},
        {"pair_id": "pair_beta", "recommendation": "start_paper_tracking", "best_lock_edge": 0.009},
        {"pair_id": "pair_repeat", "recommendation": "start_paper_tracking", "best_lock_edge": 0.011},
    ]
    source_triage.write_text(
        json.dumps({"selected_candidates": selected_candidates, "top_n": 3}, indent=2) + "\n",
        encoding="utf-8",
    )

    event_rows: list[dict[str, object]] = []
    opportunity_rows: list[dict[str, object]] = []
    paper_rows: list[dict[str, object]] = []
    return_rows: list[dict[str, object]] = []

    for i in range(30):
        run_id = f"20260311T000{i:02d}Z"
        quote_name = f"tracked_pair_quotes_{run_id}.jsonl"
        timestamp = f"2026-03-11T00:00:{i:02d}+00:00"
        quote_rows = [
            {
                "timestamp_utc": timestamp,
                "pair_id": "pair_alpha",
                "kalshi_yes_bid": 0.1 + i * 0.001,
                "kalshi_yes_ask": 0.11 + i * 0.001,
                "kalshi_no_bid": 0.88 - i * 0.001,
                "kalshi_no_ask": 0.89 - i * 0.001,
                "polymarket_yes_bid": 0.09 + i * 0.001,
                "polymarket_yes_ask": 0.1 + i * 0.001,
                "polymarket_no_bid": 0.89 - i * 0.001,
                "polymarket_no_ask": 0.9 - i * 0.001,
                "kalshi_yes_ask_size": 100 + i,
                "kalshi_no_ask_size": 100 + i,
                "polymarket_yes_ask_size": 50 + i,
                "polymarket_no_ask_size": 50 + i,
            },
            {
                "timestamp_utc": timestamp,
                "pair_id": "pair_beta",
                "kalshi_yes_bid": 0.2 + i * 0.001,
                "kalshi_yes_ask": 0.21 + i * 0.001,
                "kalshi_no_bid": 0.78 - i * 0.001,
                "kalshi_no_ask": 0.79 - i * 0.001,
                "polymarket_yes_bid": 0.19 + i * 0.001,
                "polymarket_yes_ask": 0.2 + i * 0.001,
                "polymarket_no_bid": 0.79 - i * 0.001,
                "polymarket_no_ask": 0.8 - i * 0.001,
                "kalshi_yes_ask_size": 120 + i,
                "kalshi_no_ask_size": 120 + i,
                "polymarket_yes_ask_size": 60 + i,
                "polymarket_no_ask_size": 60 + i,
            },
            {
                "timestamp_utc": timestamp,
                "pair_id": "pair_repeat",
                "kalshi_yes_bid": 0.3,
                "kalshi_yes_ask": 0.31,
                "kalshi_no_bid": 0.68,
                "kalshi_no_ask": 0.69,
                "polymarket_yes_bid": 0.29,
                "polymarket_yes_ask": 0.3,
                "polymarket_no_bid": 0.69,
                "polymarket_no_ask": 0.7,
                "kalshi_yes_ask_size": 140,
                "kalshi_no_ask_size": 140,
                "polymarket_yes_ask_size": 70,
                "polymarket_no_ask_size": 70,
            },
        ]
        write_jsonl(quotes_dir / quote_name, quote_rows)

        event_rows.append(
            {
                "timestamp_utc": timestamp,
                "execution_candidates": [
                    {"pair_id": "pair_alpha"},
                    {"pair_id": "pair_beta"},
                    {"pair_id": "pair_repeat"},
                ],
                "filled_results": [
                    {"pair_id": "pair_alpha"},
                    {"pair_id": "pair_beta"},
                    {"pair_id": "pair_repeat"},
                ],
            }
        )
        for pair_id, edge, cost in (
            ("pair_alpha", 0.010, 0.990),
            ("pair_beta", 0.008, 0.992),
            ("pair_repeat", 0.011, 0.989),
        ):
            opportunity_rows.append({"pair_id": pair_id, "net_edge": edge, "total_cost": cost})
            paper_rows.append(
                {
                    "run_id": run_id,
                    "generated_at_utc": timestamp,
                    "quote_snapshot": str(quotes_dir / quote_name),
                    "pair_id": pair_id,
                    "label": pair_id,
                    "status": "filled",
                    "reason": "edge_survived_timeout",
                    "expected_total_cost": f"{cost:.6f}",
                    "realized_total_cost": f"{cost:.6f}",
                    "expected_net_edge": f"{edge:.6f}",
                    "realized_net_edge": f"{edge:.6f}",
                    "min_size_available": "25.000000",
                    "realized_min_size": "25.000000",
                }
            )
            return_rows.append(
                {
                    "timestamp": timestamp,
                    "strategy": f"pair_lock_{pair_id}",
                    "net_return": f"{edge:.6f}",
                    "source": "paper_fast_pair_lock",
                    "run_id": run_id,
                    "note": f"pair_id={pair_id}; expected_total_cost={cost:.6f}; realized_total_cost={cost:.6f}; realized_net_edge={edge:.6f}",
                }
            )

    write_jsonl(events_path, event_rows)
    write_jsonl(opportunities_path, opportunity_rows)
    write_csv(
        paper_ledger_path,
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
    write_csv(
        returns_path,
        ["timestamp", "strategy", "net_return", "source", "run_id", "note"],
        return_rows,
    )

    subprocess.run(
        [
            "python3",
            "scripts/analyze_pair_lock_fast_loop.py",
            "--source-triage",
            str(source_triage),
            "--events",
            str(events_path),
            "--opportunities",
            str(opportunities_path),
            "--returns",
            str(returns_path),
            "--quotes-dir",
            str(quotes_dir),
            "--paper-ledger",
            str(paper_ledger_path),
            "--out-json",
            str(out_json),
            "--out-csv",
            str(out_csv),
            "--refined-triage-out",
            str(refined_triage_out),
            "--scout-out",
            str(scout_out),
            "--max-active-pairs",
            "2",
        ],
        check=True,
        cwd=repo_root,
    )

    payload = json.loads(out_json.read_text(encoding="utf-8"))
    rows = {row["pair_id"]: row for row in payload["pair_rows"]}

    assert rows["pair_alpha"]["effective_fill_runs"] == 30
    assert rows["pair_beta"]["effective_fill_runs"] == 30
    assert rows["pair_repeat"]["effective_fill_runs"] == 1
    assert rows["pair_repeat"]["recommendation"] == "drop_from_shortlist"
    assert payload["recommended_keep_pairs"] == ["pair_alpha", "pair_beta"]
    assert payload["recommended_active_pairs"] == ["pair_alpha", "pair_beta"]

    refined = json.loads(refined_triage_out.read_text(encoding="utf-8"))
    assert [row["pair_id"] for row in refined["selected_candidates"]] == ["pair_alpha", "pair_beta"]

    scout = json.loads(scout_out.read_text(encoding="utf-8"))
    assert [row["pair_id"] for row in scout["selected_candidates"]] == ["pair_repeat"]
