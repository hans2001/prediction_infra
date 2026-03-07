from __future__ import annotations

import json
from typing import Any

from pred_infra.common.schema import NormalizedMarket


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mid(a: float | None, b: float | None) -> float | None:
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return (a + b) / 2.0


def _parse_outcome_prices(outcomes_value: Any, prices_value: Any) -> tuple[float | None, float | None]:
    outcomes: list[str] = []
    prices: list[float] = []

    if isinstance(outcomes_value, str):
        try:
            parsed = json.loads(outcomes_value)
            if isinstance(parsed, list):
                outcomes = [str(x) for x in parsed]
        except json.JSONDecodeError:
            outcomes = []
    elif isinstance(outcomes_value, list):
        outcomes = [str(x) for x in outcomes_value]

    if isinstance(prices_value, str):
        try:
            parsed = json.loads(prices_value)
            if isinstance(parsed, list):
                prices = [float(x) for x in parsed]
        except (json.JSONDecodeError, ValueError, TypeError):
            prices = []
    elif isinstance(prices_value, list):
        parsed_prices: list[float] = []
        for item in prices_value:
            val = _to_float(item)
            if val is None:
                continue
            parsed_prices.append(val)
        prices = parsed_prices

    if not outcomes or not prices or len(outcomes) != len(prices):
        return None, None

    yes_price = None
    no_price = None
    for outcome, price in zip(outcomes, prices):
        key = outcome.strip().lower()
        if key == "yes":
            yes_price = price
        elif key == "no":
            no_price = price
    return yes_price, no_price


def normalize_kalshi_payload(payload: dict[str, Any], snapshot_ts: str, raw_file: str) -> list[dict[str, Any]]:
    markets = payload.get("markets", [])
    if not isinstance(markets, list):
        return []

    normalized: list[dict[str, Any]] = []
    for market in markets:
        if not isinstance(market, dict):
            continue
        yes_bid = _to_float(market.get("yes_bid_dollars"))
        yes_ask = _to_float(market.get("yes_ask_dollars"))
        no_bid = _to_float(market.get("no_bid_dollars"))
        no_ask = _to_float(market.get("no_ask_dollars"))
        last_price = _to_float(market.get("last_price_dollars"))
        yes_price = last_price if last_price is not None and 0.0 <= last_price <= 1.0 else _mid(yes_bid, yes_ask)
        no_price = _mid(no_bid, no_ask)

        record = NormalizedMarket(
            source="kalshi",
            snapshot_ts=snapshot_ts,
            market_id=str(market.get("ticker", "")),
            event_id=market.get("event_ticker"),
            title=market.get("title"),
            status=market.get("status"),
            close_time=market.get("close_time") or market.get("expiration_time"),
            updated_time=market.get("updated_time"),
            yes_bid=yes_bid,
            yes_ask=yes_ask,
            no_bid=no_bid,
            no_ask=no_ask,
            yes_price=yes_price,
            no_price=no_price,
            last_price=last_price,
            liquidity=_to_float(market.get("liquidity_dollars")),
            volume=_to_float(market.get("volume")),
            raw_file=raw_file,
        )
        normalized.append(record.to_dict())
    return normalized


def normalize_polymarket_payload(payload: list[dict[str, Any]], snapshot_ts: str, raw_file: str) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []

    normalized: list[dict[str, Any]] = []
    for market in payload:
        if not isinstance(market, dict):
            continue
        yes_price, no_price = _parse_outcome_prices(market.get("outcomes"), market.get("outcomePrices"))
        yes_bid = _to_float(market.get("bestBid"))
        yes_ask = _to_float(market.get("bestAsk"))
        last_price = _to_float(market.get("lastTradePrice"))
        event_id = market.get("conditionId") or market.get("questionID")

        record = NormalizedMarket(
            source="polymarket",
            snapshot_ts=snapshot_ts,
            market_id=str(market.get("id", "")),
            event_id=str(event_id) if event_id is not None else None,
            title=market.get("question"),
            status="closed" if market.get("closed") else "active" if market.get("active") else "inactive",
            close_time=market.get("endDate"),
            updated_time=market.get("updatedAt"),
            yes_bid=yes_bid,
            yes_ask=yes_ask,
            no_bid=None,
            no_ask=None,
            yes_price=yes_price,
            no_price=no_price,
            last_price=last_price,
            liquidity=_to_float(market.get("liquidity")),
            volume=_to_float(market.get("volume")),
            raw_file=raw_file,
        )
        normalized.append(record.to_dict())
    return normalized
