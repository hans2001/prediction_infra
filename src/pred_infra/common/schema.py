from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class NormalizedMarket:
    source: str
    snapshot_ts: str
    market_id: str
    event_id: str | None
    title: str | None
    status: str | None
    close_time: str | None
    updated_time: str | None
    yes_bid: float | None
    yes_ask: float | None
    no_bid: float | None
    no_ask: float | None
    yes_price: float | None
    no_price: float | None
    last_price: float | None
    liquidity: float | None
    volume: float | None
    raw_file: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
