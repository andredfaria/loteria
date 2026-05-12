"""Tests for dashboard server API endpoints."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import dashboard.server as server_module

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "dados" / "sample"


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
