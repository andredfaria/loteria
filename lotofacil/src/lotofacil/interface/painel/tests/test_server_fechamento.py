"""Tests for the /api/fechamento endpoint (covering design)."""
import json
import time

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


def _wait_result(client, task_id):
    for _ in range(300):
        response = client.get(f"/api/jobs/{task_id}/result")
        if response.status_code == 200:
            return json.loads(response.data)
        time.sleep(0.01)
    pytest.fail("background job did not finish")


def test_fechamento_returns_expected_shape(client, tmp_path, monkeypatch):
    monkeypatch.setattr(server_module, "_registry", TreinoRegistry(tmp_path / "jobs.db"))
    monkeypatch.setattr(server_module, "_JOB_RESULTS_DIR", tmp_path / "results")
    r = client.post("/api/fechamento", json={"pool_size": 16, "jogos": 4})
    assert r.status_code == 202, r.data
    task_id = json.loads(r.data)["task_id"]
    job = _wait_result(client, task_id)
    assert job["success"] is True
    d = job["result"]
    for key in ("pool", "jogos", "curva_garantia", "custo_total", "nota_ev", "concurso_alvo"):
        assert key in d, f"missing key: {key}"
    assert len(d["jogos"]) == 4
    assert len(d["pool"]) == 16
    assert all(len(j) == 15 for j in d["jogos"])


def test_fechamento_respeita_override(client, tmp_path, monkeypatch):
    monkeypatch.setattr(server_module, "_registry", TreinoRegistry(tmp_path / "jobs.db"))
    monkeypatch.setattr(server_module, "_JOB_RESULTS_DIR", tmp_path / "results")
    r = client.post(
        "/api/fechamento",
        json={"pool_size": 16, "jogos": 2, "fixar": [20, 22], "excluir": [1, 2, 3]},
    )
    assert r.status_code == 202, r.data
    task_id = json.loads(r.data)["task_id"]
    d = _wait_result(client, task_id)["result"]
    assert {20, 22} <= set(d["pool"])
    assert not (set(d["pool"]) & {1, 2, 3})


def test_fechamento_erro_entrada_invalida(client):
    r = client.post("/api/fechamento", json={"pool_size": 14, "jogos": 4})
    assert r.status_code == 400
    assert "error" in json.loads(r.data)


def test_index_serve_aba_geracao(client):
    html = client.get("/").data.decode("utf-8")
    assert "tab-geracao" in html
    assert "renderGeracao" in html
    assert "/api/fechamento" in html
