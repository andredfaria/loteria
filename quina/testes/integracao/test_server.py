"""Tests for the Quina dashboard Flask server."""
from functools import partial

import pytest

from quina.infra.dados.banco import DatabaseManager
from quina.interface.painel import server as painel_server


def _patch_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(painel_server, "DatabaseManager", partial(DatabaseManager, db_path=db_path))
    return db_path


@pytest.fixture
def client():
    painel_server.app.config["TESTING"] = True
    return painel_server.app.test_client()


class TestApiStatus:
    def test_status_empty(self, client, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        resp = client.get("/api/status")

        assert resp.status_code == 200
        assert resp.get_json() == {"total_concursos": 0, "ultimo_concurso": None}

    def test_status_with_data(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])

        resp = client.get("/api/status")
        data = resp.get_json()

        assert data["total_concursos"] == 1
        assert data["ultimo_concurso"]["concurso"] == 7059
        assert data["ultimo_concurso"]["data"] == "07/07/2026"
        assert data["ultimo_concurso"]["dezenas"] == [27, 47, 57, 70, 78]
