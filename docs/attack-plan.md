# Attack Plan

This plan is designed to remove guessing. Every stage has explicit pass/fail gates.

## Stage 0: Ground Truth and Access Setup
Goal: avoid building on wrong assumptions.

1. Read and extract from official docs:
   - API endpoints
   - fees
   - rate limits
   - resolution rules
   - trading restrictions
2. Create access in this order:
   - Kalshi demo account + API keys
   - Polymarket read-only/public data access
   - Polymarket trading auth only after paper gates pass

Pass gates:
- `docs/sources.md` updated with exact links used
- `docs/repo-target.md` has chosen strategy ranking and rationale

## Stage 1: Data Pipeline Reliability
Goal: trust market data before strategy decisions.

Build:
1. Pull market snapshots from both venues
2. Normalize to a common schema
3. Store raw + normalized snapshots with UTC timestamps

Validation:
1. Completeness: no missing required fields
2. Freshness: snapshot lag under configured threshold
3. Integrity: duplicate and parse-error rates near zero

Pass gates:
- 7 consecutive days with no critical data failures
- Integrity report generated daily

## Stage 2: Evaluation Engine (No Live Money)
Goal: prove metrics and accounting are correct.

Build:
1. Prediction metrics: Brier score, log loss, calibration
2. Trading metrics: gross/net PnL, fee impact, max drawdown
3. Fee/slippage model configurable by venue

Validation:
1. Unit tests for all metrics
2. Reconciliation tests on known toy ledgers
3. Sensitivity analysis on fee/slippage assumptions

Pass gates:
- All metric tests pass
- PnL changes directionally correctly under stress assumptions

## Stage 3: Strategy Research and Backtesting
Goal: rank strategies by robust net returns, not raw wins.

Process:
1. Define one hypothesis per strategy
2. Use train/validation/test splits (time-based, no leakage)
3. Run walk-forward backtests
4. Record all runs in `docs/experiment-log-template.csv`

Validation:
1. Net PnL after modeled fees/slippage
2. Drawdown and tail-risk behavior
3. Stability across market regimes

Pass gates:
- Top strategy remains positive in out-of-sample windows
- Performance remains acceptable after conservative cost bump

## Stage 4: Paper Trading
Goal: test reality gap between backtest and live market behavior.

Process:
1. Run strategy in paper mode for 30+ days
2. Compare expected vs observed fill quality
3. Track per-day and per-market risk exposure

Pass gates:
- Paper net PnL > 0 for the evaluation window
- Max drawdown and daily loss within risk limits
- No unresolved critical incidents

## Stage 5: Tiny Live Trial
Goal: validate execution with minimal downside.

Process:
1. Use very small fixed size
2. Enforce hard kill switch and daily stop-loss
3. Review every fill and anomaly

Pass gates:
- 2+ weeks positive net with low variance
- No risk-limit breaches
- Incident postmortems completed

## Stage 6: Scale and Optional AI Layer
Goal: add complexity only after edge is demonstrated.

1. Increase size slowly based on risk budget
2. Add automation and AI agent features last
3. Keep human override for all staged-live/live deployments

## Weekly Operating Loop
1. Monday: run data quality and infra health review
2. Tuesday-Wednesday: strategy experiments
3. Thursday: paper/live performance review
4. Friday: decide keep/kill for strategies based on gates

## "No Vibes" Rule
No strategy promotion without:
1. linked experiment artifact
2. linked metrics report
3. linked source/rule references
