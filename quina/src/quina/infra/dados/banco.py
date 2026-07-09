"""SQLite persistence layer for Quina data."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional

from quina.infra.config import DB_PATH

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

                CREATE TABLE IF NOT EXISTS estrategias_backtest (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    estrategia      TEXT NOT NULL,
                    janela          INTEGER NOT NULL,
                    metricas_json   TEXT NOT NULL,
                    criado_em       TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS jogos_gerados (
                    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                    estrategia               TEXT NOT NULL,
                    tamanho_aposta           INTEGER NOT NULL,
                    dezenas_json             TEXT NOT NULL,
                    score                    REAL,
                    custo                    REAL NOT NULL,
                    criado_em                TEXT DEFAULT (datetime('now')),
                    concurso_alvo_validacao  INTEGER,
                    acertos                  INTEGER
                );
            """)
        logger.debug("Database initialised at %s", self.db_path)

    # -- Concursos --------------------------------------------------------------

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

    # -- Estrategias / backtest --------------------------------------------------

    def salvar_backtest(self, estrategia: str, janela: int, metricas: dict) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO estrategias_backtest (estrategia, janela, metricas_json) VALUES (?, ?, ?)",
                (estrategia, janela, json.dumps(metricas)),
            )
        return cur.lastrowid

    def listar_backtests(self, limite: int = 20) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, estrategia, janela, metricas_json, criado_em
                   FROM estrategias_backtest ORDER BY id DESC LIMIT ?""",
                (limite,),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "estrategia": r["estrategia"],
                "janela": r["janela"],
                "metricas": json.loads(r["metricas_json"]),
                "criado_em": r["criado_em"],
            }
            for r in rows
        ]

    # -- Jogos gerados ------------------------------------------------------------

    def salvar_jogo_gerado(
        self,
        estrategia: str,
        tamanho_aposta: int,
        dezenas: List[int],
        score: Optional[float],
        custo: float,
        concurso_alvo_validacao: Optional[int] = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO jogos_gerados
                   (estrategia, tamanho_aposta, dezenas_json, score, custo, concurso_alvo_validacao)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (estrategia, tamanho_aposta, json.dumps(sorted(dezenas)), score, custo, concurso_alvo_validacao),
            )
        return cur.lastrowid

    def listar_jogos_gerados(self, limite: int = 50, offset: int = 0) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, estrategia, tamanho_aposta, dezenas_json, score, custo,
                          criado_em, concurso_alvo_validacao, acertos
                   FROM jogos_gerados ORDER BY id DESC LIMIT ? OFFSET ?""",
                (limite, offset),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "estrategia": r["estrategia"],
                "tamanho_aposta": r["tamanho_aposta"],
                "dezenas": json.loads(r["dezenas_json"]),
                "score": r["score"],
                "custo": r["custo"],
                "criado_em": r["criado_em"],
                "concurso_alvo_validacao": r["concurso_alvo_validacao"],
                "acertos": r["acertos"],
            }
            for r in rows
        ]

    def atualizar_acertos_pendentes(self, concurso: int, dezenas_sorteadas: List[int]) -> int:
        sorteadas = set(dezenas_sorteadas)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, dezenas_json FROM jogos_gerados WHERE concurso_alvo_validacao = ? AND acertos IS NULL",
                (concurso,),
            ).fetchall()
            for r in rows:
                dezenas_jogo = json.loads(r["dezenas_json"])
                acertos = len(set(dezenas_jogo) & sorteadas)
                conn.execute("UPDATE jogos_gerados SET acertos = ? WHERE id = ?", (acertos, r["id"]))
        return len(rows)
