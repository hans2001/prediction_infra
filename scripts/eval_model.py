#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pred_infra.eval.metrics import brier_score, log_loss, summarize_trade_ledger  # noqa: E402


def load_probs_and_outcomes(path: Path) -> tuple[list[float], list[int]]:
    probs: list[float] = []
    outcomes: list[int] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            probs.append(float(row["probability"]))
            outcomes.append(int(row["outcome"]))
    return probs, outcomes


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate model predictions and optional trade ledger.")
    parser.add_argument("--predictions", required=True, help="CSV with columns: probability,outcome")
    parser.add_argument(
        "--ledger",
        default="",
        help="Optional trade ledger CSV with columns: side,entry_price,exit_price,qty,fees",
    )
    args = parser.parse_args()

    pred_path = Path(args.predictions)
    probs, outcomes = load_probs_and_outcomes(pred_path)
    print(f"brier_score={brier_score(probs, outcomes):.6f}")
    print(f"log_loss={log_loss(probs, outcomes):.6f}")

    if args.ledger:
        summary = summarize_trade_ledger(args.ledger)
        print(f"trades={summary.trades}")
        print(f"gross_pnl={summary.gross_pnl:.6f}")
        print(f"fees={summary.fees:.6f}")
        print(f"net_pnl={summary.net_pnl:.6f}")
        print(f"avg_net_per_trade={summary.avg_net_per_trade:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
