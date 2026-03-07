from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class SnapshotMeta:
    source: str
    captured_at_utc: datetime
    endpoint: str
    count: int


@dataclass(slots=True)
class Opportunity:
    strategy: str
    market: str
    edge_bps: float
    details: dict[str, Any]
