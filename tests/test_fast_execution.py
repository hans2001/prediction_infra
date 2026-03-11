from pred_infra.strategy.cross_venue_parity import CrossVenueBinaryLockResult, VenueCostModel
from pred_infra.strategy.fast_execution import (
    ExecutionPolicy,
    select_execution_candidates,
    simulate_execution_on_next_snapshot,
    summarize_paper_execution,
)


def _result(
    *,
    pair_id: str = "pair1",
    status: str = "provable_lock",
    buy_yes_venue: str = "polymarket",
    buy_no_venue: str = "kalshi",
    total_cost: float | None = 0.998,
    net_edge: float | None = 0.002,
) -> CrossVenueBinaryLockResult:
    return CrossVenueBinaryLockResult(
        pair_id=pair_id,
        label="Test Pair",
        buy_yes_venue=buy_yes_venue,
        buy_no_venue=buy_no_venue,
        yes_market_id="Y1",
        no_market_id="N1",
        yes_ask=0.026,
        no_ask=0.97,
        adjusted_yes_cost=0.027,
        adjusted_no_cost=0.971,
        total_cost=total_cost,
        net_edge=net_edge,
        status=status,
        reason="test",
    )


def test_select_execution_candidates_requires_size_and_cost_gate() -> None:
    results = [_result()]
    quote_rows = {
        "pair1": {
            "timestamp_utc": "2026-03-11T00:00:10+00:00",
            "polymarket_yes_book_timestamp": "1773187205000",
            "polymarket_no_book_timestamp": "1773187205000",
            "polymarket_yes_ask_size": 25.0,
            "kalshi_no_ask_size": 30.0,
        }
    }
    candidates = select_execution_candidates(results, quote_rows, ExecutionPolicy(min_size=10.0, max_total_cost=0.999))
    assert len(candidates) == 1
    assert candidates[0].min_size_available == 25.0

    blocked = select_execution_candidates(results, quote_rows, ExecutionPolicy(min_size=40.0, max_total_cost=0.999))
    assert blocked == []


def test_simulate_execution_on_next_snapshot_marks_fill_when_edge_survives() -> None:
    candidates = select_execution_candidates(
        [_result()],
        {
            "pair1": {
                "timestamp_utc": "2026-03-11T00:00:10+00:00",
                "polymarket_yes_book_timestamp": "1773187205000",
                "polymarket_no_book_timestamp": "1773187205000",
                "polymarket_yes_ask_size": 25.0,
                "kalshi_no_ask_size": 30.0,
            }
        },
        ExecutionPolicy(min_size=10.0, max_total_cost=0.999),
    )
    next_rows = {
        "pair1": {
            "timestamp_utc": "2026-03-11T00:00:12+00:00",
            "polymarket_yes_book_timestamp": "1773187211000",
            "polymarket_no_book_timestamp": "1773187211000",
            "polymarket_yes_ask": 0.026,
            "kalshi_no_ask": 0.97,
            "polymarket_yes_ask_size": 20.0,
            "kalshi_no_ask_size": 50.0,
        }
    }
    results = simulate_execution_on_next_snapshot(
        candidates,
        next_rows,
        kalshi_costs=VenueCostModel(buy_slippage=0.001),
        polymarket_costs=VenueCostModel(buy_slippage=0.001),
        policy=ExecutionPolicy(min_size=10.0, max_total_cost=0.999),
    )
    assert len(results) == 1
    assert results[0].status == "filled"
    summary = summarize_paper_execution(results)
    assert summary["filled_count"] == 1


def test_simulate_execution_on_next_snapshot_marks_miss_when_edge_disappears() -> None:
    candidates = select_execution_candidates(
        [_result()],
        {
            "pair1": {
                "timestamp_utc": "2026-03-11T00:00:10+00:00",
                "polymarket_yes_book_timestamp": "1773187205000",
                "polymarket_no_book_timestamp": "1773187205000",
                "polymarket_yes_ask_size": 25.0,
                "kalshi_no_ask_size": 30.0,
            }
        },
        ExecutionPolicy(min_size=10.0, max_total_cost=0.999),
    )
    next_rows = {
        "pair1": {
            "timestamp_utc": "2026-03-11T00:00:12+00:00",
            "polymarket_yes_book_timestamp": "1773187211000",
            "polymarket_no_book_timestamp": "1773187211000",
            "polymarket_yes_ask": 0.03,
            "kalshi_no_ask": 0.98,
            "polymarket_yes_ask_size": 20.0,
            "kalshi_no_ask_size": 50.0,
        }
    }
    results = simulate_execution_on_next_snapshot(
        candidates,
        next_rows,
        kalshi_costs=VenueCostModel(buy_slippage=0.001),
        polymarket_costs=VenueCostModel(buy_slippage=0.001),
        policy=ExecutionPolicy(min_size=10.0, max_total_cost=0.999),
    )
    assert len(results) == 1
    assert results[0].status == "missed"
    assert results[0].reason == "edge_gone_on_next_snapshot"


def test_execution_gates_stale_books_and_size_decay() -> None:
    candidates = select_execution_candidates(
        [_result()],
        {
            "pair1": {
                "timestamp_utc": "2026-03-11T00:00:30+00:00",
                "polymarket_yes_book_timestamp": "1773187205000",
                "polymarket_no_book_timestamp": "1773187205000",
                "polymarket_yes_ask_size": 25.0,
                "kalshi_no_ask_size": 30.0,
            }
        },
        ExecutionPolicy(min_size=10.0, max_total_cost=0.999, max_polymarket_book_age_sec=20.0),
    )
    assert candidates == []

    fresh_candidates = select_execution_candidates(
        [_result()],
        {
            "pair1": {
                "timestamp_utc": "2026-03-11T00:00:10+00:00",
                "polymarket_yes_book_timestamp": "1773187205000",
                "polymarket_no_book_timestamp": "1773187205000",
                "polymarket_yes_ask_size": 25.0,
                "kalshi_no_ask_size": 30.0,
            }
        },
        ExecutionPolicy(min_size=10.0, max_total_cost=0.999, min_size_survival_ratio=0.8),
    )
    results = simulate_execution_on_next_snapshot(
        fresh_candidates,
        {
            "pair1": {
                "timestamp_utc": "2026-03-11T00:00:12+00:00",
                "polymarket_yes_book_timestamp": "1773187211000",
                "polymarket_no_book_timestamp": "1773187211000",
                "polymarket_yes_ask": 0.026,
                "kalshi_no_ask": 0.97,
                "polymarket_yes_ask_size": 12.0,
                "kalshi_no_ask_size": 50.0,
            }
        },
        kalshi_costs=VenueCostModel(buy_slippage=0.001),
        polymarket_costs=VenueCostModel(buy_slippage=0.001),
        policy=ExecutionPolicy(min_size=10.0, max_total_cost=0.999, min_size_survival_ratio=0.8),
    )
    assert results[0].status == "missed"
    assert results[0].reason == "size_decay_in_next_snapshot"
