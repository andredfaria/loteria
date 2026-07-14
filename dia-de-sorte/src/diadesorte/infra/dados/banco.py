import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional

from diadesorte.infra.config import get_db_path

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_db_path()
        self._init_db()

    @contextmanager
    def _connect(self):
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

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS concursos (
                    concurso     INTEGER PRIMARY KEY,
                    data         TEXT NOT NULL,
                    dezenas      TEXT NOT NULL,
                    mes_sorte    TEXT NOT NULL DEFAULT '',
                    raw_json     TEXT
                );
            """)
        logger.debug("Database initialised at %s", self.db_path)

    def upsert_concurso(self, concurso: int, data: str, dezenas: List[int], mes_sorte: str = "", raw: dict = None):
        dezenas_json = json.dumps(sorted(dezenas))
        raw_json = json.dumps(raw, ensure_ascii=False) if raw else None
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO concursos (concurso, data, dezenas, mes_sorte, raw_json)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(concurso) DO UPDATE SET
                       data=excluded.data,
                       dezenas=excluded.dezenas,
                       mes_sorte=excluded.mes_sorte,
                       raw_json=excluded.raw_json""",
                (concurso, data, dezenas_json, mes_sorte, raw_json),
            )

    def count_concursos(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM concursos").fetchone()
        return row[0] if row else 0

    def get_all_concursos(self) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT concurso, data, dezenas, mes_sorte FROM concursos ORDER BY concurso"
            ).fetchall()
        return [
            {
                "concurso": r["concurso"],
                "data": r["data"],
                "dezenas": json.loads(r["dezenas"]),
                "mes_sorte": r["mes_sorte"],
            }
            for r in rows
        ]

    def get_latest_concurso(self) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT concurso, data, dezenas, mes_sorte FROM concursos ORDER BY concurso DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return {
            "concurso": row["concurso"],
            "data": row["data"],
            "dezenas": json.loads(row["dezenas"]),
            "mes_sorte": row["mes_sorte"],
        }
