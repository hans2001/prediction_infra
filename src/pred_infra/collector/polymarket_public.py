from __future__ import annotations

from typing import Any

from .http import get_json

POLYMARKET_GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"


def fetch_markets(limit: int = 200, active: bool = True, closed: bool = False) -> list[dict[str, Any]]:
    return get_json(
        POLYMARKET_GAMMA_MARKETS,
        params={"limit": limit, "active": str(active).lower(), "closed": str(closed).lower()},
    )
