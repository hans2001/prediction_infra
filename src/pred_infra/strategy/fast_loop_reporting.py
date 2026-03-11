from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .fast_execution import PaperExecutionCandidate, PaperExecutionResult


def append_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def build_execution_candidate_rows(
    candidates: Iterable[PaperExecutionCandidate],
    *,
    run_id: str,
    generated_at_utc: str,
    quote_snapshot: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in candidates:
        rows.append(
            {
                "run_id": run_id,
                "generated_at_utc": generated_at_utc,
                "quote_snapshot": quote_snapshot,
                "pair_id": item.pair_id,
                "label": item.label,
                "buy_yes_venue": item.buy_yes_venue,
                "buy_no_venue": item.buy_no_venue,
                "expected_total_cost": f"{item.expected_total_cost:.6f}",
                "expected_net_edge": f"{item.expected_net_edge:.6f}",
                "min_size_available": f"{item.min_size_available:.6f}",
            }
        )
    return rows


def build_paper_execution_rows(
    results: Iterable[PaperExecutionResult],
    *,
    run_id: str,
    generated_at_utc: str,
    quote_snapshot: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in results:
        rows.append(
            {
                "run_id": run_id,
                "generated_at_utc": generated_at_utc,
                "quote_snapshot": quote_snapshot,
                "pair_id": item.pair_id,
                "label": item.label,
                "status": item.status,
                "reason": item.reason,
                "expected_total_cost": f"{item.expected_total_cost:.6f}",
                "realized_total_cost": "" if item.realized_total_cost is None else f"{item.realized_total_cost:.6f}",
                "expected_net_edge": f"{item.expected_net_edge:.6f}",
                "realized_net_edge": "" if item.realized_net_edge is None else f"{item.realized_net_edge:.6f}",
                "min_size_available": f"{item.min_size_available:.6f}",
                "realized_min_size": "" if item.realized_min_size is None else f"{item.realized_min_size:.6f}",
            }
        )
    return rows


def build_returns_rows(
    results: Iterable[PaperExecutionResult],
    *,
    timestamp_utc: str,
    strategy_prefix: str = "pair_lock",
    source: str = "paper_fast_pair_lock",
    run_id: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in results:
        if item.status != "filled" or item.realized_total_cost in {None, 0.0} or item.realized_net_edge is None:
            continue
        net_return = item.realized_net_edge / item.realized_total_cost
        rows.append(
            {
                "timestamp": timestamp_utc,
                "strategy": f"{strategy_prefix}_{item.pair_id}",
                "net_return": f"{net_return:.6f}",
                "source": source,
                "run_id": run_id,
                "note": (
                    f"pair_id={item.pair_id}; expected_total_cost={item.expected_total_cost:.6f}; "
                    f"realized_total_cost={item.realized_total_cost:.6f}; realized_net_edge={item.realized_net_edge:.6f}; "
                    f"realized_size_survival_ratio={(item.realized_size_survival_ratio or 0.0):.6f}; "
                    f"quality_score={item.quality_score:.6f}"
                ),
            }
        )
    return rows
