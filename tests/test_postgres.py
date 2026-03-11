import subprocess

from pred_infra.storage import postgres
from pred_infra.storage.postgres import is_repo_local_postgres_url, prepare_runtime_db_url


def test_is_repo_local_postgres_url_matches_repo_local_instance() -> None:
    assert is_repo_local_postgres_url("postgresql://predinfra@127.0.0.1:55432/prediction_infra?sslmode=disable")
    assert is_repo_local_postgres_url("postgresql://predinfra@localhost:55432/prediction_infra")


def test_is_repo_local_postgres_url_rejects_other_targets() -> None:
    assert not is_repo_local_postgres_url("")
    assert not is_repo_local_postgres_url("postgresql://predinfra@127.0.0.1:5432/prediction_infra")
    assert not is_repo_local_postgres_url("postgresql://predinfra@127.0.0.1:55432/other_db")


def test_prepare_runtime_db_url_falls_back_on_local_bootstrap_failure(monkeypatch, tmp_path) -> None:
    def _boom(root, db_url):
        raise subprocess.CalledProcessError(1, ["bash", "scripts/start_local_postgres.sh"])

    monkeypatch.setattr(postgres, "ensure_local_postgres", _boom)

    db_url, warning = prepare_runtime_db_url(
        tmp_path,
        "postgresql://predinfra@127.0.0.1:55432/prediction_infra?sslmode=disable",
    )

    assert db_url == ""
    assert "runtime_state_db_fallback=sqlite" in warning
    assert "CalledProcessError" in warning


def test_prepare_runtime_db_url_keeps_nonlocal_urls(monkeypatch, tmp_path) -> None:
    called = False

    def _track(root, db_url):
        nonlocal called
        called = True

    monkeypatch.setattr(postgres, "ensure_local_postgres", _track)

    db_url, warning = prepare_runtime_db_url(
        tmp_path,
        "postgresql://predinfra@example.com:5432/prediction_infra?sslmode=require",
    )

    assert db_url == "postgresql://predinfra@example.com:5432/prediction_infra?sslmode=require"
    assert warning == ""
    assert called is False
