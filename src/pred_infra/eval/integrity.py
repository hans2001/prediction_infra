from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from typing import Any, Iterable

REQUIRED_FIELDS = ("source", "snapshot_ts", "market_id", "status")
PRICE_FIELDS = ("yes_bid", "yes_ask", "no_bid", "no_ask", "yes_price", "no_price", "last_price")


@dataclass(slots=True)
class IntegrityStats:
    rows: int = 0
    missing_required_rows: int = 0
    duplicate_rows: int = 0
    out_of_bounds_price_rows: int = 0
    stale_rows: int = 0
    parse_error_rows: int = 0
    max_snapshot_age_hours: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["missing_required_rate"] = self._rate(self.missing_required_rows)
        data["duplicate_rate"] = self._rate(self.duplicate_rows)
        data["out_of_bounds_price_rate"] = self._rate(self.out_of_bounds_price_rows)
        data["stale_rate"] = self._rate(self.stale_rows)
        data["parse_error_rate"] = self._rate(self.parse_error_rows)
        data["pass"] = (
            self.missing_required_rows == 0
            and self.duplicate_rows == 0
            and self.out_of_bounds_price_rows == 0
            and self.parse_error_rows == 0
        )
        return data

    def _rate(self, numerator: int) -> float:
        if self.rows == 0:
            return 0.0
        return numerator / self.rows


def _parse_snapshot_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    variants = (value, value.replace("Z", "+00:00"))
    for raw in variants:
        try:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except ValueError:
            continue
    return None


def _has_missing_required(row: dict[str, Any]) -> bool:
    for key in REQUIRED_FIELDS:
        value = row.get(key)
        if value is None or value == "":
            return True
    return False


def _has_out_of_bounds_price(row: dict[str, Any]) -> bool:
    for key in PRICE_FIELDS:
        value = row.get(key)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return True
        if not 0.0 <= numeric <= 1.0:
            return True
    return False


def build_integrity_report(
    rows: Iterable[dict[str, Any]],
    max_age_hours: float = 24.0,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    current = now_utc.astimezone(UTC) if now_utc is not None else datetime.now(UTC)
    by_source: dict[str, IntegrityStats] = {}
    aggregate = IntegrityStats()
    seen_keys: set[tuple[str, str, str]] = set()
    snapshot_ages: Counter[str] = Counter()

    def get_stats(source: str) -> IntegrityStats:
        stats = by_source.get(source)
        if stats is None:
            stats = IntegrityStats()
            by_source[source] = stats
        return stats

    for row in rows:
        source = str(row.get("source", "unknown") or "unknown")
        stats = get_stats(source)
        aggregate.rows += 1
        stats.rows += 1

        missing_required = _has_missing_required(row)
        if missing_required:
            aggregate.missing_required_rows += 1
            stats.missing_required_rows += 1

        market_id = str(row.get("market_id", ""))
        snapshot_ts = str(row.get("snapshot_ts", ""))
        dedupe_key = (source, snapshot_ts, market_id)
        if dedupe_key in seen_keys:
            aggregate.duplicate_rows += 1
            stats.duplicate_rows += 1
        else:
            seen_keys.add(dedupe_key)

        out_of_bounds = _has_out_of_bounds_price(row)
        if out_of_bounds:
            aggregate.out_of_bounds_price_rows += 1
            stats.out_of_bounds_price_rows += 1

        parsed_ts = _parse_snapshot_ts(row.get("snapshot_ts"))
        if parsed_ts is None:
            aggregate.parse_error_rows += 1
            stats.parse_error_rows += 1
        else:
            age_hours = max(0.0, (current - parsed_ts).total_seconds() / 3600.0)
            snapshot_ages[row["snapshot_ts"]] += 1
            stats.max_snapshot_age_hours = max(stats.max_snapshot_age_hours, age_hours)
            aggregate.max_snapshot_age_hours = max(aggregate.max_snapshot_age_hours, age_hours)
            if age_hours > max_age_hours:
                aggregate.stale_rows += 1
                stats.stale_rows += 1

    return {
        "generated_at_utc": current.isoformat(),
        "max_age_hours": max_age_hours,
        "aggregate": aggregate.to_dict(),
        "by_source": {source: stats.to_dict() for source, stats in sorted(by_source.items())},
        "snapshot_count": len(snapshot_ages),
    }
