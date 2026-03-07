# Scientific Policy

This document is mandatory for all human contributors and AI agents.

## Core Philosophy
We optimize for objective truth in performance, not storytelling.
Our working assumption is:
- prediction markets may contain mathematically exploitable inefficiencies.
- careful measurement and falsification can approach those inefficiencies.

This is not a guarantee of profit.
All strategy claims remain provisional until validated out-of-sample and in forward testing.

## Non-Negotiable Rules
1. No strategy claim without reproducible evidence.
2. No strategy ranking using in-sample performance only.
3. No promotion to live mode without paper-trading gates.
4. No silent metric changes after results are known.
5. No unresolved data-integrity failures when evaluating strategy quality.

## Scientific Workflow
1. Define hypothesis:
   - include mechanism and failure conditions
2. Predefine metrics:
   - e.g., net PnL after fees/slippage, max drawdown, calibration
3. Define experiment design:
   - time-based train/validation/test
   - walk-forward evaluation
4. Execute and log:
   - store exact code/data/config version
5. Falsify or keep:
   - if gate fails, strategy is rejected or revised

## Required Statistical Discipline
- use proper scoring rules for probabilities (Brier/log loss)
- stress fee/slippage assumptions
- evaluate overfitting risk for multi-strategy search
- report uncertainty, not only point estimates

## Decision Rule
A strategy is "provisionally viable" only if:
1. out-of-sample net performance is positive
2. risk constraints are respected
3. results are stable under conservative cost assumptions
