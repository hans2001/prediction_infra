from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping

from .cross_venue_parity import CrossVenueBinaryLockResult, VenueCostModel


@dataclass(slots=True)
class ExecutionPolicy:
    min_size: float = 10.0
    max_total_cost: float = 0.999
    timeout_iterations: int = 1
    min_size_survival_ratio: float = 0.6
    max_polymarket_book_age_sec: float = 20.0


@dataclass(slots=True)
class PaperExecutionCandidate:
    pair_id: str
    label: str
    buy_yes_venue: str
    buy_no_venue: str
    expected_total_cost: float
    expected_net_edge: float
    min_size_available: float
    polymarket_book_age_sec: float | None = None


@dataclass(slots=True)
class PaperExecutionResult:
    pair_id: str
    label: str
    status: str
    reason: str
    expected_total_cost: float
    realized_total_cost: float | None
    expected_net_edge: float
    realized_net_edge: float | None
    min_size_available: float
    realized_min_size: float | None
    realized_size_survival_ratio: float | None = None
    polymarket_book_age_sec: float | None = None
    quality_score: float = 0.0


def select_execution_candidates(
    results: Iterable[CrossVenueBinaryLockResult],
    quote_rows: Mapping[str, Mapping[str, object]],
    policy: ExecutionPolicy,
) -> list[PaperExecutionCandidate]:
    candidates: list[PaperExecutionCandidate] = []
    for item in results:
        if item.status != "provable_lock" or item.total_cost is None or item.net_edge is None:
            continue
        quote_row = quote_rows.get(item.pair_id)
        if not quote_row:
            continue
        book_age_sec = _polymarket_book_age_sec(quote_row)
        if book_age_sec is not None and book_age_sec > policy.max_polymarket_book_age_sec:
            continue
        min_size = _min_leg_size(item, quote_row)
        if min_size is None or min_size < policy.min_size:
            continue
        if item.total_cost > policy.max_total_cost:
            continue
        candidates.append(
            PaperExecutionCandidate(
                pair_id=item.pair_id,
                label=item.label,
                buy_yes_venue=item.buy_yes_venue,
                buy_no_venue=item.buy_no_venue,
                expected_total_cost=item.total_cost,
                expected_net_edge=item.net_edge,
                min_size_available=min_size,
                polymarket_book_age_sec=book_age_sec,
            )
        )
    candidates.sort(key=lambda item: (item.expected_net_edge, item.min_size_available), reverse=True)
    return candidates


def simulate_execution_on_next_snapshot(
    candidates: Iterable[PaperExecutionCandidate],
    next_quote_rows: Mapping[str, Mapping[str, object]],
    *,
    kalshi_costs: VenueCostModel,
    polymarket_costs: VenueCostModel,
    policy: ExecutionPolicy,
) -> list[PaperExecutionResult]:
    results: list[PaperExecutionResult] = []
    for candidate in candidates:
        next_row = next_quote_rows.get(candidate.pair_id)
        if not next_row:
            results.append(
                PaperExecutionResult(
                    pair_id=candidate.pair_id,
                    label=candidate.label,
                    status="missed",
                    reason="pair_missing_in_next_snapshot",
                    expected_total_cost=candidate.expected_total_cost,
                    realized_total_cost=None,
                    expected_net_edge=candidate.expected_net_edge,
                    realized_net_edge=None,
                    min_size_available=candidate.min_size_available,
                    realized_min_size=None,
                )
            )
            continue
        yes_ask = _ask_for_venue(next_row, candidate.buy_yes_venue, "yes")
        no_ask = _ask_for_venue(next_row, candidate.buy_no_venue, "no")
        yes_size = _ask_size_for_venue(next_row, candidate.buy_yes_venue, "yes")
        no_size = _ask_size_for_venue(next_row, candidate.buy_no_venue, "no")
        realized_min_size = _min_nullable(yes_size, no_size)
        realized_size_survival_ratio = (
            realized_min_size / candidate.min_size_available if realized_min_size is not None and candidate.min_size_available > 0 else None
        )
        book_age_sec = _polymarket_book_age_sec(next_row)
        if yes_ask is None or no_ask is None:
            results.append(
                PaperExecutionResult(
                    pair_id=candidate.pair_id,
                    label=candidate.label,
                    status="missed",
                    reason="missing_quote_in_next_snapshot",
                    expected_total_cost=candidate.expected_total_cost,
                    realized_total_cost=None,
                    expected_net_edge=candidate.expected_net_edge,
                    realized_net_edge=None,
                    min_size_available=candidate.min_size_available,
                    realized_min_size=realized_min_size,
                    realized_size_survival_ratio=realized_size_survival_ratio,
                    polymarket_book_age_sec=book_age_sec,
                )
            )
            continue
        if book_age_sec is not None and book_age_sec > policy.max_polymarket_book_age_sec:
            results.append(
                PaperExecutionResult(
                    pair_id=candidate.pair_id,
                    label=candidate.label,
                    status="missed",
                    reason="stale_polymarket_book_in_next_snapshot",
                    expected_total_cost=candidate.expected_total_cost,
                    realized_total_cost=None,
                    expected_net_edge=candidate.expected_net_edge,
                    realized_net_edge=None,
                    min_size_available=candidate.min_size_available,
                    realized_min_size=realized_min_size,
                    realized_size_survival_ratio=realized_size_survival_ratio,
                    polymarket_book_age_sec=book_age_sec,
                )
            )
            continue
        if realized_min_size is None or realized_min_size < policy.min_size:
            results.append(
                PaperExecutionResult(
                    pair_id=candidate.pair_id,
                    label=candidate.label,
                    status="missed",
                    reason="insufficient_size_in_next_snapshot",
                    expected_total_cost=candidate.expected_total_cost,
                    realized_total_cost=None,
                    expected_net_edge=candidate.expected_net_edge,
                    realized_net_edge=None,
                    min_size_available=candidate.min_size_available,
                    realized_min_size=realized_min_size,
                    realized_size_survival_ratio=realized_size_survival_ratio,
                    polymarket_book_age_sec=book_age_sec,
                )
            )
            continue
        if realized_size_survival_ratio is not None and realized_size_survival_ratio < policy.min_size_survival_ratio:
            results.append(
                PaperExecutionResult(
                    pair_id=candidate.pair_id,
                    label=candidate.label,
                    status="missed",
                    reason="size_decay_in_next_snapshot",
                    expected_total_cost=candidate.expected_total_cost,
                    realized_total_cost=None,
                    expected_net_edge=candidate.expected_net_edge,
                    realized_net_edge=None,
                    min_size_available=candidate.min_size_available,
                    realized_min_size=realized_min_size,
                    realized_size_survival_ratio=realized_size_survival_ratio,
                    polymarket_book_age_sec=book_age_sec,
                )
            )
            continue
        yes_cost = yes_ask + _buy_cost(candidate.buy_yes_venue, kalshi_costs, polymarket_costs)
        no_cost = no_ask + _buy_cost(candidate.buy_no_venue, kalshi_costs, polymarket_costs)
        realized_total_cost = yes_cost + no_cost
        realized_net_edge = 1.0 - realized_total_cost
        if realized_total_cost <= policy.max_total_cost:
            status = "filled"
            reason = "edge_survived_timeout"
        else:
            status = "missed"
            reason = "edge_gone_on_next_snapshot"
        quality_score = (
            max(realized_net_edge, 0.0) * min(1.0, realized_size_survival_ratio if realized_size_survival_ratio is not None else 0.0)
            if status == "filled" and realized_net_edge is not None
            else 0.0
        )
        results.append(
            PaperExecutionResult(
                pair_id=candidate.pair_id,
                label=candidate.label,
                status=status,
                reason=reason,
                expected_total_cost=candidate.expected_total_cost,
                realized_total_cost=realized_total_cost,
                expected_net_edge=candidate.expected_net_edge,
                realized_net_edge=realized_net_edge,
                min_size_available=candidate.min_size_available,
                realized_min_size=realized_min_size,
                realized_size_survival_ratio=realized_size_survival_ratio,
                polymarket_book_age_sec=book_age_sec,
                quality_score=quality_score,
            )
        )
    return results


