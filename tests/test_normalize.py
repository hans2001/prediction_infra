from pred_infra.collector.normalize import normalize_kalshi_payload, normalize_polymarket_payload


def test_normalize_kalshi_payload() -> None:
    payload = {
        "markets": [
            {
                "ticker": "KXTEST-1",
                "event_ticker": "KXEVENT-1",
                "title": "Test market",
                "status": "active",
                "close_time": "2026-03-31T12:00:00Z",
                "yes_bid_dollars": "0.41",
                "yes_ask_dollars": "0.43",
                "no_bid_dollars": "0.57",
                "no_ask_dollars": "0.59",
                "last_price_dollars": "0.42",
                "liquidity_dollars": "100.5",
                "volume": 1234,
                "updated_time": "2026-03-07T00:00:00Z",
            }
        ]
    }
    rows = normalize_kalshi_payload(payload, snapshot_ts="2026-03-07T17:00:00+00:00", raw_file="kalshi.json")
    assert len(rows) == 1
    row = rows[0]
    assert row["source"] == "kalshi"
    assert row["market_id"] == "KXTEST-1"
    assert row["yes_bid"] == 0.41
    assert row["yes_price"] == 0.42


def test_normalize_polymarket_payload() -> None:
    payload = [
        {
            "id": 123,
            "conditionId": "0xabc",
            "question": "Will X happen?",
            "active": True,
            "closed": False,
            "endDate": "2026-03-31T12:00:00Z",
            "bestBid": 0.2,
            "bestAsk": 0.25,
            "lastTradePrice": 0.23,
            "outcomes": ["Yes", "No"],
            "outcomePrices": ["0.23", "0.77"],
            "liquidity": 1000.0,
            "volume": 5000.0,
            "updatedAt": "2026-03-07T00:00:00Z",
        }
    ]
    rows = normalize_polymarket_payload(payload, snapshot_ts="2026-03-07T17:00:00+00:00", raw_file="poly.json")
    assert len(rows) == 1
    row = rows[0]
    assert row["source"] == "polymarket"
    assert row["market_id"] == "123"
    assert row["yes_price"] == 0.23
    assert row["no_price"] == 0.77
