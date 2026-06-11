"""Tests for dashboard server API endpoints."""
import json
import sqlite3 as _sqlite3
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


@pytest.mark.parametrize(
    "linha, esperado",
    [
        (
            "EPOCH_PROGRESS: 5/40 loss=0.6931 val_loss=0.7012",
            {"epoch_atual": 5, "epoch_total": 40, "loss": 0.6931, "val_loss_atual": 0.7012},
        ),
        (
            "[12:30:01] EPOCH_PROGRESS: 1/15 loss=1.2000 val_loss=1.1500",
            {"epoch_atual": 1, "epoch_total": 15, "loss": 1.2, "val_loss_atual": 1.15},
        ),
        ("188/188 [==============================] - 2s 11ms/step - loss: 0.6931 - val_loss: 0.6931", None),
        ("Epoch 5/40", None),
    ],
)
def test_parse_epoch_progress(linha, esperado):
    assert server_module.parse_epoch_progress(linha) == esperado


def test_api_jobs_poll_inclui_progress(client, tmp_path, monkeypatch):
    reg = TreinoRegistry(tmp_path / "test_treinos.db")
    monkeypatch.setattr(server_module, "_registry", reg)
    reg.create_job("task_progress")
    reg.write_line("task_progress", "EPOCH_PROGRESS: 3/10 loss=0.5 val_loss=0.6")
    reg.update_progress(
        "task_progress",
        {"epoch_atual": 3, "epoch_total": 10, "loss": 0.5, "val_loss_atual": 0.6, "eta_segundos": 42},
    )

    r = client.get("/api/jobs/task_progress/poll?offset=0")
    data = json.loads(r.data)
    assert data["progress"] == {
        "epoch_atual": 3, "epoch_total": 10, "loss": 0.5, "val_loss_atual": 0.6, "eta_segundos": 42,
    }


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


def test_api_models_quality_inclui_cache_info(client):
    resp = client.get("/api/models/quality?last_n=50")
    assert resp.status_code == 200
    cache_info = resp.get_json()["cache_info"]
    assert cache_info["age_seconds"] == 0
    assert cache_info["ttl_seconds"] == server_module._QUALITY_TTL
    assert "cached_at" in cache_info

    cached_resp = client.get("/api/models/quality?last_n=50")
    assert cached_resp.get_json()["cache_info"]["age_seconds"] >= 0

    refreshed = client.get("/api/models/quality?last_n=50&refresh=1")
    assert refreshed.get_json()["cache_info"]["age_seconds"] == 0


def test_api_dados_frequencia_inclui_cache_info(client):
    resp = client.get("/api/dados/frequencia")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "frequency" in data
    cache_info = data["cache_info"]
    assert cache_info["ttl_seconds"] == server_module._FREQ_TTL
    assert cache_info["age_seconds"] == 0

    refreshed = client.get("/api/dados/frequencia?refresh=1")
    assert refreshed.get_json()["cache_info"]["age_seconds"] == 0


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


def test_api_treinos_iniciar_epochs_invalido_retorna_erro_validacao(client):
    resp = client.post(
        "/api/treinos/iniciar",
        json={"nome": "teste", "tipo_config": "base", "parametros": {"epochs": 2000}},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["erro"]["tipo"] == "validacao"
    assert "epochs" in data["erro"]["mensagem"]


def test_api_treinos_iniciar_window_size_invalido_retorna_erro_validacao(client):
    resp = client.post(
        "/api/treinos/iniciar",
        json={"nome": "teste", "tipo_config": "base", "parametros": {"window_size": 999}},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["erro"]["tipo"] == "validacao"
    assert "window_size" in data["erro"]["mensagem"]


def test_compute_acertos_with_matching_numbers():
    jogos = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]]
    real = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    result = server_module._compute_acertos(jogos, real)
    assert result == [15]


def test_compute_acertos_returns_none_when_no_real():
    jogos = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]]
    result = server_module._compute_acertos(jogos, None)
    assert result is None


