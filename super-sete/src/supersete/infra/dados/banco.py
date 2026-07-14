import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional

from supersete.infra.config import get_db_path

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
                    digitos      TEXT NOT NULL,
                    raw_json     TEXT
                );
            """)
        logger.debug("Database initialised at %s", self.db_path)

    def upsert_concurso(self, concurso: int, data: str, digitos: List[int], raw: dict = None):
        digitos_json = json.dumps(digitos)
        raw_json = json.dumps(raw, ensure_ascii=False) if raw else None
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO concursos (concurso, data, digitos, raw_json)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(concurso) DO UPDATE SET
                       data=excluded.data,
                       digitos=excluded.digitos,
                       raw_json=excluded.raw_json""",
                (concurso, data, digitos_json, raw_json),
            )

    def count_concursos(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM concursos").fetchone()
        return row[0] if row else 0

    def get_all_concursos(self) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT concurso, data, digitos FROM concursos ORDER BY concurso"
            ).fetchall()
        return [
            {
                "concurso": r["concurso"],
                "data": r["data"],
                "digitos": json.loads(r["digitos"]),
            }
            for r in rows
        ]

    def get_latest_concurso(self) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT concurso, data, digitos FROM concursos ORDER BY concurso DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return {
            "concurso": row["concurso"],
            "data": row["data"],
            "digitos": json.loads(row["digitos"]),
        }
