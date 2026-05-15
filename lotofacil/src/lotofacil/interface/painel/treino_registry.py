"""SQLite registry for versioned training sessions."""

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

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db))
        conn.row_factory = sqlite3.Row
        return conn

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

    def registrar_modelo(
        self,
        treino_id: str,
        arquivo_modelo: str,
        metricas: dict,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE treinos SET arquivo_modelo = ?, metricas = ?, status = 'completed', concluido_em = ? WHERE id = ?",
                (
                    str(arquivo_modelo),
                    json.dumps(metricas, ensure_ascii=False),
                    _now(),
                    treino_id,
                ),
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
