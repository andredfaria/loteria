"""Tests for TreinoRegistry job cleanup."""
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from lotofacil.interface.painel.treino_registry import TreinoRegistry


@pytest.fixture
def reg(tmp_path):
    return TreinoRegistry(tmp_path / "test.db")


def _insert_finished_job(reg, task_id: str, age_days: float = 0.0) -> None:
    ts = (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat()
    with reg._conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO job_status (task_id, done, created_at, finished_at) VALUES (?,1,?,?)",
            (task_id, ts, ts),
        )
        conn.execute(
            "INSERT INTO job_output (task_id, text) VALUES (?,?)",
            (task_id, "output line"),
        )
        conn.commit()


def test_purge_remove_jobs_antigos(reg):
    _insert_finished_job(reg, "old_job", age_days=10)
    reg._purge_old_jobs(max_age_days=7, max_jobs=200)
    with reg._conn() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM job_status WHERE task_id='old_job'"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM job_output WHERE task_id='old_job'"
        ).fetchone()[0] == 0


def test_purge_remove_jobs_excedentes(reg):
    for i in range(205):
        _insert_finished_job(reg, f"job_{i:03d}", age_days=i * 0.01)
    reg._purge_old_jobs(max_age_days=365, max_jobs=200)
    with reg._conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM job_status WHERE done = 1"
        ).fetchone()[0]
        assert count <= 200


def test_purge_preserva_jobs_ativos(reg):
    active_task = "active_job"
    with reg._conn() as conn:
        ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO job_status (task_id, done, created_at) VALUES (?,0,?)",
            (active_task, ts),
        )
        conn.execute(
            "INSERT INTO job_output (task_id, text) VALUES (?,?)",
            (active_task, "running"),
        )
        conn.commit()
    reg._purge_old_jobs(max_age_days=1, max_jobs=0)
    with reg._conn() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM job_status WHERE task_id=?", (active_task,)
        ).fetchone()[0] == 1
