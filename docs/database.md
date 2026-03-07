# Database

## Current State
Default local storage still exists:
- `data/raw`
- `data/normalized`
- `data/reports`
- `data/returns/returns_history.csv`

For production durability, use PostgreSQL (recommended: AWS RDS PostgreSQL).

## Schema
SQL file:
- `sql/001_init_postgres.sql`

Tables:
1. `market_snapshots`
2. `strategy_returns`
3. `pipeline_runs`

## Connection
Use one of:
1. `DATABASE_URL`
2. `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGSSLMODE`

Template:
- `configs/db.env.example`

## Initialize DB
```bash
python3 scripts/init_postgres.py --db-url "$DATABASE_URL"
```

## Ingest Normalized Market Data
```bash
python3 scripts/ingest_normalized_to_db.py \
  --normalized-dir data/normalized \
  --db-url "$DATABASE_URL"
```

## Sync Returns History
```bash
python3 scripts/sync_returns_to_db.py \
  --returns-csv data/returns/returns_history.csv \
  --db-url "$DATABASE_URL"
```

## Daily Pipeline with DB Write
```bash
python3 scripts/run_daily_pipeline.py \
  --focus-strategy mm_v1 \
  --db-write \
  --db-url "$DATABASE_URL"
```