def test_compute_acertos_partial_hits():
    jogos = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
             [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 1, 2, 3, 4, 5]]
    real = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    result = server_module._compute_acertos(jogos, real)
    assert result == [15, 5]


def test_get_draw_dezenas_returns_list(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    with _sqlite3.connect(str(db)) as conn:
        conn.execute("CREATE TABLE concursos (concurso INTEGER, dezenas TEXT)")
        conn.execute(
            "INSERT INTO concursos VALUES (?, ?)",
            (1000, '[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]'),
        )
    monkeypatch.setattr(server_module, "DB_PATH", db)
    result = server_module._get_draw_dezenas(1000)
    assert result == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]


def test_get_draw_dezenas_returns_none_for_missing(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    with _sqlite3.connect(str(db)) as conn:
        conn.execute("CREATE TABLE concursos (concurso INTEGER, dezenas TEXT)")
    monkeypatch.setattr(server_module, "DB_PATH", db)
    result = server_module._get_draw_dezenas(9999)
    assert result is None


def test_compute_acertos_returns_none_when_empty_dezenas():
    jogos = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]]
    result = server_module._compute_acertos(jogos, [])
    assert result is None


def test_compute_acertos_returns_empty_list_when_no_jogos():
    result = server_module._compute_acertos([], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
    assert result == []


def test_api_jogos_gerados_series_agrega_por_modelo_e_concurso(client, tmp_path, monkeypatch):
    reg = TreinoRegistry(tmp_path / "test_treinos.db")
    monkeypatch.setattr(server_module, "_registry", reg)

    db = tmp_path / "concursos.db"
    real = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    with _sqlite3.connect(str(db)) as conn:
        conn.execute("CREATE TABLE concursos (concurso INTEGER, dezenas TEXT)")
        conn.execute("INSERT INTO concursos VALUES (?, ?)", (101, json.dumps(real)))
        conn.execute("INSERT INTO concursos VALUES (?, ?)", (102, json.dumps(real)))
    monkeypatch.setattr(server_module, "DB_PATH", db)

    # modelo "ml": 101 -> 1 jogo com 15 acertos; 102 -> 1 jogo com 5 acertos
    reg.salvar_jogo("t1", "ml", 101, [real])
    reg.salvar_jogo("t1", "ml", 102, [[16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 1, 2, 3, 4, 5]])
    # modelo "neural": 101 -> 1 jogo com 9 acertos
    reg.salvar_jogo("t2", "neural", 101, [[1, 2, 3, 4, 5, 6, 7, 8, 9, 16, 17, 18, 19, 20, 21]])

    r = client.get("/api/jogos-gerados/series")
    assert r.status_code == 200
    data = json.loads(r.data)

    assert data["baseline_aleatorio"] == 9
    assert data["menor_premio"] == 11
    assert data["series"]["ml"] == [
        {"concurso": 101, "media_acertos": 15.0},
        {"concurso": 102, "media_acertos": 5.0},
    ]
    assert data["series"]["neural"] == [{"concurso": 101, "media_acertos": 9.0}]


# ── Atraso das dezenas ────────────────────────────────────────

def test_api_dados_atraso_retorna_200(client):
    resp = client.get("/api/dados/atraso")
    assert resp.status_code == 200


def test_api_dados_atraso_chaves(client):
    data = json.loads(client.get("/api/dados/atraso").data)
    assert "atraso" in data
    assert "total_sorteios" in data
    # each number should have atraso key
    for n in range(1, 26):
        assert str(n) in data["atraso"]
        assert "atraso" in data["atraso"][str(n)]


# ── ROI Lab endpoints ──────────────────────────────────────────

def test_api_roi_backtest_retorna_200(client):
    from unittest.mock import patch

    fake_draws = [
        {"concurso": i, "data": "01/01/2020", "dezenas": list(range(i, i + 15))}
        for i in range(1, 4)
    ]
    with patch("lotofacil.servicos.roi_lab.DatabaseManager") as MockDB:
        MockDB.return_value.get_all_concursos.return_value = fake_draws
        resp = client.post(
            "/api/roi/backtest",
            json={"filtros": {"soma": [171, 220]}, "n_jogos": 2, "janela": None},
        )
    assert resp.status_code == 200


def test_api_roi_backtest_chaves_resposta(client):
    from unittest.mock import patch

    fake_draws = [{"concurso": 1, "data": "01/01/2020", "dezenas": list(range(1, 16))}]
    with patch("lotofacil.servicos.roi_lab.DatabaseManager") as MockDB:
        MockDB.return_value.get_all_concursos.return_value = fake_draws
        data = json.loads(client.post("/api/roi/backtest", json={"filtros": {}, "n_jogos": 1}).data)
    assert "estrategia" in data
    assert "baseline" in data
    assert "roi_pct" in data["estrategia"]


def test_api_roi_strategies_vazio(client, tmp_path, monkeypatch):
    monkeypatch.setattr(server_module, "_ROI_STRATEGIES_PATH", tmp_path / "roi.json")
    resp = client.get("/api/roi/strategies")
    assert resp.status_code == 200
    assert json.loads(resp.data) == []


def test_api_roi_strategies_salvar_e_listar(client, tmp_path, monkeypatch):
    monkeypatch.setattr(server_module, "_ROI_STRATEGIES_PATH", tmp_path / "roi.json")
    payload = {"nome": "teste-a", "filtros": {"soma": [171, 220]}, "resumo": {"roi_pct": -15.0}}
    r = client.post("/api/roi/strategies", json=payload)
    assert r.status_code == 200
    lista = json.loads(client.get("/api/roi/strategies").data)
    assert len(lista) == 1
    assert lista[0]["nome"] == "teste-a"


def test_api_roi_strategies_salvar_sobrescreve_mesmo_nome(client, tmp_path, monkeypatch):
    monkeypatch.setattr(server_module, "_ROI_STRATEGIES_PATH", tmp_path / "roi.json")
    payload = {"nome": "teste-a", "filtros": {}, "resumo": {"roi_pct": -10.0}}
    client.post("/api/roi/strategies", json=payload)
    payload["resumo"]["roi_pct"] = -5.0
    client.post("/api/roi/strategies", json=payload)
    lista = json.loads(client.get("/api/roi/strategies").data)
    assert len(lista) == 1
    assert lista[0]["resumo"]["roi_pct"] == -5.0


def test_api_roi_strategies_deletar(client, tmp_path, monkeypatch):
    monkeypatch.setattr(server_module, "_ROI_STRATEGIES_PATH", tmp_path / "roi.json")
    client.post("/api/roi/strategies", json={"nome": "teste-a", "filtros": {}, "resumo": {}})
    r = client.delete("/api/roi/strategies/teste-a")
    assert r.status_code == 200
    lista = json.loads(client.get("/api/roi/strategies").data)
    assert lista == []


# ── SSE streaming ──────────────────────────────────────────────

def test_api_job_stream_emite_linhas_e_done(client, tmp_path, monkeypatch):
    """SSE endpoint emite linhas de output e finaliza com event: done."""
    from lotofacil.interface.painel.treino_registry import TreinoRegistry
    reg = TreinoRegistry(tmp_path / "test.db")
    reg.create_job("test_sse")
    reg.write_line("test_sse", "linha 1")
    reg.write_line("test_sse", "linha 2")
    reg.finish_job("test_sse", success=True)
    monkeypatch.setattr(server_module, "_registry", reg)

    resp = client.get("/api/jobs/test_sse/stream")
    assert resp.status_code == 200
    assert b"linha 1" in resp.data
    assert b"linha 2" in resp.data
    assert b"event: done" in resp.data
    assert b'"success": true' in resp.data or b'"success":true' in resp.data
    assert resp.content_type.startswith("text/event-stream")


def test_api_job_stream_job_inexistente_retorna_done(client, tmp_path, monkeypatch):
    """SSE com task_id desconhecido emite event: done imediatamente."""
    from lotofacil.interface.painel.treino_registry import TreinoRegistry
    reg = TreinoRegistry(tmp_path / "test.db")
    monkeypatch.setattr(server_module, "_registry", reg)

    resp = client.get("/api/jobs/nao_existe/stream")
    assert resp.status_code == 200
    assert b"event: done" in resp.data


# ── Autenticação ───────────────────────────────────────────────

def test_sem_password_nao_requer_auth(client):
    """Sem DASHBOARD_PASSWORD configurada, dashboard abre sem login."""
    resp = client.get("/")
    assert resp.status_code == 200


def test_com_password_redireciona_para_login(client, monkeypatch):
    """Com DASHBOARD_PASSWORD definida, GET / sem sessão → 302 para /login."""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "teste123")
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_correto_cria_sessao(client, monkeypatch):
    """POST /login com senha correta → redireciona para /."""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "teste123")
    resp = client.post("/login", data={"password": "teste123"}, follow_redirects=False)
    assert resp.status_code == 302


