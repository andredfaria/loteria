"""SQLite registry for versioned training sessions and job output."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path


_SCHEMA = """
CREATE TABLE IF NOT EXISTS treinos (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    tipo_config TEXT NOT NULL,
    parametros TEXT NOT NULL,
    arquivo_modelo TEXT,
    metricas TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    criado_em TEXT NOT NULL,
    concluido_em TEXT
);

CREATE TABLE IF NOT EXISTS job_output (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id  TEXT NOT NULL,
    text     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_status (
    task_id     TEXT PRIMARY KEY,
    done        INTEGER NOT NULL DEFAULT 0,
    success     INTEGER,
    created_at  TEXT,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS jogos_gerados (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    treino_id  TEXT NOT NULL,
    treino_nome TEXT NOT NULL,
    concurso   INTEGER NOT NULL,
    jogos      TEXT NOT NULL,
    criado_em  TEXT NOT NULL
);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_job_output_task ON job_output(task_id, id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for key in ("parametros", "metricas"):
        if d.get(key):
            try:
                d[key] = json.loads(d[key])
            except Exception:
                pass
    return d


class TreinoRegistry:
    def __init__(self, db_path: Path) -> None:
        self._db = Path(db_path)
        self._db.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_SCHEMA)
            conn.executescript(_INDEXES)
            try:
                conn.execute(
                    "ALTER TABLE job_status ADD COLUMN created_at TEXT"
                )
                conn.commit()
            except sqlite3.OperationalError:
                pass  # column already exists
            try:
                conn.execute(
                    "ALTER TABLE job_status ADD COLUMN progress TEXT"
                )
                conn.commit()
            except sqlite3.OperationalError:
                pass  # column already exists
        self._recover_orphans()

    def _recover_orphans(self) -> None:
        """Mark treinos stuck as 'running' from a previous server instance as failed."""
        now = _now()
        with self._conn() as conn:
            conn.execute(
                "UPDATE treinos SET status = 'failed', concluido_em = ? "
                "WHERE status = 'running'",
                (now,),
            )
            # Find all incomplete jobs so we can write a recovery message to each
            orphan_jobs = conn.execute(
                "SELECT task_id FROM job_status WHERE done = 0"
            ).fetchall()
            for row in orphan_jobs:
                conn.execute(
                    "INSERT INTO job_output (task_id, text) VALUES (?, ?)",
                    (row[0], "⚠️  Treino interrompido: servidor reiniciado durante o treinamento."),
                )
            conn.execute(
                "UPDATE job_status SET done = 1, success = 0, finished_at = ? "
                "WHERE done = 0",
                (now,),
            )
            conn.commit()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db))
        conn.row_factory = sqlite3.Row
        return conn

    # ── Treinos ──────────────────────────────────────────────────

    def criar(self, treino_id: str, nome: str, tipo_config: str, parametros: dict) -> dict:
        row = {
            "id": treino_id,
            "nome": nome,
            "tipo_config": tipo_config,
            "parametros": json.dumps(parametros, ensure_ascii=False),
            "status": "running",
            "criado_em": _now(),
        }
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO treinos (id, nome, tipo_config, parametros, status, criado_em) "
                "VALUES (:id, :nome, :tipo_config, :parametros, :status, :criado_em)",
                row,
            )
        return self.buscar(treino_id)

    def atualizar_status(self, treino_id: str, status: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE treinos SET status = ? WHERE id = ?",
                (status, treino_id),
            )

    def registrar_modelo(self, treino_id: str, arquivo_modelo: str, metricas: dict) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE treinos SET arquivo_modelo = ?, metricas = ?, status = 'completed', concluido_em = ? WHERE id = ?",
                (str(arquivo_modelo), json.dumps(metricas, ensure_ascii=False), _now(), treino_id),
            )

    def marcar_falha(self, treino_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE treinos SET status = 'failed', concluido_em = ? WHERE id = ?",
                (_now(), treino_id),
            )

    def listar(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM treinos ORDER BY criado_em DESC"
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def buscar(self, treino_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM treinos WHERE id = ?", (treino_id,)
            ).fetchone()
        return _row_to_dict(row) if row else None

    def renomear(self, treino_id: str, nome: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE treinos SET nome = ? WHERE id = ?", (nome.strip(), treino_id)
            )
        return cur.rowcount > 0

    def deletar(self, treino_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM treinos WHERE id = ?", (treino_id,))
        return cur.rowcount > 0

    # ── Jogos gerados ────────────────────────────────────────────

    def salvar_jogo(self, treino_id: str, treino_nome: str, concurso: int, jogos: list) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO jogos_gerados (treino_id, treino_nome, concurso, jogos, criado_em) "
                "VALUES (?, ?, ?, ?, ?)",
                (treino_id, treino_nome, concurso, json.dumps(jogos, ensure_ascii=False), _now()),
            )
        return cur.lastrowid

    def listar_jogos(self, limit: int = 100) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jogos_gerados ORDER BY criado_em DESC LIMIT ?", (limit,)
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("jogos"):
                try:
                    d["jogos"] = json.loads(d["jogos"])
                except Exception:
                    pass
            result.append(d)
        return result

    # ── Job output ───────────────────────────────────────────────

    def _purge_old_jobs(self, max_age_days: int = 7, max_jobs: int = 200) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        with self._conn() as conn:
            old = conn.execute(
                "SELECT task_id FROM job_status WHERE done = 1 AND finished_at < ?",
                (cutoff,),
            ).fetchall()
            total_done = conn.execute(
                "SELECT COUNT(*) FROM job_status WHERE done = 1"
            ).fetchone()[0]
            excess_count = max(0, total_done - max_jobs)
            excess = []
            if excess_count > 0:
                excess = conn.execute(
                    "SELECT task_id FROM job_status WHERE done = 1 "
                    "ORDER BY COALESCE(created_at, '0000-00-00') ASC LIMIT ?",
                    (excess_count,),
                ).fetchall()
            to_delete = list({r[0] for r in old + excess})
            if not to_delete:
                return
            ph = ",".join("?" * len(to_delete))
            conn.execute(f"DELETE FROM job_output WHERE task_id IN ({ph})", to_delete)
            conn.execute(f"DELETE FROM job_status WHERE task_id IN ({ph})", to_delete)
            conn.commit()

    def create_job(self, task_id: str) -> None:
        self._purge_old_jobs()
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO job_status (task_id, done, created_at) VALUES (?, 0, ?)",
                (task_id, _now()),
            )

    def write_line(self, task_id: str, text: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO job_output (task_id, text) VALUES (?, ?)",
                (task_id, text),
            )

    def update_progress(self, task_id: str, progress: dict) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE job_status SET progress = ? WHERE task_id = ?",
                (json.dumps(progress, ensure_ascii=False), task_id),
            )

    def finish_job(self, task_id: str, success: bool) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE job_status SET done = 1, success = ?, finished_at = ? WHERE task_id = ?",
                (1 if success else 0, _now(), task_id),
            )

    def poll_job(self, task_id: str, offset: int) -> dict:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, text FROM job_output WHERE task_id = ? AND id > ? ORDER BY id LIMIT 100",
                (task_id, offset),
            ).fetchall()
            status_row = conn.execute(
                "SELECT done, success, progress FROM job_status WHERE task_id = ?",
                (task_id,),
            ).fetchone()

        lines = [r["text"] for r in rows]
        next_offset = rows[-1]["id"] if rows else offset

        if status_row is None:
            return {"lines": lines, "done": True, "success": False, "next_offset": next_offset}

        done = bool(status_row["done"])
        result: dict = {"lines": lines, "done": done, "next_offset": next_offset}
        if status_row["progress"]:
            try:
                result["progress"] = json.loads(status_row["progress"])
            except (TypeError, ValueError):
                pass
        if done:
            result["success"] = bool(status_row["success"])
        return result
