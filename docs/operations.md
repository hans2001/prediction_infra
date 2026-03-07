# Operations

## Daily Automation
The daily automation entrypoint is:
- `scripts/run_daily_pipeline.py`

It executes:
1. market snapshot fetch
2. normalization
3. integrity report
4. probability report (if returns history exists)
5. go/no-go validation report (if returns history exists)
6. optional PostgreSQL sync (if `--db-write` is enabled)
7. appends pipeline timing metrics to `data/reports/pipeline_metrics.jsonl`

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
Cron template:
- `ops/cron/pred_infra.cron`

Install:
```bash
crontab ops/cron/pred_infra.cron
```

Verify:
```bash
crontab -l
tail -n 100 data/reports/cron_pipeline.log
```

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
