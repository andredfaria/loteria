"""O painel da Mega-Sena precisa falhar fechado.

Mesmo contrato dos painéis do lotofacil e da quina: sem uma decisão explícita
de segurança (`DASHBOARD_PASSWORD` ou `DASHBOARD_PUBLICO=1`) o processo não
sobe, e com senha configurada nenhuma rota de API responde sem sessão.
"""
from __future__ import annotations

from functools import partial

import pytest

from megasena.infra.dados.banco import DatabaseManager
from megasena.interface.painel import server as painel_server


class TestDecisaoDeStartup:
    """A decisão é pura, então dá para cobrir a matriz inteira."""

    @pytest.mark.parametrize(
        "password,publico,pular,esperado",
        [
            ("",       False, False, "blocked"),           # padrão: recusa subir
            ("",       True,  False, "ok_public"),         # público confirmado
            ("senha",  False, False, "ok_authenticated"),  # com senha
            ("senha",  True,  False, "ok_authenticated"),  # senha tem precedência
            ("",       False, True,  "skipped"),           # escape da suíte
        ],
    )
    def test_matriz(self, password, publico, pular, esperado):
        assert painel_server._decidir_auth_startup(password, publico, pular) == esperado


class TestStartupCheck:
    def test_sem_variaveis_recusa_iniciar(self, monkeypatch):
        monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
        monkeypatch.delenv("DASHBOARD_PUBLICO", raising=False)
        monkeypatch.delenv("DASHBOARD_SKIP_AUTH_CHECK", raising=False)
        with pytest.raises(SystemExit) as exc:
            painel_server._startup_auth_check()
        assert "DASHBOARD_PASSWORD" in str(exc.value)

    def test_publico_sobe_mas_avisa(self, monkeypatch, caplog):
        monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
        monkeypatch.delenv("DASHBOARD_SKIP_AUTH_CHECK", raising=False)
        monkeypatch.setenv("DASHBOARD_PUBLICO", "1")
        with caplog.at_level("WARNING"):
            painel_server._startup_auth_check()
        assert "SEM AUTENTICACAO" in caplog.text

    def test_senha_sem_auth_secret_avisa(self, monkeypatch, caplog):
        monkeypatch.setenv("DASHBOARD_PASSWORD", "s3nh4")
        monkeypatch.delenv("DASHBOARD_AUTH_SECRET", raising=False)
        monkeypatch.delenv("DASHBOARD_SKIP_AUTH_CHECK", raising=False)
        with caplog.at_level("WARNING"):
            painel_server._startup_auth_check()
        assert "DASHBOARD_AUTH_SECRET" in caplog.text


class TestGuardaDeRequisicao:
    @pytest.fixture
    def client(self):
        painel_server.app.config["TESTING"] = True
        with painel_server.app.test_client() as c:
            yield c

    def test_api_sem_sessao_retorna_401(self, client, monkeypatch):
        monkeypatch.setenv("DASHBOARD_PASSWORD", "s3nh4")
        resp = client.get("/api/status")
        assert resp.status_code == 401
        assert resp.get_json() == {"error": "unauthorized"}

    def test_atualizar_sem_sessao_bloqueia(self, client, monkeypatch):
        """A rota de escrita é a que mais importa."""
        monkeypatch.setenv("DASHBOARD_PASSWORD", "s3nh4")
        assert client.post("/api/atualizar").status_code == 401
        assert client.post("/api/bolao/avaliar").status_code == 401

    def test_pagina_sem_sessao_redireciona_para_login(self, client, monkeypatch):
        monkeypatch.setenv("DASHBOARD_PASSWORD", "s3nh4")
        resp = client.get("/")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_login_com_senha_correta_libera_api(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(
            painel_server, "DatabaseManager",
            partial(DatabaseManager, db_path=tmp_path / "test.db"),
        )
        monkeypatch.setenv("DASHBOARD_PASSWORD", "s3nh4")
        assert client.post("/login", data={"password": "errada"}).status_code == 200
        assert client.get("/api/status").status_code == 401
        client.post("/login", data={"password": "s3nh4"})
        assert client.get("/api/status").status_code == 200

    def test_sem_senha_configurada_permanece_aberto(self, client, monkeypatch, tmp_path):
        """Só alcançável com DASHBOARD_PUBLICO=1, garantido pelo startup check."""
        monkeypatch.setattr(
            painel_server, "DatabaseManager",
            partial(DatabaseManager, db_path=tmp_path / "test.db"),
        )
        monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
        assert client.get("/api/status").status_code == 200

    def test_healthz_sem_sessao_responde_200(self, client, monkeypatch):
        """O HEALTHCHECK do Docker não tem sessão: /healthz precisa responder."""
        monkeypatch.setenv("DASHBOARD_PASSWORD", "s3nh4")
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}

    def test_healthz_nao_abre_o_resto(self, client, monkeypatch):
        monkeypatch.setenv("DASHBOARD_PASSWORD", "s3nh4")
        client.get("/healthz")
        assert client.get("/api/status").status_code == 401
        assert client.get("/").status_code == 302

    def test_healthz_nao_toca_no_banco(self, client, monkeypatch):
        """Primeiro boot com volume vazio ou banco quebrado: continua saudável."""
        def explode(*a, **k):
            raise RuntimeError("banco indisponível")
        monkeypatch.setattr(painel_server, "DatabaseManager", explode)
        monkeypatch.setenv("DASHBOARD_PASSWORD", "s3nh4")
        assert client.get("/healthz").status_code == 200
