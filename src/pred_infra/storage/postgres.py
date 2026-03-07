from __future__ import annotations

import os
from pathlib import Path


def load_db_url(explicit: str = "") -> str:
    if explicit:
        return explicit
    env_url = os.getenv("DATABASE_URL", "").strip()
    if env_url:
        return env_url

    host = os.getenv("PGHOST", "").strip()
    user = os.getenv("PGUSER", "").strip()
    password = os.getenv("PGPASSWORD", "").strip()
    dbname = os.getenv("PGDATABASE", "").strip()
    port = os.getenv("PGPORT", "5432").strip() or "5432"
    sslmode = os.getenv("PGSSLMODE", "require").strip() or "require"
    if host and user and dbname:
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode={sslmode}"
    raise ValueError("database url not provided. set DATABASE_URL or PG* env vars")


def connect_db(db_url: str):
    import psycopg

    return psycopg.connect(db_url)


def apply_schema(conn, schema_path: str | Path) -> None:
    sql = Path(schema_path).read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
