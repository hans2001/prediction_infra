#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pred_infra.eval.integrity import build_integrity_report  # noqa: E402


def load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    aggregate = report["aggregate"]
    lines = [
        "# Integrity Report",
        "",
        f"- generated_at_utc: {report['generated_at_utc']}",
        f"- max_age_hours: {report['max_age_hours']}",
        f"- snapshot_count: {report['snapshot_count']}",
        "",
        "## Aggregate",
        f"- rows: {aggregate['rows']}",
        f"- missing_required_rows: {aggregate['missing_required_rows']}",
        f"- duplicate_rows: {aggregate['duplicate_rows']}",
        f"- out_of_bounds_price_rows: {aggregate['out_of_bounds_price_rows']}",
        f"- stale_rows: {aggregate['stale_rows']}",
        f"- parse_error_rows: {aggregate['parse_error_rows']}",
        f"- max_snapshot_age_hours: {aggregate['max_snapshot_age_hours']:.3f}",
        f"- pass: {aggregate['pass']}",
        "",
        "## By Source",
    ]
    for source, stats in report["by_source"].items():
        lines.extend(
            [
                f"### {source}",
                f"- rows: {stats['rows']}",
                f"- missing_required_rows: {stats['missing_required_rows']}",
                f"- duplicate_rows: {stats['duplicate_rows']}",
                f"- out_of_bounds_price_rows: {stats['out_of_bounds_price_rows']}",
                f"- stale_rows: {stats['stale_rows']}",
                f"- parse_error_rows: {stats['parse_error_rows']}",
                f"- max_snapshot_age_hours: {stats['max_snapshot_age_hours']:.3f}",
                f"- pass: {stats['pass']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build data integrity report from normalized snapshots.")
    parser.add_argument("--normalized-dir", default=str(ROOT / "data" / "normalized"))
    parser.add_argument("--out-dir", default=str(ROOT / "data" / "reports"))
    parser.add_argument("--max-age-hours", type=float, default=24.0)
    args = parser.parse_args()

    normalized_dir = Path(args.normalized_dir)
    out_dir = Path(args.out_dir)
    files = sorted(normalized_dir.glob("*.jsonl"))
    if not files:
        print("no normalized jsonl files found")
        return 1

    rows: list[dict[str, Any]] = []
    for path in files:
        rows.extend(load_jsonl_rows(path))

    report = build_integrity_report(rows, max_age_hours=args.max_age_hours, now_utc=datetime.now(UTC))
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"integrity_report_{stamp}.json"
    md_path = out_dir / f"integrity_report_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    write_markdown(md_path, report)

    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(f"aggregate_pass={report['aggregate']['pass']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
