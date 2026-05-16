"""Tests for dashboard server API endpoints."""
import json
from pathlib import Path

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


def test_api_dados_returns_200(client):
    r = client.get("/api/dados")
    assert r.status_code == 200


def test_api_dados_top_level_keys(client):
    d = json.loads(client.get("/api/dados").data)
    for key in ("total", "page", "per_page", "items", "clima_total", "lua_total"):
        assert key in d, f"missing key: {key}"


def test_api_dados_item_fields(client):
    d = json.loads(client.get("/api/dados?page=1&per_page=5").data)
    assert isinstance(d["items"], list)
    assert len(d["items"]) <= 5
    for item in d["items"]:
        for key in ("concurso", "data", "dezenas", "clima", "lua"):
            assert key in item, f"item missing key: {key}"


def test_api_dados_pagination_order(client):
    d1 = json.loads(client.get("/api/dados?page=1&per_page=5").data)
    d2 = json.loads(client.get("/api/dados?page=2&per_page=5").data)
    assert d1["page"] == 1
    assert d2["page"] == 2
    if d1["items"] and d2["items"]:
        assert d1["items"][0]["concurso"] > d2["items"][-1]["concurso"]


def test_api_jobs_poll_returns_lines(client, tmp_path, monkeypatch):
    reg = TreinoRegistry(tmp_path / "test_treinos.db")
    monkeypatch.setattr(server_module, "_registry", reg)
    reg.create_job("task_abc")
    reg.write_line("task_abc", "output line 1")
    reg.finish_job("task_abc", True)

    r = client.get("/api/jobs/task_abc/poll?offset=0")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["lines"] == ["output line 1"]
    assert data["done"] is True
    assert data["success"] is True


def test_api_jobs_poll_offset_advances(client, tmp_path, monkeypatch):
    reg = TreinoRegistry(tmp_path / "test_treinos.db")
    monkeypatch.setattr(server_module, "_registry", reg)
    reg.create_job("task_xyz")
    reg.write_line("task_xyz", "linha A")
    reg.write_line("task_xyz", "linha B")

    first = json.loads(client.get("/api/jobs/task_xyz/poll?offset=0").data)
    assert first["lines"] == ["linha A", "linha B"]

    second = json.loads(client.get(f"/api/jobs/task_xyz/poll?offset={first['next_offset']}").data)
    assert second["lines"] == []
    assert second["done"] is False


def test_api_jobs_poll_unknown_task(client, tmp_path, monkeypatch):
    reg = TreinoRegistry(tmp_path / "test_treinos.db")
    monkeypatch.setattr(server_module, "_registry", reg)

    r = client.get("/api/jobs/nonexistent_task/poll?offset=0")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["done"] is True
    assert data["success"] is False


def test_cancel_unknown_task_returns_404(client, monkeypatch):
    import lotofacil.interface.painel.server as srv
    monkeypatch.setattr(srv, "_procs", {})
    resp = client.post("/api/jobs/nao_existe/cancel")
    assert resp.status_code == 404
    data = resp.get_json()
    assert "error" in data


def test_cancel_running_task_terminates(client, monkeypatch):
    import lotofacil.interface.painel.server as srv

    class FakeProc:
        terminated = False
        def terminate(self):
            self.terminated = True

    fake = FakeProc()
    monkeypatch.setattr(srv, "_procs", {"task_abc": fake})
    resp = client.post("/api/jobs/task_abc/cancel")
    assert resp.status_code == 200
    assert fake.terminated is True
    data = resp.get_json()
    assert data.get("ok") is True


def test_api_models_status_returns_list(client):
    resp = client.get("/api/models/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_api_models_quality_returns_models_key(client):
    resp = client.get("/api/models/quality")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "models" in data
    assert isinstance(data["models"], list)


def test_api_treinos_iniciar_returns_ids(client, monkeypatch):
    import threading
    monkeypatch.setattr(threading, "Thread", lambda *a, **kw: type("T", (), {"start": lambda s: None})())
    resp = client.post(
        "/api/treinos/iniciar",
        json={"nome": "teste", "tipo_config": "base", "parametros": {"epochs": 10}},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "treino_id" in data
    assert "task_id" in data
