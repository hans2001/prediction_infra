# Agent Handoff

Last updated: 2026-03-11

This document is the shortest high-signal handoff for future coding agents.

Use it before opening a new strategy lane or changing scheduler behavior.

## Current Strategic State

- Primary approved paper family remains `kalshi_pair_arb_v1`.
- `cross_venue_pair_lock` remains the active structural backup candidate.
- Do not promote a new family ahead of ontology / strict-match / execution-reality work.

Why:

- this repo is still in the structural-edge search phase
- the highest-ROI path is still strict structural discovery, not strategy sprawl
- the current pair-lock lane already has active evidence flow and reusable infrastructure

## Current Fast-Loop Structure

The pair-lock workflow now has three layers:

1. Broad research triage:
   - [cross_venue_pair_lock_triage.json](/home/hans2/prediction_infra/data/reports/cross_venue_pair_lock_triage.json)
2. Active dense-observation shortlist:
   - [cross_venue_pair_lock_triage_refined.json](/home/hans2/prediction_infra/data/reports/cross_venue_pair_lock_triage_refined.json)
3. Scout re-entry lane:
   - [cross_venue_pair_lock_scout_candidates.json](/home/hans2/prediction_infra/data/reports/cross_venue_pair_lock_scout_candidates.json)

Current refined shortlist:

- `nhl_stanley_cup_carolina_hurricanes`
- `nhl_stanley_cup_colorado_avalanche`

Current scout lane:

- `nhl_atlantic_division_buffalo_sabres`
- `nhl_pacific_division_vegas_golden_knights`
- `nhl_stanley_cup_buffalo_sabres`

Rationale:

- dense polling should stay focused on pairs with current support
- broader names should not be treated as permanently dead

## Current Quote-Diagnostic State

Quote staleness / repeated-state diagnostics are now first-class artifacts:

- [pair_lock_quote_diagnostics.json](/home/hans2/prediction_infra/data/reports/pair_lock_quote_diagnostics.json)

Current interpretation:

- `nhl_stanley_cup_carolina_hurricanes`: `watch`
- `nhl_stanley_cup_colorado_avalanche`: `watch`
- `nhl_pacific_division_vegas_golden_knights`: `review_now`

Meaning:

- `watch` does not remove a pair from the active shortlist
- `review_now` should demote the pair from the active refined shortlist until the quote behavior looks cleaner

## Operator Workflow

Refresh quote diagnostics first:

```bash
python3 scripts/analyze_pair_lock_quote_diagnostics.py
```

Then refresh the fast-loop analysis and shortlist artifacts:

```bash
python3 scripts/analyze_pair_lock_fast_loop.py
```

Useful artifacts after refresh:

- [pair_lock_fast_loop_analysis.json](/home/hans2/prediction_infra/data/reports/pair_lock_fast_loop_analysis.json)
- [pair_lock_fast_loop_pair_summary.csv](/home/hans2/prediction_infra/data/reports/pair_lock_fast_loop_pair_summary.csv)
- [cross_venue_pair_lock_triage_refined.json](/home/hans2/prediction_infra/data/reports/cross_venue_pair_lock_triage_refined.json)
- [cross_venue_pair_lock_scout_candidates.json](/home/hans2/prediction_infra/data/reports/cross_venue_pair_lock_scout_candidates.json)

The local fast-loop launchers already prefer the refined triage file automatically if it exists.

## Status / Monitor Notes

- [status_report.py](/home/hans2/prediction_infra/scripts/status_report.py) now falls back to SQLite if repo-local Postgres bootstrap fails.
- [monitor_pipeline.py](/home/hans2/prediction_infra/scripts/monitor_pipeline.py) now surfaces:
  - refined triage candidates
  - scout candidates
  - quote diagnostics

Do not re-break the operator path by making local Postgres bootstrap a hard requirement for quick status checks.

## Highest-ROI Next Moves

For the next 7 days, prefer these in order:

1. expand ontology coverage around strict same-resolution structural candidates
2. add pair-level staleness and fill-survival scoring improvements
3. automate periodic scout sweeps without diluting the hot loop
4. tighten execution realism around size, stale quotes, and two-leg survivability
5. only then consider opening the next adjacent structural family, likely partition/parity or event-latency

## What Not To Do

Do not:

- open many unrelated new families
- revive broad maker-family work as a default path
- treat the refined shortlist as permanent truth
- call the pair-lock family validated from current evidence
- confuse repeated quote states with durable tradable edge

## Decision Rule For Future Agents

Before making a change, ask:

- does this improve signal quality, execution realism, risk control, or reliability?
- does this help the current structural-edge search path more than starting a new family would?

If not, defer it.
