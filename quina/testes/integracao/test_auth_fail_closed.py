"""O painel da Quina precisa falhar fechado e limitar entradas.

Estes testes existem porque a versão anterior deste painel expunha onze rotas
— incluindo `POST /api/atualizar`, `POST /api/treinos/iniciar` e
`POST /api/jogos/gerar` — sem autenticação nenhuma e sem teto nos parâmetros.
Como o repositório é público, quem clonasse e implantasse herdava a exposição.
"""
from __future__ import annotations

import pytest

from quina.interface.painel import server as painel_server


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

    def test_padrao_e_bloquear(self):
        """Nenhuma variável definida = não sobe. É o ponto inteiro do fix."""
        assert painel_server._decidir_auth_startup("", False, False) == "blocked"


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

    def test_post_sem_sessao_tambem_bloqueia(self, client, monkeypatch):
        """As rotas de escrita são as que mais importam."""
        monkeypatch.setenv("DASHBOARD_PASSWORD", "s3nh4")
        for rota in ("/api/atualizar", "/api/treinos/iniciar", "/api/jogos/gerar"):
            assert client.post(rota).status_code == 401, rota

    def test_sem_senha_configurada_permanece_aberto(self, client, monkeypatch):
        """Só alcançável com DASHBOARD_PUBLICO=1, garantido pelo startup check."""
        monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
        assert client.get("/api/status").status_code == 200


class TestLimitesDeEntrada:
    """Cada endpoint pesado precisa recusar parâmetros absurdos."""

    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
        painel_server.app.config["TESTING"] = True
        with painel_server.app.test_client() as c:
            yield c

    def test_janela_gigante_recusada(self, client):
        resp = client.post("/api/treinos/iniciar", json={"janela": 10**9})
        assert resp.status_code == 400
        assert "janela" in resp.get_json()["error"]

    def test_quantidade_gigante_recusada(self, client):
        resp = client.post("/api/jogos/gerar", json={"quantidade": 10**7})
        assert resp.status_code == 400
        assert "quantidade" in resp.get_json()["error"]

    def test_limite_de_listagem_recusado(self, client):
        resp = client.get("/api/jogos?limite=10000000")
        assert resp.status_code == 400
        assert "limite" in resp.get_json()["error"]

    def test_pool_de_fechamento_gigante_recusado(self, client):
        """C(len(pool), k) explode; sem teto isso trava o worker."""
        resp = client.post("/api/fechamento", json={"dezenas": list(range(1, 81)), "k": 5, "faixa": 4})
        assert resp.status_code == 400
        assert "dezenas" in resp.get_json()["error"]

    def test_orcamento_invalido_recusado(self, client):
        for valor in (0, -1, 10**9):
            resp = client.post("/api/portfolio", json={"orcamento": valor})
            assert resp.status_code == 400, valor

    def test_valores_legitimos_passam_da_validacao(self, client):
        """A validação não pode estrangular uso normal."""
        resp = client.post("/api/treinos/iniciar", json={"janela": 300})
        assert resp.status_code != 400 or "janela" not in resp.get_json().get("error", "")
