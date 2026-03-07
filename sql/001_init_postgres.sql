CREATE TABLE IF NOT EXISTS market_snapshots (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    snapshot_ts TIMESTAMPTZ NOT NULL,
    market_id TEXT NOT NULL,
    event_id TEXT NULL,
    title TEXT NULL,
    status TEXT NULL,
    close_time TIMESTAMPTZ NULL,
    updated_time TIMESTAMPTZ NULL,
    yes_bid DOUBLE PRECISION NULL,
    yes_ask DOUBLE PRECISION NULL,
    no_bid DOUBLE PRECISION NULL,
    no_ask DOUBLE PRECISION NULL,
    yes_price DOUBLE PRECISION NULL,
    no_price DOUBLE PRECISION NULL,
    last_price DOUBLE PRECISION NULL,
    liquidity DOUBLE PRECISION NULL,
    volume DOUBLE PRECISION NULL,
    raw_file TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, snapshot_ts, market_id)
);

CREATE INDEX IF NOT EXISTS idx_market_snapshots_source_ts
    ON market_snapshots(source, snapshot_ts DESC);

CREATE TABLE IF NOT EXISTS strategy_returns (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    strategy TEXT NOT NULL,
    net_return DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL DEFAULT 'paper',
    run_id TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (timestamp, strategy, source, run_id)
);

CREATE INDEX IF NOT EXISTS idx_strategy_returns_strategy_ts
    ON strategy_returns(strategy, timestamp DESC);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id BIGSERIAL PRIMARY KEY,
    run_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);
