# Docs Index

Read these in order if you want the fastest path to a working mental model of this repository.

## Start Here

1. `docs/system-mental-model.md`
   - what the repo is trying to do
   - the core loop from market data to go/no-go decision
   - what is real today versus what is still scaffolding
2. `docs/pipeline-step-by-step.md`
   - the exact daily pipeline, step by step
   - which script runs at each stage
   - which files get created and why they matter
3. `docs/repo-map.md`
   - what each top-level folder and important module owns
   - where to look when something breaks
   - where to extend the system without adding confusion

## Existing Policy / Ops Docs

- `docs/current-status.md`
  - current machine status and immediate gaps
- `docs/agent-handoff.md`
  - current structural-edge operating state for future coding agents
  - active shortlist, scout lane, quote-diagnostic lane, and next ROI steps
- `docs/operations.md`
  - scheduler and operational workflow
- `docs/always-on-host-plan.md`
  - lowest-cost always-on hosting plan
  - deployment runbook for the always-on host
  - migration checklist and explicit spend guardrails
- `docs/always-on-host-longlist.md`
  - host-provider longlist and recommendation logic
  - why the default remains a single small VM
- `docs/macbook-host-checklist.md`
  - zero-monthly-cost MacBook host path
  - macOS-specific operating constraints and checklist
- `docs/strategy-intake-template.md`
  - required fields before a new strategy family gets research time
- `docs/strategy-discovery-loop.md`
  - repeatable funnel for discovering structural edges and rejecting weak ideas early
- `docs/registry-manual.md`
  - how to maintain the strategy family registry and contract ontology
- `docs/experiment-log-manual.md`
  - how to log every tested variant and keep only one primary paper family plus one backup candidate
- `docs/cross-venue-research.md`
  - ontology-first strict-match research workflow and the candidate triage handoff
- `docs/database.md`
  - PostgreSQL schema and sync flow
- `docs/scientific-policy.md`
  - mandatory research discipline
- `docs/rigorous-validation-pipeline.md`
  - statistical validation philosophy and gates
- `docs/validation-matrix.md`
  - required test coverage by stage
- `docs/repo-target.md`
  - target architecture and phase plan
- `docs/money-first-roadmap.md`
  - direction reset grounded in trading and forecasting literature
  - practical manual for improving the probability of real profitability
- `docs/immediate-bug-report.md`
  - urgent mistakes to correct now
- `docs/desired-feature-manual.md`
  - feature priority manual for increasing the chance of real profitability
- `docs/attack-plan.md`
  - build order and pass/fail milestones
- `docs/sources.md`
  - external references and source material

## One-Sentence Summary

This repo is a prediction-market research and paper-trading pipeline whose current live purpose is:
collect trustworthy market snapshots, normalize them, test simple strategies honestly, log paper returns, and refuse to scale until the evidence is good enough.
