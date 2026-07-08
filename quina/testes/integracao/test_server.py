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


def _seed_three_concursos(db):
    db.upsert_concurso(7057, "04/07/2026", [34, 38, 47, 63, 75])
    db.upsert_concurso(7058, "06/07/2026", [8, 26, 27, 66, 79])
    db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])


class TestApiFrequencia:
    def test_frequencia_empty(self, client, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        resp = client.get("/api/frequencia")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["total_concursos"] == 0
        assert data["frequencia"]["1"] == 0
        assert data["frequencia"]["80"] == 0
        assert len(data["frequencia"]) == 80

    def test_frequencia_with_data(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_three_concursos(DatabaseManager(db_path=db_path))

        resp = client.get("/api/frequencia")
        data = resp.get_json()

        assert data["total_concursos"] == 3
        assert data["frequencia"]["27"] == 2   # concursos 7058 e 7059
        assert data["frequencia"]["47"] == 2   # concursos 7057 e 7059
        assert data["frequencia"]["34"] == 1
        assert data["frequencia"]["1"] == 0    # nunca sorteado


class TestApiAtraso:
    def test_atraso_empty(self, client, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        resp = client.get("/api/atraso")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["total_concursos"] == 0
        assert data["atraso"]["1"] == {"atraso": 0, "ultimo_concurso": None}

    def test_atraso_with_data(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_three_concursos(DatabaseManager(db_path=db_path))

        resp = client.get("/api/atraso")
        data = resp.get_json()

        assert data["total_concursos"] == 3
        # 27 e 47 saíram no último concurso (7059) -> atraso 0
        assert data["atraso"]["27"] == {"atraso": 0, "ultimo_concurso": 7059}
        assert data["atraso"]["47"] == {"atraso": 0, "ultimo_concurso": 7059}
        # 8 saiu só no concurso 7058 (índice 1 de 3) -> atraso 1
        assert data["atraso"]["8"] == {"atraso": 1, "ultimo_concurso": 7058}
        # 34 saiu só no concurso 7057 (índice 0 de 3) -> atraso 2
        assert data["atraso"]["34"] == {"atraso": 2, "ultimo_concurso": 7057}
        # 1 nunca saiu -> atraso == total_concursos, sem último concurso
        assert data["atraso"]["1"] == {"atraso": 3, "ultimo_concurso": None}