def test_login_errado_retorna_erro(client, monkeypatch):
    """POST /login com senha errada → 200 com mensagem de erro."""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "teste123")
    resp = client.post("/login", data={"password": "errada"})
    assert resp.status_code == 200
    assert b"incorreta" in resp.data.lower() or b"senha" in resp.data.lower()


def test_api_sem_sessao_retorna_401(client, monkeypatch):
    """Com auth ativa, GET /api/status sem sessão → 401 JSON."""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "teste123")
    resp = client.get("/api/status")
    assert resp.status_code == 401
    data = json.loads(resp.data)
    assert "error" in data


def test_logout_limpa_sessao(client, monkeypatch):
    """Após login + logout, GET / redireciona novamente para /login."""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "teste123")
    client.post("/login", data={"password": "teste123"})
    client.get("/logout")
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# ── _extract_model_path_from_output ──────────────────────────────

def test_extract_path_same_line():
    lines = ["TREINO_MODELO_PATH: /home/user/models/neural_abc.keras"]
    result = server_module._extract_model_path_from_output(lines)
    assert result == "/home/user/models/neural_abc.keras"


def test_extract_path_next_line():
    lines = [
        "Saved: neural_test.keras",
        "TREINO_MODELO_PATH: ",
        "/home/user/models/neural_test.keras",
    ]
    result = server_module._extract_model_path_from_output(lines)
    assert result == "/home/user/models/neural_test.keras"


