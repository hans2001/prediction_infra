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
from pred_infra.eval.validation import evaluate_thresholds, summarize_returns  # noqa: E402


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
            ret = float(row[return_col])
            ts = row.get(time_col, "").strip() if time_col else ""
            rows.append((ts, strategy, ret))
    if time_col:
        rows.sort(key=lambda x: x[0])

    grouped: dict[str, list[float]] = defaultdict(list)
    for _, strategy, ret in rows:
        grouped[strategy].append(ret)
    return dict(grouped)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rigorous go/no-go validation for strategy viability.")
    parser.add_argument("--returns", required=True)
    parser.add_argument("--gates", default=str(ROOT / "configs" / "stat_validation_gates.example.json"))
    parser.add_argument("--strategy-col", default="strategy")
    parser.add_argument("--return-col", default="net_return")
    parser.add_argument("--time-col", default="timestamp")
    parser.add_argument("--focus-strategy", default="")
    parser.add_argument("--n-trials", type=int, default=5000)
    parser.add_argument("--block-size", type=int, default=5)
    parser.add_argument("--horizon", type=int, default=0)
    parser.add_argument("--pbo-splits", type=int, default=200)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    grouped = load_returns(
        Path(args.returns),
        strategy_col=args.strategy_col,
        return_col=args.return_col,
        time_col=args.time_col,
    )
    if not grouped:
        raise SystemExit("no usable returns found")

    gates = json.loads(Path(args.gates).read_text(encoding="utf-8"))
    focus = args.focus_strategy or max(grouped, key=lambda s: len(grouped[s]))
    if focus not in grouped:
        raise SystemExit(f"focus strategy not found: {focus}")

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
        max_drawdown=gates.get("max_drawdown", 0.2),
        period_stop_loss=gates.get("period_stop_loss", 0.05),
        seed=args.seed + 1,
    )

    pbo = 1.0
    pbo_warning = ""
    if len(grouped) >= 2:
        try:
            pbo = estimate_pbo(grouped, n_splits=args.pbo_splits, seed=args.seed + 2).pbo
        except ValueError as exc:
            pbo_warning = str(exc)

    conservative_score = conservative_real_profit_score(p_profit, p_ruin, pbo)
    summary = summarize_returns(focus_returns)
    metrics = {
        **summary,
        "p_profit": p_profit,
        "p_ruin": p_ruin,
        "pbo": pbo,
        "conservative_score": conservative_score,
    }
    decision = evaluate_thresholds(metrics, gates)

    report = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "focus_strategy": focus,
        "n_strategies": len(grouped),
        "metrics": metrics,
        "gates": gates,
        "go_live_candidate": decision.passed,
        "failed_rules": decision.failed_rules,
        "warnings": [pbo_warning] if pbo_warning else [],
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
