#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pred_infra.eval.probability import (  # noqa: E402
    conservative_real_profit_score,
    estimate_pbo,
    estimate_profit_probability,
    estimate_ruin_probability,
)


def _parse_float(value: str) -> float:
    return float(value.strip())


def load_returns(
    csv_path: Path,
    strategy_col: str,
    return_col: str,
    time_col: str,
) -> dict[str, list[float]]:
    rows = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            strategy = row.get(strategy_col, "").strip()
            if not strategy:
                continue
            ret = _parse_float(row[return_col])
            timestamp = row.get(time_col, "").strip() if time_col else ""
            rows.append((timestamp, strategy, ret))

    if time_col:
        rows.sort(key=lambda x: x[0])

    grouped: dict[str, list[float]] = defaultdict(list)
    for _, strategy, ret in rows:
        grouped[strategy].append(ret)
    return dict(grouped)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build probability report for strategy viability.")
    parser.add_argument("--returns", required=True, help="CSV file with strategy return history")
    parser.add_argument("--strategy-col", default="strategy")
    parser.add_argument("--return-col", default="net_return")
    parser.add_argument("--time-col", default="timestamp")
    parser.add_argument("--focus-strategy", default="", help="strategy used for P_profit/P_ruin")
    parser.add_argument("--n-trials", type=int, default=5000)
    parser.add_argument("--block-size", type=int, default=5)
    parser.add_argument("--horizon", type=int, default=0, help="0 means use observed length")
    parser.add_argument("--max-drawdown", type=float, default=0.20)
    parser.add_argument("--period-stop-loss", type=float, default=0.05)
    parser.add_argument("--pbo-splits", type=int, default=200)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default="", help="optional path to write report json")
    args = parser.parse_args()

    returns_path = Path(args.returns)
    grouped = load_returns(
        returns_path,
        strategy_col=args.strategy_col,
        return_col=args.return_col,
        time_col=args.time_col,
    )
    if not grouped:
        raise SystemExit("no usable returns found in csv")

    if args.focus_strategy:
        if args.focus_strategy not in grouped:
            raise SystemExit(f"focus strategy not found: {args.focus_strategy}")
        focus = args.focus_strategy
    else:
        focus = max(grouped, key=lambda s: len(grouped[s]))

    focus_returns = grouped[focus]
    horizon = args.horizon if args.horizon > 0 else len(focus_returns)
    p_profit = estimate_profit_probability(
        focus_returns,
        n_trials=args.n_trials,
        block_size=args.block_size,
        horizon=horizon,
        seed=args.seed,
    )
    p_ruin = estimate_ruin_probability(
        focus_returns,
        n_trials=args.n_trials,
        block_size=args.block_size,
        horizon=horizon,
        max_drawdown=args.max_drawdown,
        period_stop_loss=args.period_stop_loss,
        seed=args.seed + 1,
    )

    warnings: list[str] = []
    pbo = None
    pbo_meta: dict[str, float | int] = {}
    if len(grouped) >= 2:
        try:
            result = estimate_pbo(grouped, n_splits=args.pbo_splits, seed=args.seed + 2)
            pbo = result.pbo
            pbo_meta = {
                "splits_used": result.splits_used,
                "median_oos_percentile": result.median_oos_percentile,
            }
        except ValueError as exc:
            pbo = None
            pbo_meta = {}
            warnings.append(f"PBO skipped: {exc}")

    score = conservative_real_profit_score(p_profit, p_ruin, pbo if pbo is not None else 0.5)
    if len(focus_returns) < 300:
        warnings.append("focus strategy has fewer than 300 observations; probability estimates may be unstable")
    if len(grouped) < 2:
        warnings.append("PBO requires >=2 strategies; fallback pbo=0.5 used for conservative score")

    report = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "focus_strategy": focus,
        "n_strategies": len(grouped),
        "focus_observations": len(focus_returns),
        "horizon": horizon,
        "p_profit": p_profit,
        "p_ruin": p_ruin,
        "pbo": pbo,
        "conservative_real_profit_score": score,
        "pbo_meta": pbo_meta,
        "params": {
            "n_trials": args.n_trials,
            "block_size": args.block_size,
            "max_drawdown": args.max_drawdown,
            "period_stop_loss": args.period_stop_loss,
            "pbo_splits": args.pbo_splits,
            "seed": args.seed,
        },
        "warnings": warnings,
    }

    print(json.dumps(report, ensure_ascii=True, indent=2))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
