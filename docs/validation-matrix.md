# Validation Matrix

This matrix defines how we verify Stage 1, Stage 2, and Stage 3.

## Stage 1: Data Pipeline Legitimacy
Objective: prove input data used for research is trustworthy.

Required tests:
1. Unit tests
   - parser/normalizer field mapping
   - price and timestamp parsing edge cases
2. Integration tests
   - fetch -> normalize -> report end-to-end
3. Data integrity checks
   - missing required fields
   - duplicate rows
   - out-of-range prices
   - parse errors
   - staleness threshold
4. Backpressure tests
   - burst ingest (many snapshots rapidly)
   - verify no data corruption or deadlock

Pass criteria:
- critical integrity errors are zero
- deterministic normalization output for the same input
- pipeline remains stable under burst load

## Stage 2: Evaluation Engine Legitimacy
Objective: prove metrics and accounting are mathematically correct.

Required tests:
1. Unit tests
   - Brier score, log loss, max drawdown
   - PnL accounting with fees/slippage
2. Reconciliation tests
   - known toy ledgers with expected outputs
3. Sensitivity tests
   - performance under conservative fee/slippage bumps
4. Integration tests
   - normalized data -> evaluation report

Pass criteria:
- metric tests pass
- ledger reconciliation matches expected values
- conclusions do not invert under small realistic cost shifts

## Stage 3: Strategy Legitimacy
Objective: prove a strategy has robust edge, not backtest luck.

Required tests:
1. Walk-forward out-of-sample backtests
2. Time-ordered train/validation/test splits
3. Regime robustness checks
4. Overfitting controls
   - limit strategy search space
   - track repeated tuning attempts
5. Forward validation
   - paper trading consistency check

Pass criteria:
- net OOS performance positive after fees/slippage
- drawdown within risk limits
- stable results across windows/regimes
- no unresolved overfitting red flags
