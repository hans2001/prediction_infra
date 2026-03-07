# Rigorous Validation Pipeline

This is the required go/no-go pipeline before risking meaningful capital.

## Objective
Prove competitive advantage with statistical evidence, not subjective confidence.

## Pipeline
1. Stage 1 data legitimacy
   - run integrity checks
   - reject runs with critical data errors
2. Stage 2 metric legitimacy
   - verify accounting and prediction metrics
   - run regression tests to prevent silent metric drift
3. Stage 3 strategy legitimacy
   - run out-of-sample walk-forward backtests
   - estimate `P_profit`, `P_ruin`, and `PBO`
4. Go/No-Go decision
   - apply fixed threshold gates
   - log failed rules explicitly

## Regression Testing Requirement
Any change in:
- data normalization
- fee/slippage model
- metric calculation
- strategy logic

must trigger regression validation and produce a new report artifact.

## Command Sequence
```bash
# Stage 1
python3 scripts/fetch_market_snapshot.py --source all --limit 100
python3 scripts/normalize_snapshots.py
python3 scripts/build_integrity_report.py --max-age-hours 24

# Stage 2 + 3 probability view
python3 scripts/probability_report.py \
  --returns data/examples/returns.csv \
  --focus-strategy mm_v1

# Final go/no-go gate
python3 scripts/validate_strategy.py \
  --returns data/examples/returns.csv \
  --gates configs/stat_validation_gates.example.json \
  --focus-strategy mm_v1 \
  --out data/reports/validation_report_example.json
```

## Decision Rule
`go_live_candidate = true` is required before moving from paper to staged-live.
If false, improve model or execution and rerun from Stage 1/2 as needed.
