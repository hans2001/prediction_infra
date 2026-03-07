from datetime import UTC, datetime

from pred_infra.eval.integrity import build_integrity_report


def test_integrity_report_detects_issues() -> None:
    rows = [
        {
            "source": "kalshi",
            "snapshot_ts": "2026-03-07T00:00:00+00:00",
            "market_id": "A",
            "status": "active",
            "yes_bid": 0.4,
        },
        {
            "source": "kalshi",
            "snapshot_ts": "2026-03-07T00:00:00+00:00",
            "market_id": "A",
            "status": "active",
            "yes_bid": 1.2,
        },
        {
            "source": "polymarket",
            "snapshot_ts": "bad-ts",
            "market_id": "",
            "status": "active",
        },
    ]
    now = datetime(2026, 3, 8, 0, 0, tzinfo=UTC)
    report = build_integrity_report(rows, max_age_hours=1.0, now_utc=now)
    agg = report["aggregate"]
    assert agg["rows"] == 3
    assert agg["duplicate_rows"] == 1
    assert agg["out_of_bounds_price_rows"] == 1
    assert agg["missing_required_rows"] == 1
    assert agg["parse_error_rows"] == 1
