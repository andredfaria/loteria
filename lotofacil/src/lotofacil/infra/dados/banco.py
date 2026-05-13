"""SQLite persistence layer for Lotofácil data."""

import sqlite3
import json
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from lotofacil.infra.config import DB_PATH

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
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
                    raw_json     TEXT
                );

                CREATE TABLE IF NOT EXISTS predicoes (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    concurso_alvo     INTEGER NOT NULL,
                    dezenas_sugeridas TEXT NOT NULL,
                    probabilidades    TEXT NOT NULL,
                    confianca_media   REAL,
                    modelos_utilizados TEXT,
                    criado_em         TEXT DEFAULT (datetime('now')),
                    acertos           INTEGER,
                    validado_em       TEXT,
                    UNIQUE(concurso_alvo)
                );
            """)
        logger.debug("Database initialised at %s", self.db_path)

    # ── Concursos ──────────────────────────────────────────────────────────────

    def upsert_concurso(self, concurso: int, data: str, dezenas: List[int], raw: dict = None):
        dezenas_json = json.dumps(sorted(dezenas))
        raw_json = json.dumps(raw) if raw else None
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

    def get_all_concursos(self) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT concurso, data, dezenas FROM concursos ORDER BY concurso"
            ).fetchall()
        return [
            {
                "concurso": r["concurso"],
                "data": r["data"],
                "dezenas": json.loads(r["dezenas"]),
            }
            for r in rows
        ]

    def get_latest_concurso(self) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT concurso, data, dezenas FROM concursos ORDER BY concurso DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return {
            "concurso": row["concurso"],
            "data": row["data"],
            "dezenas": json.loads(row["dezenas"]),
        }

    # ── Predições ──────────────────────────────────────────────────────────────

    def save_prediction(self, concurso_alvo: int, dezenas: List[int],
                        probabilidades: List[float], confianca_media: float,
                        modelos: List[str]):
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO predicoes
                       (concurso_alvo, dezenas_sugeridas, probabilidades, confianca_media, modelos_utilizados)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(concurso_alvo) DO UPDATE SET
                       dezenas_sugeridas=excluded.dezenas_sugeridas,
                       probabilidades=excluded.probabilidades,
                       confianca_media=excluded.confianca_media,
                       modelos_utilizados=excluded.modelos_utilizados,
                       criado_em=datetime('now')""",
                (
                    concurso_alvo,
                    json.dumps(sorted(dezenas)),
                    json.dumps([round(float(p), 6) for p in probabilidades]),
                    float(confianca_media),
                    json.dumps(modelos),
                ),
            )

    def update_validation(self, concurso_alvo: int, acertos: int):
        with self._connect() as conn:
            conn.execute(
                """UPDATE predicoes SET acertos=?, validado_em=datetime('now')
                   WHERE concurso_alvo=?""",
                (acertos, concurso_alvo),
            )

    def get_prediction_history(self, limit: int = 50) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT concurso_alvo, dezenas_sugeridas, confianca_media,
                          acertos, criado_em, validado_em
                   FROM predicoes
                   ORDER BY concurso_alvo DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        return [
            {
                "concurso_alvo": r["concurso_alvo"],
                "dezenas_sugeridas": json.loads(r["dezenas_sugeridas"]),
                "confianca_media": r["confianca_media"],
                "acertos": r["acertos"],
                "criado_em": r["criado_em"],
                "validado_em": r["validado_em"],
            }
            for r in rows
        ]

    def get_pending_validations(self) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT concurso_alvo, dezenas_sugeridas
                   FROM predicoes WHERE acertos IS NULL
                   ORDER BY concurso_alvo"""
            ).fetchall()
        return [
            {
                "concurso_alvo": r["concurso_alvo"],
                "dezenas_sugeridas": json.loads(r["dezenas_sugeridas"]),
            }
            for r in rows
        ]