def summarize_paper_execution(results: Iterable[PaperExecutionResult]) -> dict[str, object]:
    items = list(results)
    filled = [item for item in items if item.status == "filled"]
    return {
        "candidate_count": len(items),
        "filled_count": len(filled),
        "missed_count": sum(item.status == "missed" for item in items),
        "mean_realized_net_edge": (
            sum(item.realized_net_edge for item in filled if item.realized_net_edge is not None) / len(filled)
            if filled
            else None
        ),
        "mean_quality_score": (sum(item.quality_score for item in filled) / len(filled) if filled else None),
    }


def _min_leg_size(item: CrossVenueBinaryLockResult, row: Mapping[str, object]) -> float | None:
    yes_size = _ask_size_for_venue(row, item.buy_yes_venue, "yes")
    no_size = _ask_size_for_venue(row, item.buy_no_venue, "no")
    return _min_nullable(yes_size, no_size)


def _ask_for_venue(row: Mapping[str, object], venue: str, side: str) -> float | None:
    value = row.get(f"{venue}_{side}_ask")
    return float(value) if value is not None else None


def _ask_size_for_venue(row: Mapping[str, object], venue: str, side: str) -> float | None:
    value = row.get(f"{venue}_{side}_ask_size")
    return float(value) if value is not None else None


def _buy_cost(venue: str, kalshi_costs: VenueCostModel, polymarket_costs: VenueCostModel) -> float:
    costs = kalshi_costs if venue == "kalshi" else polymarket_costs
    return costs.buy_fee + costs.buy_slippage


def _min_nullable(lhs: float | None, rhs: float | None) -> float | None:
    if lhs is None or rhs is None:
        return None
    return min(lhs, rhs)


def _polymarket_book_age_sec(row: Mapping[str, object]) -> float | None:
    row_ts = _parse_iso(str(row.get("timestamp_utc") or ""))
    yes_book_ts = _parse_ms_timestamp(row.get("polymarket_yes_book_timestamp"))
    no_book_ts = _parse_ms_timestamp(row.get("polymarket_no_book_timestamp"))
    if row_ts is None:
        return None
    ages = [
        max(0.0, (row_ts - book_ts).total_seconds())
        for book_ts in (yes_book_ts, no_book_ts)
        if book_ts is not None
    ]
    return max(ages) if ages else None


def _parse_iso(raw: str) -> datetime | None:
    text = raw.strip()
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _parse_ms_timestamp(raw: object) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError:
        return None
    return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
