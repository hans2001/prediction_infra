# AGENTS.md

This file defines how AI agents and human contributors should work in this repository.

This repository is not a toy project.
Its direction determines whether the company converges toward real profit or burns time on plausible-sounding noise.

## CEO Mandate

`pred-infra` exists to discover, validate, and execute prediction-market edges that can survive costs, risk controls, and reality.

Everything else is secondary.

The company wins by:

1. finding structural edges before others
2. rejecting weak ideas quickly
3. preserving evidence quality
4. staying alive long enough to compound a real edge

The company loses by:

1. mistaking activity for progress
2. promoting strategy variants without mechanism
3. trusting optimistic fills
4. expanding complexity before one family proves durable

## Strategic Direction (Mandatory)

Current target hierarchy:

1. single-venue structural arbitrage / parity
2. strictly matched cross-venue locks
3. event-latency / state-transition strategies
4. narrow maker filters with explicit inventory control
5. forecasting overlays as filters, not primary alpha

Interpretation:

- structural edges come first
- forecasting is supportive, not central
- broad market making is not the main bet
- no strategy family should become "default" just because code already exists

Reference docs:

- `docs/money-first-roadmap.md`
- `docs/repo-target.md`
- `docs/registry-manual.md`
- `docs/immediate-bug-report.md`
- `docs/desired-feature-manual.md`
- `docs/agent-handoff.md`

Operational note:

- before opening a new strategy lane or changing active structural-edge automation, read `docs/agent-handoff.md` for the current shortlist, scout lane, and quote-diagnostic state

## Priority Filter (Mandatory)

Every task must map to at least one:

- `edge`: improves signal quality, candidate discovery, or opportunity detection
- `execution`: improves fill quality, latency handling, or correctness
- `risk`: reduces blow-up risk, hidden exposure, or false confidence
- `reliability`: reduces downtime, drift, data corruption, or broken automation

If a task maps to none of the above, defer it.

Current stage priority order:

1. data integrity
2. contract ontology / rule matching
3. backtest validity
4. pre-screen discipline and multiple-testing control
5. paper-trade consistency
6. live execution hardening
7. AI/assistant features (deferred)

## Non-Negotiable Rules

1. Default to `paper` mode unless explicitly asked to enable live mode.
2. Never commit secrets, private keys, or API credentials.
3. Never call a strategy "working" without out-of-sample evidence.
4. Never promote a strategy family to scheduled paper tracking without explicit approval.
5. Never use a rejected or demoted family as the scheduler default.
6. Never present optimistic fills as if they were realistic execution.
7. Never hide failed experiments, sibling variants, or parameter sweeps.
8. Never claim edge without the mechanism, evidence artifact, and invalidation conditions.
9. Never add UI, chatbot, or framework work ahead of edge / execution / risk work.
10. After each backtest or paper run, upsert returns into `data/returns/returns_history.csv`.

## Operating Principles

1. Profitability over presentation.
2. Measured edge over opinions.
3. Execution correctness over feature count.
4. Risk control over aggressive sizing.
5. Scientific falsification over narrative confirmation.
6. Simplicity over strategy sprawl.
7. Forward evidence over backtest aesthetics.

## What Counts As Progress

Progress is:

- a cleaner market mapping layer
- better candidate generation from structural relationships
- faster rejection of bad families
- more realistic execution assumptions
- better calibration and uncertainty measurement
- one surviving paper family with positive net expectancy

Progress is not:

- more strategy names
- more dashboards
- more broad abstractions
- more paper returns from unapproved families
- more code that cannot improve trading decisions

## Scientific Policy (Mandatory)

1. Every strategy starts with a falsifiable hypothesis.
2. Metrics and pass/fail gates are declared before running experiments.
3. Train/validation/test split must be time-ordered to prevent leakage.
4. Strategy ranking must use net performance after fees/slippage.
5. Multiple-testing risk must be addressed at the strategy-family level.
6. Preserve experiment logs and exact code/data/config version references.
7. Treat "mathematically right answer" as a search process, not a guaranteed result.
8. If evidence quality falls, the correct action is to stop and repair it, not power through.

## Research Doctrine

Every strategy proposal must answer:

1. what is the mechanism?
2. why should it persist after costs?
3. what exact market rules make it valid?
4. what would falsify it?
5. what are the main execution failure modes?

Preferred candidate families:

- complement/parity violations
- partition inconsistencies
- strict cross-venue rule matches
- event-transition lag
- narrow inventory-light maker buckets

Disfavored candidate families:

