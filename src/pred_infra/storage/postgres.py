from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def load_db_url(explicit: str = "") -> str:
    if explicit:
        return explicit
    env_url = os.getenv("DATABASE_URL", "").strip()
    if env_url:
        return env_url
    for candidate in (Path.cwd() / ".env", Path.cwd() / ".env.local"):
        file_env_url = _read_env_file(candidate).get("DATABASE_URL", "").strip()
        if file_env_url:
            return file_env_url

    host = os.getenv("PGHOST", "").strip()
    user = os.getenv("PGUSER", "").strip()
    password = os.getenv("PGPASSWORD", "").strip()
    dbname = os.getenv("PGDATABASE", "").strip()
    port = os.getenv("PGPORT", "5432").strip() or "5432"
    sslmode = os.getenv("PGSSLMODE", "require").strip() or "require"
    if host and user and dbname:
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode={sslmode}"
    raise ValueError("database url not provided. set DATABASE_URL or PG* env vars")


def is_repo_local_postgres_url(db_url: str) -> bool:
    if not db_url:
        return False
    parsed = urlparse(db_url)
    hostname = (parsed.hostname or "").strip().lower()
    port = parsed.port or 5432
    dbname = parsed.path.lstrip("/")
    return hostname in {"127.0.0.1", "localhost"} and port == 55432 and dbname == "prediction_infra"


def ensure_local_postgres(root: str | Path, db_url: str) -> None:
    if not is_repo_local_postgres_url(db_url):
        return
    repo_root = Path(root)
    script_path = repo_root / "scripts" / "start_local_postgres.sh"
    if not script_path.exists():
        raise FileNotFoundError(f"local postgres bootstrap script missing: {script_path}")
    subprocess.run(
        ["bash", str(script_path)],
        cwd=repo_root,
        check=True,
        env=os.environ.copy(),
    )


def prepare_runtime_db_url(root: str | Path, db_url: str) -> tuple[str, str]:
    if not db_url:
        return "", ""
    if not is_repo_local_postgres_url(db_url):
        return db_url, ""
    try:
        ensure_local_postgres(root, db_url)
    except (FileNotFoundError, OSError, subprocess.CalledProcessError) as exc:
        return "", f"runtime_state_db_fallback=sqlite reason={type(exc).__name__}: {exc}"
    return db_url, ""


def connect_db(db_url: str):
    import psycopg

    return psycopg.connect(db_url)


def apply_schema(conn, schema_path: str | Path) -> None:
    path = Path(schema_path)
    if path.is_dir():
        files = sorted(path.glob("*.sql"))
    else:
        files = [path]
    with conn.cursor() as cur:
        for file_path in files:
            sql = file_path.read_text(encoding="utf-8")
            cur.execute(sql)
    conn.commit()