def test_extract_path_not_found():
    lines = ["Config: base", "Training... (this may take a while)"]
    result = server_module._extract_model_path_from_output(lines)
    assert result is None


def _escrever_concurso(dados_dir, concurso, data, dezenas):
    import json
    dados_dir.mkdir(parents=True, exist_ok=True)
    path = dados_dir / f"concurso_{concurso}.json"
    path.write_text(json.dumps({"concurso": concurso, "data": data, "dezenas": dezenas}), encoding="utf-8")


@pytest.fixture(autouse=True)
def _clear_predicao_proxima_cache():
    server_module._predicao_proxima_cache.clear()
    yield
    server_module._predicao_proxima_cache.clear()


def test_api_predicao_proxima_returns_payload(client, tmp_path, monkeypatch):
    _escrever_concurso(tmp_path, 100, "26/06/2024", list(range(1, 16)))
    _escrever_concurso(tmp_path, 101, "27/06/2024", list(range(2, 17)))
    _escrever_concurso(tmp_path, 102, "28/06/2024", list(range(3, 18)))
    monkeypatch.setattr(server_module, "DADOS_DIR", tmp_path)

    r = client.get("/api/predicao/proxima")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["concurso_alvo"] == 103
    assert len(data["dezenas"]) == 15
    assert data["baseline_esperado"] == 9.0
    assert "modelo" in data and "abordagem" in data


def test_api_predicao_proxima_sem_dados_retorna_400(client, tmp_path, monkeypatch):
    monkeypatch.setattr(server_module, "DADOS_DIR", tmp_path)

    r = client.get("/api/predicao/proxima")
    assert r.status_code == 400
    data = json.loads(r.data)
    assert data["erro"]["tipo"] == "validacao"
