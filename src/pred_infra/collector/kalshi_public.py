from __future__ import annotations

from typing import Any

from .http import get_json

# Kalshi docs use this base in examples for public market data.
KALSHI_PUBLIC_BASE = "https://api.elections.kalshi.com/trade-api/v2"


def fetch_markets(limit: int = 200, status: str = "open") -> dict[str, Any]:
    return get_json(
        f"{KALSHI_PUBLIC_BASE}/markets",
        params={"limit": limit, "status": status},
    )


def fetch_orderbook(ticker: str, depth: int = 10) -> dict[str, Any]:
    return get_json(
        f"{KALSHI_PUBLIC_BASE}/markets/{ticker}/orderbook",
        params={"depth": depth},
    )
