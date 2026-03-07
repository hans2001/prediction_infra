from __future__ import annotations

import csv
import subprocess
from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "strategy", "net_return"])
        writer.writeheader()
        writer.writerows(rows)


def test_upsert_returns_history_dedupes(tmp_path: Path) -> None:
    input_csv = tmp_path / "input.csv"
    history_csv = tmp_path / "history.csv"

    rows = [
        {"timestamp": "2026-01-01T00:00:00Z", "strategy": "mm_v1", "net_return": "0.001"},
        {"timestamp": "2026-01-02T00:00:00Z", "strategy": "mm_v1", "net_return": "0.002"},
    ]
    _write_csv(input_csv, rows)

    cmd = [
        "python3",
        "scripts/upsert_returns_history.py",
        "--input-csv",
        str(input_csv),
        "--history",
        str(history_csv),
        "--default-source",
        "paper",
    ]
    subprocess.run(cmd, check=True, cwd=Path(__file__).resolve().parents[1])
    subprocess.run(cmd, check=True, cwd=Path(__file__).resolve().parents[1])

    with history_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        output = list(reader)
    assert len(output) == 2
