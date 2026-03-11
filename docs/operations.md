# Operations

## Daily Automation
The daily automation entrypoint is:
- `scripts/run_daily_pipeline.py`

It executes:
1. market snapshot fetch
2. normalization
3. integrity report
4. probability report (if returns history exists)
5. strategy leaderboard + triage report (if returns history exists)
6. go/no-go validation report (if returns history exists)
7. persists local operational state to `data/reports/pipeline_state.db`
8. optional PostgreSQL sync (if `--db-write` is enabled)

Quick status check:
```bash
python3 scripts/status_report.py
```

Automated probability and validation reports exclude `source=bootstrap_example` so scheduled reports reflect real paper history by default.
Scheduled leaderboard reports use the same source filter and write `strategy_leaderboard_*.json` into `data/reports/`.
Maker-family and watcher-family return generation are disabled by default in the scheduled pipeline and must be explicitly enabled when approved for paper tracking.
Scheduled fetches should use a conservative per-source snapshot limit by default to reduce resource spikes on smaller hosts.

Important boundary:
- the daily cron pipeline is no longer the primary evidence engine for `cross_venue_pair_lock`
- the triaged tracked-pair fast loop is the primary evidence engine for that family
- cron remains useful for broad repo health, normalization, integrity, and baseline reports

## Returns History Pipeline
Canonical history file:
- `data/returns/returns_history.csv`

To add new strategy returns from a backtest/paper run:
```bash
python3 scripts/upsert_returns_history.py \
  --input-csv path/to/new_returns.csv \
  --history data/returns/returns_history.csv \
  --default-source paper
```

Required columns in input:
- `timestamp`
- `strategy`
- `net_return`

Optional columns:
- `source`
- `run_id`
- `note`

## Cron Setup
Use cron only when you are not using the packaged `systemd` timer. On a server, prefer the timer-based deployment in `ops/lightsail/systemd`.

Cron template:
- `ops/cron/pred_infra.cron`

Install:
```bash
crontab ops/cron/pred_infra.cron
```

Default cron assumptions:
- app lives at `/opt/pred-infra`
- virtualenv lives at `/opt/pred-infra/.venv`
- focus strategy is `kalshi_pair_arb_v1`
- snapshot limit is `5000` markets per source by default for scheduled runs
- maker-family auto-upserts are disabled unless you explicitly add enable flags

If your install path differs, edit the template before loading it into crontab.

Verify:
```bash
crontab -l
tail -n 100 data/reports/cron_pipeline.log
python3 scripts/status_report.py
```

## Live Monitor
Run the local monitor service:

```bash
python3 scripts/monitor_pipeline.py --host 127.0.0.1 --port 8787
```

Install it as a persistent user service:

```bash
bash scripts/install_local_monitor.sh
```

Check status:

```bash
systemctl --user status pred-infra-monitor.service --no-pager
journalctl --user -u pred-infra-monitor.service -n 50 --no-pager
```

Open:

```text
http://127.0.0.1:8787
```

What it shows:
- current run status: `running`, `success`, `failed`
- scheduler health: `on schedule` vs `overdue`
- paper watcher health, decision, and recent watcher cycles
- current pipeline step and last output line
- next expected run time and schedule drift
- recent run history and latest-run step timeline
- latest integrity / probability / validation artifact summaries
- recent step timings from the latest run
- recent `pipeline_state.db` metric history
- live tail of `data/reports/cron_pipeline.log`

Update model:
- the dashboard opens a live server-sent events stream at `/api/stream`
- if the stream drops, the page falls back to periodic snapshot fetches from `/api/monitor`
- pipeline state is sourced from the local SQLite metrics database written by the scheduled job, not from browser polling

Monitor data sources:
- `data/reports/pipeline_state.db`
- `data/reports/watcher_status.json`
- `data/reports/watcher_events.jsonl`
- `data/reports/watcher_opportunities.jsonl`
- `data/reports/cross_venue_pair_lock_triage_refined.json`
- `data/reports/cross_venue_pair_lock_scout_candidates.json`
- `data/reports/pair_lock_quote_diagnostics.json`
- `data/reports/cron_pipeline.log`

Recommended interpretation:
- `running`: the pipeline is currently active
- `on schedule`: the last success is within the expected 15 minute interval
- `overdue`: no successful run has landed within the expected interval window
- `failed`: the most recent run exited non-zero; inspect the log tail and `last_error`
- `next expected run`: when the next healthy completion should roughly appear if cron remains healthy
- `schedule drift`: how far beyond the expected run window the system has slipped; `0s` is healthy
- `recent runs`: use this to spot repeating slowdowns or a fresh failure after a sequence of successes
- `latest validation report`: use this to separate scheduler health from strategy quality; a healthy scheduler can still produce a non-go-live strategy report
- `quote review-now pairs`: active shortlist names whose repeated-state or book-timestamp behavior warrants extra skepticism before treating the edge as durable

Persistence note:
- the local installer creates a `systemd --user` service
- if `loginctl show-user "$USER" -p Linger` returns `Linger=no`, the monitor starts on login rather than at machine boot
- to keep it alive across reboots without login, enable linger as root: `loginctl enable-linger <user>`

## Paper Watcher

The old generic watcher is no longer the primary path for structural lock discovery.

