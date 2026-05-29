# Job Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar cleanup automático de jobs antigos ao `TreinoRegistry` para evitar crescimento ilimitado das tabelas `job_status` e `job_output` no SQLite.

**Architecture:** Método `_purge_old_jobs(max_age_days=7, max_jobs=200)` adicionado a `TreinoRegistry` e chamado no início de `create_job()` (lazy cleanup). Remove jobs finalizados com mais de 7 dias OU quando o total de jobs finalizados excede 200, o que ocorrer primeiro. Jobs ativos (`done=0`) nunca são removidos.

**Tech Stack:** Python 3.12, SQLite via `sqlite3`, pytest.

---

## File Map

| Arquivo | Ação |
|---------|------|
| `src/lotofacil/interface/painel/treino_registry.py` | Modificar: import `timedelta`, migration de schema, `_purge_old_jobs`, atualizar `create_job` |
| `src/lotofacil/interface/painel/tests/test_registry_cleanup.py` | Criar: 3 testes unitários |

---

## Task 1: Testes de cleanup (TDD)

**Files:**
- Create: `src/lotofacil/interface/painel/tests/test_registry_cleanup.py`

- [ ] **Step 1: Criar arquivo de testes**

```python
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
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd /home/andre/Documentos/projetos/loteria/lotofacil && source venv/bin/activate
pytest src/lotofacil/interface/painel/tests/test_registry_cleanup.py -v 2>&1 | tail -15
```

Expected: `FAILED` — `AttributeError: 'TreinoRegistry' object has no attribute '_purge_old_jobs'` ou `OperationalError: table job_status has no column named created_at`.

---

## Task 2: Implementar `_purge_old_jobs` e atualizar schema

**Files:**
- Modify: `src/lotofacil/interface/painel/treino_registry.py`

- [ ] **Step 1: Adicionar `timedelta` ao import**

Localizar linha 7:
```python
from datetime import datetime, timezone
```

Substituir por:
```python
from datetime import datetime, timezone, timedelta
```

- [ ] **Step 2: Adicionar coluna `created_at` ao schema**

Localizar a constante `_SCHEMA` que contém `CREATE TABLE IF NOT EXISTS job_status`. Substituir o bloco:
```python
CREATE TABLE IF NOT EXISTS job_status (
    task_id     TEXT PRIMARY KEY,
    done        INTEGER NOT NULL DEFAULT 0,
    success     INTEGER,
    finished_at TEXT
);
```

Por:
```python
CREATE TABLE IF NOT EXISTS job_status (
    task_id     TEXT PRIMARY KEY,
    done        INTEGER NOT NULL DEFAULT 0,
    success     INTEGER,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT
);
```

- [ ] **Step 3: Adicionar migration para bancos existentes**

Localizar o `__init__` da classe `TreinoRegistry`:
```python
def __init__(self, db_path: Path) -> None:
    self._db = Path(db_path)
    self._db.parent.mkdir(parents=True, exist_ok=True)
    with self._conn() as conn:
        conn.executescript(_SCHEMA)
        conn.executescript(_INDEXES)
```

Substituir por:
```python
def __init__(self, db_path: Path) -> None:
    self._db = Path(db_path)
    self._db.parent.mkdir(parents=True, exist_ok=True)
    with self._conn() as conn:
        conn.executescript(_SCHEMA)
        conn.executescript(_INDEXES)
        try:
            conn.execute(
                "ALTER TABLE job_status ADD COLUMN created_at TEXT NOT NULL DEFAULT (datetime('now'))"
            )
            conn.commit()
        except Exception:
            pass  # coluna já existe em bancos criados após a migration
```

- [ ] **Step 4: Adicionar método `_purge_old_jobs`**

Imediatamente antes do método `create_job`, inserir:
```python
def _purge_old_jobs(self, max_age_days: int = 7, max_jobs: int = 200) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    with self._conn() as conn:
        old = conn.execute(
            "SELECT task_id FROM job_status WHERE done = 1 AND finished_at < ?",
            (cutoff,),
        ).fetchall()
        excess = conn.execute(
            """SELECT task_id FROM job_status WHERE done = 1
               ORDER BY created_at ASC
               LIMIT MAX(0,
                 (SELECT COUNT(*) FROM job_status WHERE done = 1) - ?
               )""",
            (max_jobs,),
        ).fetchall()
        to_delete = list({r[0] for r in old + excess})
        if not to_delete:
            return
        ph = ",".join("?" * len(to_delete))
        conn.execute(f"DELETE FROM job_output WHERE task_id IN ({ph})", to_delete)
        conn.execute(f"DELETE FROM job_status WHERE task_id IN ({ph})", to_delete)
        conn.commit()
```

- [ ] **Step 5: Atualizar `create_job` para chamar cleanup e persistir `created_at`**

Substituir o método `create_job` atual:
```python
def create_job(self, task_id: str) -> None:
    with self._conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO job_status (task_id, done) VALUES (?, 0)",
            (task_id,),
        )
```

Por:
```python
def create_job(self, task_id: str) -> None:
    self._purge_old_jobs()
    with self._conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO job_status (task_id, done, created_at) VALUES (?, 0, ?)",
            (task_id, _now()),
        )
```

- [ ] **Step 6: Rodar os testes**

```bash
pytest src/lotofacil/interface/painel/tests/test_registry_cleanup.py -v
```

Expected: `3 passed`.

- [ ] **Step 7: Rodar suite completa para verificar regressões**

```bash
pytest src/lotofacil/interface/painel/tests/ -v 2>&1 | tail -10
```

Expected: todos `PASSED`.

- [ ] **Step 8: Commit**

```bash
git add src/lotofacil/interface/painel/treino_registry.py \
        src/lotofacil/interface/painel/tests/test_registry_cleanup.py
git commit -m "feat: add lazy job cleanup to TreinoRegistry (TTL 7d + max 200 jobs)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Self-Review

- ✅ `_purge_old_jobs` só deleta jobs com `done=1` — jobs ativos são preservados
- ✅ `timedelta` adicionado ao import
- ✅ Migration idempotente (`except Exception: pass`)
- ✅ `create_job` persiste `created_at` explicitamente (não depende do DEFAULT do schema)
- ✅ 3 testes cobrem: antigos, excedentes, ativos preservados
