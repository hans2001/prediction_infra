from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


def brier_score(probabilities: Iterable[float], outcomes: Iterable[int]) -> float:
    probs = list(probabilities)
    obs = list(outcomes)
    if not probs or len(probs) != len(obs):
        raise ValueError("probabilities and outcomes must be same non-zero length")
    return sum((p - y) ** 2 for p, y in zip(probs, obs)) / len(probs)


def log_loss(probabilities: Iterable[float], outcomes: Iterable[int], eps: float = 1e-12) -> float:
    probs = list(probabilities)
    obs = list(outcomes)
    if not probs or len(probs) != len(obs):
        raise ValueError("probabilities and outcomes must be same non-zero length")
    clipped = [min(max(p, eps), 1 - eps) for p in probs]
    return -sum(y * math.log(p) + (1 - y) * math.log(1 - p) for p, y in zip(clipped, obs)) / len(clipped)


def max_drawdown(equity_curve: Iterable[float]) -> float:
    peak = -math.inf
    max_dd = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        drawdown = peak - value
        max_dd = max(max_dd, drawdown)
    return max_dd


@dataclass(slots=True)
class PnLSummary:
    trades: int
    gross_pnl: float
    fees: float
    net_pnl: float
    avg_net_per_trade: float


def summarize_trade_ledger(csv_path: str | Path) -> PnLSummary:
    path = Path(csv_path)
    gross = 0.0
    fees = 0.0
    trades = 0
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = float(row["entry_price"])
            exit_price = float(row["exit_price"])
            qty = float(row["qty"])
            fee = float(row.get("fees", 0.0))
            side = row["side"].strip().lower()
            direction = 1.0 if side == "long" else -1.0
            pnl = direction * (exit_price - entry) * qty
            gross += pnl
            fees += fee
            trades += 1
    net = gross - fees
    avg = net / trades if trades else 0.0
    return PnLSummary(trades=trades, gross_pnl=gross, fees=fees, net_pnl=net, avg_net_per_trade=avg)
