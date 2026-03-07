# AGENTS.md

This file defines how AI agents and human contributors should work in this repository.

## Project Intent
`pred-infra` exists to generate risk-adjusted profit in prediction markets.
Everything else is secondary.

## Operating Principles
1. Profitability over presentation.
2. Measured edge over opinions.
3. Execution correctness over feature count.
4. Risk control over aggressive sizing.
5. Ship small, test fast, iterate weekly.
6. Scientific falsification over narrative confirmation.

## Priority Filter (Mandatory)
Every task must map to at least one:
- `edge`: improves signal quality or opportunity detection
- `execution`: improves fill quality, speed, or correctness
- `risk`: reduces blow-up risk or hidden exposure
- `reliability`: reduces downtime/data errors

If a task maps to none of the above, defer it.

Current stage priority order:
1. data integrity
2. backtest validity
3. paper-trade consistency
4. live execution hardening
5. AI/assistant features (deferred)

## Agent Rules
1. Default to paper trading unless explicitly asked to enable live mode.
2. Never commit secrets, private keys, or API credentials.
3. Validate with reproducible scripts before claiming edge.
4. Log fills, PnL, and risk events with timestamps.
5. For strategy changes, include before/after metrics.
6. Do not add agent/chatbot features unless profitability gates are met.
7. Do not claim "working strategy" without out-of-sample evidence.
8. For every strategy claim, include assumptions that could invalidate it.
9. Run `scripts/validate_strategy.py` and attach the report before any go-live recommendation.

## Scientific Policy (Mandatory)
1. Every strategy starts with a falsifiable hypothesis.
2. Metrics and pass/fail gates are declared before running experiments.
3. Train/validation/test split must be time-ordered to prevent leakage.
4. Strategy ranking must use net performance after fees/slippage.
5. Multiple-testing risk must be addressed (avoid data snooping).
6. Preserve experiment logs and exact code/data version references.
7. Treat "mathematically right answer" as a search process, not a guaranteed result.

## Suggested Repo Layout
```text
src/
  collector/
  strategy/
  sim/
  risk/
  agent/
  common/
tests/
scripts/
configs/
data/
docs/
```

## Development Standards
- Language: Python first (TypeScript optional for adapters/tools).
- Tests: prioritize pricing logic, settlement, and risk guards.
- Determinism: simulation must be seedable and reproducible.
- Observability: structured logs for decision -> order -> fill -> PnL.

## Execution Mode Gates
1. `research`: data pull + analysis only
2. `paper`: simulated fills and PnL tracking
3. `staged-live`: real APIs with minimal capital and strict caps
4. `live`: enabled only with explicit operator approval

## Minimum Risk Controls
- max position size per market
- max daily loss
- max concurrent exposure
- stale-data guard
- emergency kill switch

## Non-Priorities
- Fancy UI or branding work
- Generic framework abstractions before profitable strategy exists
- Multi-agent complexity before single-strategy workflow is reliable
- New strategy ideas without proper evaluation pipeline

## Definition of Done (Required)
1. Code implemented with basic tests
2. Risk impact documented (position, drawdown, failure modes)
3. Logs/metrics added
4. Paper-trading or backtest evidence attached
5. Net result reported after fees/slippage assumptions
6. Regression validation report attached for metric/strategy/data logic changes