- broad maker-everywhere ideas
- "whale-follow" as primary alpha
- loose cross-venue matches
- heavily tuned threshold variants
- ideas that only work under perfect fill assumptions

## Forecasting Doctrine

If a task involves predictions or models:

1. output probabilities, not categorical confidence
2. use base rates and reference classes first
3. score with Brier and/or log loss
4. report calibration, not just hit rate
5. treat forecasting as an overlay unless it proves standalone value

Forecasting guidance is inspired by:

- Tetlock / Gardner, *Superforecasting*
- Mellers et al., Good Judgment Project work
- proper scoring-rule literature

## Execution Doctrine

Execution realism is part of strategy validity.

Required concerns:

- venue fees
- slippage stress
- stale-data guard
- partial fills where relevant
- queue / latency effects where relevant
- inventory drift for maker-style families

Any backtest or paper model that ignores the dominant execution risk for that family is incomplete.

## Strategy Family Gating

Allowed statuses:

1. `research`
2. `candidate`
3. `paper-approved`
4. `rejected`
5. `archived`

Rules:

1. only `paper-approved` families may be scheduled by default
2. `candidate` families must pass intake and pre-screen first
3. `rejected` families must not remain in default automation
4. reviving a rejected family requires a written reason and materially new evidence
5. every active family must appear in `configs/research_queue.csv` with an explicit role
6. the queue must contain exactly one `primary_paper` and at most one `backup_candidate`

## Required Workflow For New Strategy Families

1. Fill out `docs/strategy-intake-template.md`.
2. Explain the mechanism and invalidation rule.
3. Build a minimal backtest or candidate return series.
4. Update `configs/strategy_families.csv` and `configs/contract_ontology.csv` if the family or mapping layer changed.
5. Add or update the family entry in `configs/research_queue.csv`.
6. Log every tested variant to `data/experiments/strategy_family_experiments.csv`.
7. Run `scripts/validate_registries.py`.
8. Run `scripts/prescreen_strategy_candidates.py`.
9. If it passes, run `scripts/validate_strategy.py` when sample size is sufficient.
10. Only then consider paper approval.

If a family fails pre-screen, treat it as failed until new evidence exists.

## Required Artifacts For Strategy Claims

For every strategy claim, attach:

1. exact platform rule / resolution references
2. exact fee and slippage assumptions
3. exact code path used
4. exact data range
5. pre-screen output if candidate stage
6. validation report if paper/live recommendation stage
7. assumptions that could invalidate the result

## Required Artifacts For Code Changes

For any change affecting:

- data schema or normalization
- strategy logic
- fee/slippage modeling
- paper accounting
- validation logic
- scheduler defaults

the contributor must provide:

1. tests or reproducible command output
2. risk impact
3. regression evidence
4. note on whether returns history interpretation changes

## Automation Rules

1. Scheduled automation must center the current primary approved family, not legacy defaults.
2. No family gets auto-upserted by the daily pipeline unless explicitly approved.
3. If a family is demoted strategically, cron/systemd defaults must be updated in the same change.
4. Operator-facing docs must match actual scheduler behavior.

## Current Immediate Corrections To Respect

1. default scheduled focus is `kalshi_pair_arb_v1`, not the Polymarket maker family
2. maker-family and watcher-family auto-upserts are disabled by default
3. broad maker research is secondary until structural-edge work is stronger
4. contract ontology / rule mapping is a top priority gap

## Development Standards

- Language: Python first.
- Tests: prioritize settlement logic, pricing logic, risk guards, and pipeline gating.
- Determinism: simulation and evaluation must be seedable and reproducible.
- Observability: structured logs for decision -> order -> fill -> PnL.
- Comments: explain non-obvious logic, not trivial code.

## Minimum Risk Controls

- max position size per market
- max daily loss
- max concurrent exposure
- stale-data guard
- emergency kill switch
- explicit capital caps for staged-live

## Non-Priorities

- fancy UI or branding work
- generic exchange abstractions before one edge is proven
- multi-agent complexity before the single-strategy workflow is reliable
- new strategy ideas without the evaluation pipeline
- live scaling tools before 30+ day positive paper evidence

## Definition Of Done (Required)

1. Code implemented with tests or reproducible validation commands.
2. Risk impact documented.
3. Logs/metrics added if operationally relevant.
4. Paper-trading or backtest evidence attached when strategy behavior changes.
5. Net result reported after fees/slippage assumptions.
6. Regression validation report attached for metric/strategy/data logic changes.
7. Scheduler / ops docs updated if automation behavior changed.
