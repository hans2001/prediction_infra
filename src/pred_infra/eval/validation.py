from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean

from .metrics import max_drawdown


def _stdev(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = fmean(values)
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    return math.sqrt(var)


def sharpe_ratio(values: list[float]) -> float:
    if not values:
        return float("-inf")
    std = _stdev(values)
    mean = fmean(values)
    if std == 0.0:
        if mean > 0:
            return float("inf")
        if mean < 0:
            return float("-inf")
        return 0.0
    return mean / std


def cumulative_equity(values: list[float], initial: float = 1.0) -> list[float]:
    equity = initial
    curve: list[float] = []
    for r in values:
        equity *= 1.0 + r
        curve.append(equity)
    return curve


@dataclass(slots=True)
class GateDecision:
    passed: bool
    failed_rules: list[str]


def evaluate_thresholds(metrics: dict[str, float], gates: dict[str, float]) -> GateDecision:
    failed: list[str] = []

    def lt(metric_key: str, gate_key: str) -> None:
        if metric_key in metrics and gate_key in gates and metrics[metric_key] < gates[gate_key]:
            failed.append(f"{metric_key}<{gate_key} ({metrics[metric_key]:.6f}<{gates[gate_key]:.6f})")

    def gt(metric_key: str, gate_key: str) -> None:
        if metric_key in metrics and gate_key in gates and metrics[metric_key] > gates[gate_key]:
            failed.append(f"{metric_key}>{gate_key} ({metrics[metric_key]:.6f}>{gates[gate_key]:.6f})")

    lt("observations", "min_observations")
    lt("mean_return", "min_mean_return")
    lt("sharpe", "min_sharpe")
    lt("p_profit", "min_p_profit")
    gt("p_ruin", "max_p_ruin")
    gt("pbo", "max_pbo")
    lt("conservative_score", "min_conservative_score")
    gt("max_drawdown", "max_drawdown")

    return GateDecision(passed=len(failed) == 0, failed_rules=failed)


def summarize_returns(values: list[float]) -> dict[str, float]:
    curve = cumulative_equity(values, initial=1.0)
    mdd = (max_drawdown(curve) / max(curve)) if curve and max(curve) > 0 else 1.0
    return {
        "observations": float(len(values)),
        "mean_return": fmean(values) if values else float("nan"),
        "stdev_return": _stdev(values),
        "sharpe": sharpe_ratio(values),
        "final_equity": curve[-1] if curve else 1.0,
        "max_drawdown": mdd,
    }
