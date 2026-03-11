# Current Status

Last updated: 2026-03-11

## Current Progress
- local Python environment created at `.venv`
- repo installed editable into `.venv`
- targeted regression checks pass in the repo venv: `7 passed`
- end-to-end daily pipeline verified on this machine after the SQLite runtime-state migration
- local cron installed for `@reboot` and every 15 minutes
- `cron.service` is enabled on boot on this machine
- the exact scheduled cron command was executed manually and completed successfully
- automated paper-return generation is wired into the daily pipeline for `kalshi_pair_arb_v1`
- automated Polymarket maker-style paper returns are wired into the daily pipeline
- one-command operator status is available via `python3 scripts/status_report.py`
- operator-facing status/monitor timestamps are displayed in `America/New_York`

## Data Artifacts Verified
- raw snapshots written under `data/raw/`
- normalized snapshots written under `data/normalized/`
- integrity reports written under `data/reports/`
- pipeline run state and timing metrics persisted in `data/reports/pipeline_state.db`
- cron log written to `data/reports/cron_pipeline.log`
- legacy pipeline runtime files `pipeline_status.json` and `pipeline_metrics.jsonl` are no longer the source of truth

## Runtime State
- local runtime database: `data/reports/pipeline_state.db`
- pipeline run rows currently present: `46`
- pipeline metric rows currently present: `45`
- earliest recorded run in SQLite: `2026-03-10T15:59:22+00:00`
- latest recorded run in SQLite at update time: `2026-03-11T00:19:43+00:00`
- elapsed wall-clock span captured in SQLite at update time: about `8.34` hours

## Returns And Validation Status
- `data/returns/returns_history.csv` was seeded on 2026-03-10 from `data/examples/returns.csv`
- seeded rows use `source=bootstrap_example`
- real scheduled paper rows now use strategy `kalshi_pair_arb_v1` and source `paper_kalshi_pair_arb`
- historical scheduled runs also produced `polymarket_maker_microcheap_liquid_v1`, `polymarket_maker_cheap_yes_v1`, and `polymarket_maker_tight_spread_v1`
- probability and validation reports now generate during the daily pipeline
- current primary scheduled focus strategy should be `kalshi_pair_arb_v1`
- maker-family and watcher-family scheduled upserts should remain disabled unless explicitly approved
- automated probability and validation reports exclude `source=bootstrap_example`
- treat current seeded-return reports as pipeline smoke tests only, not trading evidence
- go-live criteria are not met

## Local Scheduler Behavior
- scheduled runs happen only while this computer is powered on
- shutting the computer down stops cron execution and data collection
- on next boot, `cron` starts automatically and the `@reboot` entry runs once after a short delay

## Known Gaps
- `kalshi_pair_arb_v1` history has just started and is still too short for inference
- `polymarket_maker_microcheap_liquid_v1` currently has only a handful of real observations and is far below the go/no-go thresholds
- no 30+ day paper-trading evidence exists yet
- no live execution recommendation should be made
- `cross_venue_pair_lock` evidence is still early and concentrated in a small number of pairs
- repeated quote-state behavior can still contaminate apparent pair-lock edge if diagnostics are ignored

## Recommended Next Actions
1. upsert real paper/backtest returns after each run into `data/returns/returns_history.csv`
2. review the SQLite runtime DB plus the latest integrity, ledger, probability, validation, and leaderboard artifacts daily
3. move scheduling to an always-on host if uninterrupted collection matters
4. refresh pair-lock quote diagnostics with `python3 scripts/analyze_pair_lock_quote_diagnostics.py`
5. refresh pair-lock shortlist artifacts with `python3 scripts/analyze_pair_lock_fast_loop.py`
6. use [agent-handoff.md](/home/hans2/prediction_infra/docs/agent-handoff.md) before opening a new strategy lane or changing pair-lock automation

## Pair-Lock Snapshot

Current structural backup candidate:

- `cross_venue_pair_lock`

Current active dense-observation shortlist:

- `nhl_stanley_cup_carolina_hurricanes`
- `nhl_stanley_cup_colorado_avalanche`

Current scout re-entry lane:

- `nhl_atlantic_division_buffalo_sabres`
- `nhl_pacific_division_vegas_golden_knights`
- `nhl_stanley_cup_buffalo_sabres`

Current quote-diagnostic interpretation:

- Carolina: `watch`
- Colorado: `watch`
- Vegas Pacific Division: `review_now`
