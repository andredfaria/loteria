"""Tests for the Mega-Sena dashboard Flask server."""
from functools import partial

import pytest

from megasena.infra.dados.banco import DatabaseManager
from megasena.interface.painel import server as painel_server


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
        db.upsert_concurso(2900, "30/09/2026", [5, 12, 23, 34, 45, 56])

        resp = client.get("/api/status")
        data = resp.get_json()

        assert data["total_concursos"] == 1
        assert data["ultimo_concurso"]["concurso"] == 2900
        assert data["ultimo_concurso"]["data"] == "30/09/2026"
        assert data["ultimo_concurso"]["dezenas"] == [5, 12, 23, 34, 45, 56]


def _seed_three_concursos(db):
    db.upsert_concurso(2898, "25/09/2026", [3, 14, 22, 38, 41, 60])
    db.upsert_concurso(2899, "27/09/2026", [7, 19, 27, 33, 50, 58])
    db.upsert_concurso(2900, "30/09/2026", [7, 14, 27, 36, 44, 59])


class TestApiFrequencia:
    def test_frequencia_empty(self, client, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        resp = client.get("/api/frequencia")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["total_concursos"] == 0
        assert data["frequencia"]["1"] == 0
        assert data["frequencia"]["60"] == 0
        assert len(data["frequencia"]) == 60

    def test_frequencia_with_data(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_three_concursos(DatabaseManager(db_path=db_path))

        resp = client.get("/api/frequencia")
        data = resp.get_json()

        assert data["total_concursos"] == 3
        assert data["frequencia"]["27"] == 2   # concursos 2899 e 2900
        assert data["frequencia"]["14"] == 2   # concursos 2898 e 2900
        assert data["frequencia"]["3"] == 1
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
        # 7 e 27 saíram no último concurso (2900) -> atraso 0
        assert data["atraso"]["7"] == {"atraso": 0, "ultimo_concurso": 2900}
        assert data["atraso"]["27"] == {"atraso": 0, "ultimo_concurso": 2900}
        # 19 saiu só no concurso 2899 (índice 1 de 3) -> atraso 1
        assert data["atraso"]["19"] == {"atraso": 1, "ultimo_concurso": 2899}
        # 3 saiu só no concurso 2898 (índice 0 de 3) -> atraso 2
        assert data["atraso"]["3"] == {"atraso": 2, "ultimo_concurso": 2898}
        # 1 nunca saiu -> atraso == total_concursos, sem último concurso
        assert data["atraso"]["1"] == {"atraso": 3, "ultimo_concurso": None}


class TestApiAtualizar:
    def test_atualizar_success(self, client, monkeypatch):
        class FakeFetcher:
            def __init__(self, *args, **kwargs):
                pass

            def sync_new_draws(self):
                return 3

        monkeypatch.setattr(painel_server, "MegasenaFetcher", FakeFetcher)

        resp = client.post("/api/atualizar")

        assert resp.status_code == 200
        assert resp.get_json() == {"novos": 3}

    def test_atualizar_failure(self, client, monkeypatch):
        class FakeFetcher:
            def __init__(self, *args, **kwargs):
                pass

            def sync_new_draws(self):
                raise RuntimeError("API indisponível")

        monkeypatch.setattr(painel_server, "MegasenaFetcher", FakeFetcher)

        resp = client.post("/api/atualizar")

        assert resp.status_code == 500
        # O detalhe da exceção fica no log, não na resposta: mensagens de erro
        # internas vazam caminhos e stack para quem chama a API.
        corpo = resp.get_json()["error"]
        assert "API indisponível" not in corpo
        assert corpo == "falha ao sincronizar concursos"


class TestIndex:
    def test_index_serves_html(self, client):
        resp = client.get("/")

        assert resp.status_code == 200
        assert resp.content_type.startswith("text/html")
        assert b"Mega-Sena" in resp.data


class TestApiBolao:
    def test_avalia_caso_do_guia(self, client):
        resp = client.post("/api/bolao/avaliar", json={
            "valor_total": 567, "apostas": 10, "dezenas": 7, "cotas": 10,
        })
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["custo_oficial"] == 420.0
        assert data["veredito"] == "aceitavel"
        assert data["por_cota"]["cobrado"] == 56.7

    def test_cotas_opcional(self, client):
        resp = client.post("/api/bolao/avaliar", json={
            "valor_total": 6, "apostas": 1, "dezenas": 6, "cotas": "",
        })
        assert resp.status_code == 200
        assert "por_cota" not in resp.get_json()

    @pytest.mark.parametrize("body,campo", [
        ({"apostas": 1, "dezenas": 6}, "valor_total"),
        ({"valor_total": 10, "apostas": 1, "dezenas": 21}, "dezenas"),
        ({"valor_total": 10, "apostas": 10**9, "dezenas": 6}, "apostas"),
        ({"valor_total": 10, "apostas": 1, "dezenas": 6, "cotas": 0}, "cotas"),
        ({"valor_total": -5, "apostas": 1, "dezenas": 6}, "valor_total"),
    ])
    def test_entradas_invalidas(self, client, body, campo):
        resp = client.post("/api/bolao/avaliar", json=body)
        assert resp.status_code == 400
        assert campo in resp.get_json()["error"]
