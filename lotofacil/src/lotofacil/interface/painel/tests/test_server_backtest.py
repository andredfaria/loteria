"""Tests for the /api/backtests/* endpoints (walk-forward backtest jobs)."""
import json

import pytest

from lotofacil.interface.painel import server as server_module
from lotofacil.interface.painel.treino_registry import TreinoRegistry
from lotofacil.infra.config import DADOS_DIR

SAMPLE_DIR = DADOS_DIR / "sample"


@pytest.fixture(autouse=True)
def patch_dados_dir(monkeypatch):
    monkeypatch.setattr(server_module, "DADOS_DIR", SAMPLE_DIR)


@pytest.fixture
def client():
    server_module.app.testing = True
    with server_module.app.test_client() as c:
        yield c


@pytest.fixture
def reg(tmp_path, monkeypatch):
    r = TreinoRegistry(tmp_path / "test_treinos.db")
    monkeypatch.setattr(server_module, "_registry", r)
    return r


def test_iniciar_rejeita_configs_vazias(client, reg):
    r = client.post("/api/backtests/iniciar", json={"configs": [], "start": 3641, "end": 3645})
    assert r.status_code == 400


def test_iniciar_rejeita_config_desconhecida(client, reg):
    r = client.post(
        "/api/backtests/iniciar",
        json={"configs": ["nao_existe"], "start": 3641, "end": 3645},
    )
    assert r.status_code == 400


def test_iniciar_rejeita_start_maior_que_end(client, reg):
    r = client.post(
        "/api/backtests/iniciar",
        json={"configs": ["base+temp+priors"], "start": 3645, "end": 3641},
    )
    assert r.status_code == 400


def test_iniciar_rejeita_end_alem_do_disponivel(client, reg):
    r = client.post(
        "/api/backtests/iniciar",
        json={"configs": ["base+temp+priors"], "start": 3641, "end": 99999},
    )
    assert r.status_code == 400


def test_iniciar_retorna_ids(client, reg, monkeypatch):
    import threading
    monkeypatch.setattr(threading, "Thread", lambda *a, **kw: type("T", (), {"start": lambda s: None})())
    r = client.post(
        "/api/backtests/iniciar",
        json={"configs": ["base+temp+priors"], "start": 3641, "end": 3645, "retrain_every": 25},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "backtest_id" in data
    assert "task_id" in data
    bt = reg.buscar_backtest(data["backtest_id"])
    assert bt["status"] == "running"
    assert bt["configs"] == ["base+temp+priors"]


def test_listar_backtests(client, reg):
    reg.criar_backtest("bt_1", ["base+temp+priors"], 3641, 3645, 25)
    r = client.get("/api/backtests")
    assert r.status_code == 200
    data = r.get_json()
    assert any(b["id"] == "bt_1" for b in data)


def test_detalhe_backtest_nao_encontrado(client, reg):
    r = client.get("/api/backtests/nao_existe")
    assert r.status_code == 404


def test_detalhe_backtest_inclui_resultado(client, reg, tmp_path):
    reg.criar_backtest("bt_2", ["base+temp+priors"], 3641, 3645, 25)
    resultado_path = tmp_path / "backtest_bt_2.json"
    resultado_path.write_text(json.dumps({"report": {"results": []}, "warnings": []}))
    reg.registrar_resultado_backtest("bt_2", str(resultado_path))

    r = client.get("/api/backtests/bt_2")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "completed"
    assert data["resultado"]["report"]["results"] == []


def test_deletar_backtest(client, reg):
    reg.criar_backtest("bt_3", ["base+temp+priors"], 3641, 3645, 25)
    r = client.delete("/api/backtests/bt_3")
    assert r.status_code == 200
    assert reg.buscar_backtest("bt_3") is None


def test_deletar_backtest_nao_encontrado(client, reg):
    r = client.delete("/api/backtests/nao_existe")
    assert r.status_code == 404
