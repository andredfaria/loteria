"""Persistência SQLite compartilhada para sorteios não posicionais."""
from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


class BancoSorteios:
    """Banco de concursos com o contrato histórico usado pelos painéis.

    O caminho e a política de criação de diretórios pertencem ao projeto
    consumidor; o núcleo não cria arquivos ao ser importado.
    """

    def __init__(self, caminho: Path):
        self.db_path = Path(caminho)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS concursos (
                    concurso INTEGER PRIMARY KEY,
                    data TEXT NOT NULL,
                    dezenas TEXT NOT NULL,
                    raw_json TEXT
                );
            """)
        logger.debug("Database initialised at %s", self.db_path)

    def upsert_concurso(
        self, concurso: int, data: str, dezenas: list[int], raw: dict | None = None
    ) -> None:
        dezenas_json = json.dumps(sorted(dezenas))
        raw_json = json.dumps(raw, ensure_ascii=False) if raw else None
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO concursos (concurso, data, dezenas, raw_json)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(concurso) DO UPDATE SET
                       data=excluded.data,
                       dezenas=excluded.dezenas,
                       raw_json=excluded.raw_json""",
                (concurso, data, dezenas_json, raw_json),
            )

    def count_concursos(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM concursos").fetchone()
        return row[0] if row else 0

    def get_all_concursos(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT concurso, data, dezenas FROM concursos ORDER BY concurso"
            ).fetchall()
        return [
            {"concurso": row["concurso"], "data": row["data"],
             "dezenas": json.loads(row["dezenas"])}
            for row in rows
        ]

    def get_latest_concurso(self) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT concurso, data, dezenas FROM concursos "
                "ORDER BY concurso DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return {"concurso": row["concurso"], "data": row["data"],
                "dezenas": json.loads(row["dezenas"])}
