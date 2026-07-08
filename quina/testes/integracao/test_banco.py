import json
import sqlite3

import pytest

from quina.infra.dados.banco import DatabaseManager


@pytest.fixture
def db(tmp_path):
    return DatabaseManager(db_path=tmp_path / "test_quina.db")


class TestDatabaseManager:
    def test_empty_db(self, db):
        assert db.count_concursos() == 0
        assert db.get_latest_concurso() is None
        assert db.get_all_concursos() == []

    def test_upsert_and_count(self, db):
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        assert db.count_concursos() == 1

    def test_upsert_sorts_dezenas(self, db):
        db.upsert_concurso(7059, "07/07/2026", [78, 27, 70, 47, 57])
        latest = db.get_latest_concurso()
        assert latest["dezenas"] == [27, 47, 57, 70, 78]

    def test_upsert_is_idempotent(self, db):
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        assert db.count_concursos() == 1

    def test_upsert_updates_existing(self, db):
        db.upsert_concurso(7059, "07/07/2026", [1, 2, 3, 4, 5])
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        latest = db.get_latest_concurso()
        assert latest["dezenas"] == [27, 47, 57, 70, 78]

    def test_get_latest_concurso(self, db):
        db.upsert_concurso(7058, "06/07/2026", [8, 26, 27, 66, 79])
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        latest = db.get_latest_concurso()
        assert latest["concurso"] == 7059

    def test_get_all_concursos_ordered(self, db):
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        db.upsert_concurso(7035, "26/05/2026", [14, 15, 48, 58, 73])
        all_c = db.get_all_concursos()
        assert [c["concurso"] for c in all_c] == [7035, 7059]

    def test_raw_json_persisted(self, tmp_path):
        db_path = tmp_path / "test_raw.db"
        db = DatabaseManager(db_path=db_path)
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78], raw={"loteria": "quina"})
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT raw_json FROM concursos WHERE concurso=7059").fetchone()
        conn.close()
        assert json.loads(row[0]) == {"loteria": "quina"}

    def test_predicoes_table_exists(self, db):
        conn = sqlite3.connect(db.db_path)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='predicoes'"
        ).fetchone()
        conn.close()
        assert row is not None
