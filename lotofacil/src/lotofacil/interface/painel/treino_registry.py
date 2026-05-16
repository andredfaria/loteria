"""SQLite registry for versioned training sessions and job output."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
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
    finished_at TEXT
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

    # ── Job output ───────────────────────────────────────────────

    def create_job(self, task_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO job_status (task_id, done) VALUES (?, 0)",
                (task_id,),
            )

    def write_line(self, task_id: str, text: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO job_output (task_id, text) VALUES (?, ?)",
                (task_id, text),
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
                "SELECT done, success FROM job_status WHERE task_id = ?",
                (task_id,),
            ).fetchone()

        lines = [r["text"] for r in rows]
        next_offset = rows[-1]["id"] if rows else offset

        if status_row is None:
            return {"lines": lines, "done": True, "success": False, "next_offset": next_offset}

        done = bool(status_row["done"])
        result: dict = {"lines": lines, "done": done, "next_offset": next_offset}
        if done:
            result["success"] = bool(status_row["success"])
        return result
