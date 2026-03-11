#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class PairDiagnostics:
    pair_id: str
    snapshots_seen: int = 0
    unique_quote_states: int = 0
    longest_identical_state_run: int = 0
    identical_state_share: float = 0.0
    longest_polymarket_book_age_sec: float = 0.0
    avg_polymarket_book_age_sec: float = 0.0
    max_consecutive_same_book_timestamp: int = 0
    first_timestamp_utc: str = ""
    last_timestamp_utc: str = ""
    stale_risk: str = ""
    stale_reason: str = ""


def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def parse_ms_timestamp(raw: object) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError:
        return None
    return datetime.fromtimestamp(value / 1000.0, tz=parse_iso("2026-01-01T00:00:00+00:00").tzinfo)


def classify(summary: PairDiagnostics) -> tuple[str, str]:
    if summary.snapshots_seen == 0:
        return "unknown", "no snapshots"
    if summary.longest_polymarket_book_age_sec > 120 or summary.max_consecutive_same_book_timestamp > 30:
        return "review_now", "book timestamp stayed unchanged for too long"
    if summary.identical_state_share > 0.95 and summary.unique_quote_states <= 5:
        return "review_now", "quote state changed too rarely relative to sample count"
    if summary.identical_state_share > 0.85:
        return "watch", "high repeated-state share"
    return "ok", "quote state variation looks plausible"


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose pair-lock quote staleness and repeated-state risk.")
    parser.add_argument("--quotes-dir", default=str(ROOT / "data" / "quotes"))
    parser.add_argument("--analysis-report", default=str(ROOT / "data" / "reports" / "pair_lock_fast_loop_analysis.json"))
    parser.add_argument("--out-json", default=str(ROOT / "data" / "reports" / "pair_lock_quote_diagnostics.json"))
    args = parser.parse_args()

    quotes_dir = Path(args.quotes_dir)
    analysis_report = Path(args.analysis_report)
    out_json = Path(args.out_json)

    keep_pairs: list[str] = []
    if analysis_report.exists():
        payload = json.loads(analysis_report.read_text(encoding="utf-8"))
        keep_pairs = list(payload.get("recommended_keep_pairs", []))

    state_sets: dict[str, set[tuple[object, ...]]] = defaultdict(set)
    summaries: dict[str, PairDiagnostics] = {pair_id: PairDiagnostics(pair_id=pair_id) for pair_id in keep_pairs}
    previous_state: dict[str, tuple[object, ...] | None] = defaultdict(lambda: None)
    previous_book_ts: dict[str, str] = defaultdict(str)
    current_identical_run: dict[str, int] = defaultdict(int)
    current_book_ts_run: dict[str, int] = defaultdict(int)
    identical_transitions: dict[str, int] = defaultdict(int)
    transition_count: dict[str, int] = defaultdict(int)
    book_age_sum: dict[str, float] = defaultdict(float)

    for quote_path in sorted(quotes_dir.glob("tracked_pair_quotes_*.jsonl")):
        with quote_path.open("r", encoding="utf-8") as f:
            for line in f:
                text = line.strip()
                if not text:
                    continue
                row = json.loads(text)
                pair_id = str(row.get("pair_id") or "")
                if keep_pairs and pair_id not in keep_pairs:
                    continue
                summary = summaries.setdefault(pair_id, PairDiagnostics(pair_id=pair_id))
                ts = str(row.get("timestamp_utc") or "")
                summary.snapshots_seen += 1
                if not summary.first_timestamp_utc:
                    summary.first_timestamp_utc = ts
                summary.last_timestamp_utc = ts
                state = (
                    row.get("kalshi_yes_bid"),
                    row.get("kalshi_yes_ask"),
                    row.get("kalshi_no_bid"),
                    row.get("kalshi_no_ask"),
                    row.get("polymarket_yes_bid"),
                    row.get("polymarket_yes_ask"),
                    row.get("polymarket_no_bid"),
                    row.get("polymarket_no_ask"),
                )
                state_sets[pair_id].add(state)
                if previous_state[pair_id] is not None:
                    transition_count[pair_id] += 1
                    if previous_state[pair_id] == state:
                        identical_transitions[pair_id] += 1
                        current_identical_run[pair_id] += 1
                    else:
                        current_identical_run[pair_id] = 1
                else:
                    current_identical_run[pair_id] = 1
                summary.longest_identical_state_run = max(summary.longest_identical_state_run, current_identical_run[pair_id])
                previous_state[pair_id] = state

                poly_yes_ts = str(row.get("polymarket_yes_book_timestamp") or "")
                poly_no_ts = str(row.get("polymarket_no_book_timestamp") or "")
                combined_book_ts = f"{poly_yes_ts}|{poly_no_ts}"
                if previous_book_ts[pair_id] == combined_book_ts:
                    current_book_ts_run[pair_id] += 1
                else:
                    current_book_ts_run[pair_id] = 1
                previous_book_ts[pair_id] = combined_book_ts
                summary.max_consecutive_same_book_timestamp = max(
                    summary.max_consecutive_same_book_timestamp,
                    current_book_ts_run[pair_id],
                )

                row_ts = parse_iso(ts) if ts else None
                yes_book_ts = parse_ms_timestamp(poly_yes_ts)
                if row_ts is not None and yes_book_ts is not None:
                    age_sec = max(0.0, (row_ts - yes_book_ts).total_seconds())
                    book_age_sum[pair_id] += age_sec
                    summary.longest_polymarket_book_age_sec = max(summary.longest_polymarket_book_age_sec, age_sec)

    rows = []
    for pair_id, summary in summaries.items():
        summary.unique_quote_states = len(state_sets[pair_id])
        if transition_count[pair_id] > 0:
            summary.identical_state_share = identical_transitions[pair_id] / transition_count[pair_id]
        if summary.snapshots_seen > 0:
            summary.avg_polymarket_book_age_sec = book_age_sum[pair_id] / summary.snapshots_seen
        summary.stale_risk, summary.stale_reason = classify(summary)
        rows.append(asdict(summary))
    rows.sort(key=lambda row: (row["stale_risk"], row["longest_identical_state_run"]), reverse=True)

    payload = {
        "generated_at_utc": datetime.now().astimezone().isoformat(),
        "source_analysis_report": str(analysis_report),
        "pair_rows": rows,
    }
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