For `cross_venue_pair_lock`, the watcher role is now served by the triaged fast loop plus its machine-written pair-lock watcher artifacts:
- `data/reports/pair_lock_watcher_status.json`
- `data/reports/pair_lock_watcher_events.jsonl`
- `data/reports/pair_lock_watcher_opportunities.jsonl`

Use the old generic watcher only if you are explicitly working on the separate watcher / maker research path.
Purpose:
- sample markets every 60 seconds
- detect paper arbitrage candidates
- record structured watcher decisions and opportunity telemetry

Install the local watcher service:

```bash
bash scripts/install_local_watcher.sh 60
```

Check status:

```bash
systemctl --user status pred-infra-watcher.service --no-pager
journalctl --user -u pred-infra-watcher.service -n 50 --no-pager
```

Run one cycle manually:

```bash
python3 scripts/run_paper_arb_watcher.py --interval-seconds 1 --max-loops 1 --limit 200
```

Watcher artifacts:
- `data/reports/watcher_status.json`: current machine-readable watcher state
- `data/reports/watcher_events.jsonl`: one structured event per watcher cycle
- `data/reports/watcher_opportunities.jsonl`: one row per detected candidate opportunity

How to interpret watcher decisions:
- `paper_trade` + `candidate_found`: the watcher found at least one paper candidate worth recording
- `skip` + `edge_too_small`: markets were scanned but no net-positive candidate passed the threshold
- `skip` + `no_tradeable_markets`: no usable open Kalshi rows were available in that cycle
- `error` + `execution_error`: the watcher loop failed; inspect the watcher service logs

Preferred structural-lock watcher path:
- run the triaged fast loop continuously
- read `pair_lock_watcher_status.json` and `pair_lock_watcher_events.jsonl`
- use that telemetry to measure candidate appearance, persistence, and fill survival

## Tracked Pair Fast Loop

Purpose:
- collect dense observations for the `cross_venue_pair_lock` shortlist
- test whether executable lock candidates survive to the next poll
- convert shortlist candidates into paper-return evidence

Install the local fast-loop service:

```bash
bash scripts/install_local_fast_loop.sh 5 5
```

Check status:

```bash
systemctl --user status pred-infra-fast-loop.service --no-pager
journalctl --user -u pred-infra-fast-loop.service -n 50 --no-pager
```

Recommended local default:
- `sleep_sec=5`
- `top_n=5`

Interpretation:
- use this loop to learn quickly on pair-lock candidates
- do not expect the 15 minute cron pipeline to capture short-lived locks reliably
- if you need overnight continuity, move this service to an always-on host

## Local Machine Setup
For a laptop or desktop, install the user-level cron schedule with:

```bash
bash scripts/install_local_cron.sh
```

What it installs:
- an `@reboot` pipeline run after a 60 second delay
- a recurring run every 15 minutes
- a `flock` lock so runs do not overlap
- the default scheduled focus strategy `kalshi_pair_arb_v1`
- no maker-family or watcher-family auto-upserts unless explicitly enabled

Important behavior:
- cron jobs run only while the computer is on
- putting the computer to sleep pauses collection and scheduled runs
- shutting the computer down pauses collection and scheduled runs
- when the computer boots again, `cron` starts automatically and the `@reboot` job runs once

If you need uninterrupted collection, use an always-on server instead of a personal machine.

If you need a zero-monthly-cost compromise, use the Mac checklist in [docs/macbook-host-checklist.md](/home/hans2/prediction_infra/docs/macbook-host-checklist.md). That path is acceptable for paper evidence, but it is not equivalent to a dedicated server.

For the continuous tracked-pair fast loop, the local launcher now uses `systemd-inhibit` by default so the machine does not enter sleep while the loop is active. That prevents suspend instead of trying to run through actual sleep, which is not possible on a sleeping laptop.
The installed `pred-infra-fast-loop.service` is the stable continuous collector while the machine is awake. On this host, do not wrap the user service itself with `systemd-inhibit`; interactive launcher mode is the supported sleep-blocking path.

Linux note:
- the persistent-service helpers in this repo use `systemd`

macOS note:
- use `cron` plus the `tmux` fast-loop launcher instead of the `systemd` installers
- use `caffeinate` or equivalent power settings to prevent sleep while collecting

## Regression Discipline
After any change to:
- data schema/normalization
- metric math
- fee/slippage modeling
- strategy logic

you must rerun the daily pipeline and keep generated reports as evidence.

## Lightsail Deployment
Deployment helper:
- `ops/lightsail/install_lightsail.sh`

What it sets up:
1. Python venv and package install
2. `.env` from DB template
3. `systemd` service + timer (every 15 minutes)
4. `logrotate` for pipeline logs

Optional monitor service:
- `ops/lightsail/systemd/pred-infra-monitor.service`
- serves the local dashboard on `127.0.0.1:8787`

Default scheduled focus strategy:
- `kalshi_pair_arb_v1`

Deploy:
```bash
bash ops/lightsail/install_lightsail.sh
```

Verify:
```bash
systemctl status pred-infra-pipeline.timer --no-pager
systemctl status pred-infra-pipeline.service --no-pager
systemctl list-timers --all | grep pred-infra
journalctl -u pred-infra-pipeline.service -n 100 --no-pager
```
