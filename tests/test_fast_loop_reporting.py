from pred_infra.strategy.fast_execution import PaperExecutionCandidate, PaperExecutionResult
from pred_infra.strategy.fast_loop_reporting import (
    build_execution_candidate_rows,
    build_paper_execution_rows,
    build_returns_rows,
)


def test_build_execution_candidate_rows_serializes_expected_fields() -> None:
    rows = build_execution_candidate_rows(
        [
            PaperExecutionCandidate(
                pair_id="pair1",
                label="Pair 1",
                buy_yes_venue="polymarket",
                buy_no_venue="kalshi",
                expected_total_cost=0.998,
                expected_net_edge=0.002,
                min_size_available=12.0,
            )
        ],
        run_id="run1",
        generated_at_utc="2026-03-11T00:00:00+00:00",
        quote_snapshot="quotes.jsonl",
    )
    assert rows[0]["pair_id"] == "pair1"
    assert rows[0]["expected_total_cost"] == "0.998000"


def test_build_paper_execution_rows_and_returns_rows_only_emit_fills_for_returns() -> None:
    results = [
        PaperExecutionResult(
            pair_id="pair1",
            label="Pair 1",
            status="filled",
            reason="ok",
            expected_total_cost=0.998,
            realized_total_cost=0.998,
            expected_net_edge=0.002,
            realized_net_edge=0.002,
            min_size_available=1.0,
            realized_min_size=1.0,
        ),
        PaperExecutionResult(
            pair_id="pair2",
            label="Pair 2",
            status="missed",
            reason="gone",
            expected_total_cost=0.998,
            realized_total_cost=None,
            expected_net_edge=0.002,
            realized_net_edge=None,
            min_size_available=1.0,
            realized_min_size=None,
        ),
    ]
    paper_rows = build_paper_execution_rows(
        results,
        run_id="run1",
        generated_at_utc="2026-03-11T00:00:00+00:00",
        quote_snapshot="quotes.jsonl",
    )
    assert len(paper_rows) == 2
    returns_rows = build_returns_rows(results, timestamp_utc="2026-03-11T00:00:00+00:00", run_id="run1")
    assert len(returns_rows) == 1
    assert returns_rows[0]["strategy"] == "pair_lock_pair1"
    assert "quality_score=0.000000" in returns_rows[0]["note"]
