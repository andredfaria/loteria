"""Tests for the new Quina dashboard routes: treinos, jogos, fechamento, portfolio."""
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


def _seed_draws(db):
    db.upsert_concurso(1, "01/01/2026", [1, 2, 3, 4, 5])
    db.upsert_concurso(2, "02/01/2026", [6, 7, 8, 9, 10])
    db.upsert_concurso(3, "03/01/2026", [11, 12, 13, 14, 15])


class TestApiTreinos:
    def test_iniciar_dados_insuficientes(self, client, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        resp = client.post("/api/treinos/iniciar", json={"estrategia": "filtros", "janela": 5})

        assert resp.status_code == 400

    def test_iniciar_com_dados(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        resp = client.post("/api/treinos/iniciar", json={"estrategia": "frequencia_atraso", "janela": 2})
        data = resp.get_json()

        assert resp.status_code == 200
        assert "job_id" in data
        assert data["resultado"]["total_rodadas"] == 2

    def test_iniciar_estrategia_invalida(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        resp = client.post("/api/treinos/iniciar", json={"estrategia": "inexistente"})

        assert resp.status_code == 400

    def test_listar(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.salvar_backtest("filtros", 100, {"x": 1})

        resp = client.get("/api/treinos")
        data = resp.get_json()

        assert resp.status_code == 200
        assert len(data["backtests"]) == 1


class TestApiJogos:
    def test_gerar_dados_insuficientes(self, client, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        resp = client.post("/api/jogos/gerar", json={"estrategia": "filtros", "tamanho_aposta": 5, "quantidade": 3})

        assert resp.status_code == 400

    def test_gerar_com_dados(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        resp = client.post("/api/jogos/gerar", json={"estrategia": "filtros", "tamanho_aposta": 5, "quantidade": 3})
        data = resp.get_json()

        assert resp.status_code == 200
        assert len(data["jogos"]) == 3
        assert all(len(j["dezenas"]) == 5 for j in data["jogos"])

    def test_listar(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.salvar_jogo_gerado(estrategia="filtros", tamanho_aposta=5, dezenas=[1, 2, 3, 4, 5], score=0.5, custo=3.0)

        resp = client.get("/api/jogos")
        data = resp.get_json()

        assert resp.status_code == 200
        assert len(data["jogos"]) == 1


class TestApiFechamento:
    def test_fechamento_valido(self, client):
        resp = client.post("/api/fechamento", json={"dezenas": [1, 2, 3, 4, 5], "k": 5, "faixa": 5})
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["quantidade"] == 1
        assert data["custo_total"] == 3.0

    def test_fechamento_pool_invalido(self, client):
        resp = client.post("/api/fechamento", json={"dezenas": [1, 2, 3], "k": 3, "faixa": 3})

        assert resp.status_code == 400


class TestApiPortfolio:
    def test_portfolio_dados_insuficientes(self, client, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        resp = client.post("/api/portfolio", json={"orcamento": 100, "perfil": "conservador"})

        assert resp.status_code == 400

    def test_portfolio_com_dados(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        resp = client.post("/api/portfolio", json={"orcamento": 30, "perfil": "conservador"})
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["custo_total"] <= 30
