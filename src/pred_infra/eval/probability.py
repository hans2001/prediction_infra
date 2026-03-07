from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import fmean


def _stdev(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = fmean(values)
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    return math.sqrt(var)


def _sharpe(values: list[float]) -> float:
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


def _bootstrap_path(returns: list[float], horizon: int, block_size: int, rng: random.Random) -> list[float]:
    n = len(returns)
    path: list[float] = []
    while len(path) < horizon:
        start = rng.randrange(n)
        for i in range(block_size):
            path.append(returns[(start + i) % n])
            if len(path) >= horizon:
                break
    return path


def estimate_profit_probability(
    returns: list[float],
    n_trials: int = 5000,
    block_size: int = 5,
    horizon: int | None = None,
    seed: int | None = None,
) -> float:
    if not returns:
        raise ValueError("returns must be non-empty")
    if n_trials <= 0:
        raise ValueError("n_trials must be > 0")
    if block_size <= 0:
        raise ValueError("block_size must be > 0")
    h = horizon if horizon is not None else len(returns)
    if h <= 0:
        raise ValueError("horizon must be > 0")

    rng = random.Random(seed)
    wins = 0
    for _ in range(n_trials):
        path = _bootstrap_path(returns, h, block_size, rng)
        if sum(path) > 0.0:
            wins += 1
    return wins / n_trials


def estimate_ruin_probability(
    returns: list[float],
    n_trials: int = 5000,
    block_size: int = 5,
    horizon: int | None = None,
    max_drawdown: float = 0.20,
    period_stop_loss: float = 0.05,
    seed: int | None = None,
) -> float:
    if not returns:
        raise ValueError("returns must be non-empty")
    if not 0.0 < max_drawdown < 1.0:
        raise ValueError("max_drawdown must be in (0, 1)")
    if not 0.0 < period_stop_loss < 1.0:
        raise ValueError("period_stop_loss must be in (0, 1)")

    h = horizon if horizon is not None else len(returns)
    rng = random.Random(seed)
    ruined = 0

    for _ in range(n_trials):
        path = _bootstrap_path(returns, h, block_size, rng)
        equity = 1.0
        peak = 1.0
        is_ruined = False
        for r in path:
            if r <= -period_stop_loss or r <= -1.0:
                is_ruined = True
                break
            equity *= 1.0 + r
            peak = max(peak, equity)
            drawdown = (peak - equity) / peak if peak > 0 else 1.0
            if drawdown >= max_drawdown:
                is_ruined = True
                break
        if is_ruined:
            ruined += 1
    return ruined / n_trials


@dataclass(slots=True)
class PBOResult:
    pbo: float
    splits_used: int
    median_oos_percentile: float


def estimate_pbo(
    strategy_returns: dict[str, list[float]],
    n_splits: int = 200,
    train_fraction: float = 0.5,
    seed: int | None = None,
) -> PBOResult:
    names = [name for name, values in strategy_returns.items() if values]
    if len(names) < 2:
        raise ValueError("at least two strategies are required for PBO")
    if n_splits <= 0:
        raise ValueError("n_splits must be > 0")
    if not 0.2 <= train_fraction <= 0.8:
        raise ValueError("train_fraction must be between 0.2 and 0.8")

    t = min(len(strategy_returns[name]) for name in names)
    if t < 20:
        raise ValueError("at least 20 observations per strategy required for PBO")
    data = {name: strategy_returns[name][:t] for name in names}

    k = len(names)
    train_n = int(t * train_fraction)
    if train_n < 5 or (t - train_n) < 5:
        raise ValueError("train/test split is too small")

    rng = random.Random(seed)
    overfit_count = 0
    percentiles: list[float] = []
    splits_used = 0
    all_idx = list(range(t))

    for _ in range(n_splits):
        train_idx = set(rng.sample(all_idx, train_n))
        test_idx = [i for i in all_idx if i not in train_idx]

        sharpe_is: dict[str, float] = {}
        sharpe_oos: dict[str, float] = {}
        for name in names:
            series = data[name]
            is_values = [series[i] for i in train_idx]
            oos_values = [series[i] for i in test_idx]
            sharpe_is[name] = _sharpe(is_values)
            sharpe_oos[name] = _sharpe(oos_values)

        best_is = max(names, key=lambda n: sharpe_is[n])
        ranked_oos = sorted(names, key=lambda n: sharpe_oos[n], reverse=True)
        rank = ranked_oos.index(best_is)
        percentile = 1.0 - (rank / (k - 1)) if k > 1 else 1.0
        percentiles.append(percentile)
        if percentile < 0.5:
            overfit_count += 1
        splits_used += 1

    pbo = overfit_count / splits_used if splits_used else 1.0
    median_p = sorted(percentiles)[len(percentiles) // 2] if percentiles else 0.0
    return PBOResult(pbo=pbo, splits_used=splits_used, median_oos_percentile=median_p)


def conservative_real_profit_score(p_profit: float, p_ruin: float, pbo: float) -> float:
    for value, name in ((p_profit, "p_profit"), (p_ruin, "p_ruin"), (pbo, "pbo")):
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in [0, 1]")
    return p_profit * (1.0 - p_ruin) * (1.0 - pbo)
