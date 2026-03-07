# Prediction Infra

Build a lean prediction-market trading system focused on one outcome: positive net profit after fees and slippage.

## Priority Right Now
1. Reliable data pipeline
2. Honest backtesting and paper trading
3. Tight risk controls
4. Small live validation
5. AI agent integration later (only after edge is proven)

If a task does not improve ROI, execution quality, or risk control, it is low priority.

## Scientific Method Mandate
This repo must follow a scientific workflow:
1. state a falsifiable hypothesis
2. define metrics before running experiments
3. separate train/validation/test by time
4. report out-of-sample results only for strategy decisions
5. record every run and keep reproducible artifacts

Working assumption:
- there may exist a mathematically exploitable edge in some market regimes.
- the system should converge toward that edge through measurement and falsification.

Important:
- no method guarantees profit.
- any strategy can fail under regime change, hidden costs, or execution drift.

## Success Metrics (Go/No-Go Gates)
- Positive paper-trading net PnL over 30+ days
- Positive live net PnL with small capital over 2+ weeks
- Max drawdown and daily loss stay inside predefined limits

## Strategy Ranking (Current)
1. Single-venue market making + liquidity incentives
2. Single-venue structural mispricing/parity arbitrage
3. Cross-venue arbitrage (Polymarket <-> Kalshi) only for strictly matched rules
4. Whale-follow/copy-trading as weak overlay signal only

Between your two options, current ranking is:
1. Cross-venue arbitrage
2. Whale-follow

## First Step: Account or API Docs?
Do docs first, then accounts.
1. Read official API, fee, and resolution docs from both platforms.
2. Build public-data collector + paper evaluation first.
3. Then create exchange accounts/keys for controlled live testing.

## What "Strong Dev Infra" Means
For strategy work, "strong dev infra" means:
- documented REST + WebSocket APIs
- clear auth and key lifecycle
- rate limits and error semantics
- demo/sandbox support
- clear fee schedule and settlement docs
- stable market data channels

## Repo Docs
- `docs/repo-target.md`: target architecture, phased plan, strategy scoring
- `docs/sources.md`: official docs + papers for model/evaluation tuning
- `docs/attack-plan.md`: step-by-step build and objective pass/fail gates
- `docs/scientific-policy.md`: mandatory scientific philosophy for all contributors/agents
- `docs/validation-matrix.md`: required tests by stage (Stage 1/2/3)
- `docs/rigorous-validation-pipeline.md`: go/no-go statistical validation pipeline
- `docs/operations.md`: automation, cron, and returns-history operations

## Current Scaffold
- `src/pred_infra/collector`: market data fetchers
- `src/pred_infra/collector/normalize.py`: shared market schema normalization
- `src/pred_infra/eval`: metrics and evaluation logic
- `src/pred_infra/eval/integrity.py`: Stage 1 data integrity checks
- `scripts/fetch_market_snapshot.py`: raw market snapshot pull
- `scripts/normalize_snapshots.py`: raw -> normalized JSONL
- `scripts/build_integrity_report.py`: normalized data quality report
- `scripts/eval_model.py`: probability model evaluation CLI
- `scripts/probability_report.py`: P_profit / P_ruin / PBO report
- `scripts/validate_strategy.py`: threshold-based go/no-go validator
- `scripts/upsert_returns_history.py`: append/dedupe returns history
- `scripts/run_daily_pipeline.py`: one-command daily pipeline runner

## What Is Already Implemented For Legitimacy
Stage 1 (data correctness):
- schema normalization to common fields
- integrity report with missing/duplicate/price-bounds/staleness/parse checks

Stage 2 (evaluation correctness):
- Brier score and log loss implementation
- trade-ledger gross/net PnL summary with fees
- max drawdown metric
- deterministic test fixtures for metric and normalization logic

## Quick Start
```bash
cd /Users/hans/repo/pred-infra

# 1) Fetch latest public market snapshots
python3 scripts/fetch_market_snapshot.py --source all --limit 100

# 2) Normalize snapshots to common schema
python3 scripts/normalize_snapshots.py

# 3) Build integrity report
python3 scripts/build_integrity_report.py --max-age-hours 24

# 4) Evaluate sample prediction quality + sample trade ledger
python3 scripts/eval_model.py \
  --predictions data/examples/predictions.csv \
  --ledger data/examples/ledger.csv

# 5) Build probability report from strategy return history
python3 scripts/probability_report.py \
  --returns data/examples/returns.csv \
  --focus-strategy mm_v1 \
  --out data/reports/probability_report_example.json

# 6) Run rigorous go/no-go validation gates
python3 scripts/validate_strategy.py \
  --returns data/examples/returns.csv \
  --gates configs/stat_validation_gates.example.json \
  --focus-strategy mm_v1 \
  --out data/reports/validation_report_example.json

# 7) Upsert new paper/backtest returns into long-run history
python3 scripts/upsert_returns_history.py \
  --input-csv data/examples/returns.csv \
  --history data/returns/returns_history.csv \
  --default-source paper

# 8) Run daily pipeline end-to-end
python3 scripts/run_daily_pipeline.py --focus-strategy mm_v1
```

## Collaboration
Execution rules for humans/agents are in `AGENTS.md`.
