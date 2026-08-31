"""Regressão para o fail-closed do dashboard (F-01) e o aviso de F-16.

Por padrão o dashboard (`lotofacil.interface.painel.server`) recusa iniciar
sem uma decisão explícita de segurança: `DASHBOARD_PASSWORD` (exige login)
ou `DASHBOARD_PUBLICO=1` (confirma explicitamente que o painel deve ficar
acessível sem senha). Antes desse fix, `DASHBOARD_PASSWORD` ausente
silenciosamente desabilitava toda a autenticação — nenhum Dockerfile do
repositório define essa variável, então o comportamento padrão de deploy
era "sem autenticação nenhuma".

Ver `_decide_auth_startup` / `_startup_auth_check` em
`lotofacil/src/lotofacil/interface/painel/server.py`.
"""
import logging
import os
import threading

import pytest

# A importação do módulo abaixo precisa sobreviver mesmo que o ambiente
# ambiente deste processo de teste não defina DASHBOARD_PASSWORD nem
# DASHBOARD_PUBLICO — sem isso, a checagem em nível de módulo levantaria
# SystemExit durante a coleta do pytest. O bypass vale só para esta
# importação; cada teste abaixo chama a função de checagem real
# (`_startup_auth_check`) diretamente, com variáveis de ambiente
# controladas por `monkeypatch`, para validar o comportamento de verdade.
os.environ.setdefault("DASHBOARD_SKIP_AUTH_CHECK", "1")

from lotofacil.interface.painel import server as server_module  # noqa: E402
from lotofacil.infra.config import DADOS_DIR  # noqa: E402

SAMPLE_DIR = DADOS_DIR / "sample"


def test_decide_auth_startup_matriz_pura():
    """Função de decisão pura (sem I/O): cobre as quatro combinações."""
    decide = server_module._decide_auth_startup
    assert decide(password="", publico=False, skip_check=True) == "skipped"
    assert decide(password="x", publico=False, skip_check=False) == "ok_authenticated"
    assert decide(password="", publico=True, skip_check=False) == "ok_public"
    assert decide(password="", publico=True, skip_check=True) == "skipped"
    assert decide(password="", publico=False, skip_check=False) == "blocked"


def test_sem_senha_e_sem_publico_bloqueia_inicializacao(monkeypatch):
    """(a) Sem DASHBOARD_PASSWORD e sem DASHBOARD_PUBLICO, a inicialização falha."""
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    monkeypatch.delenv("DASHBOARD_PUBLICO", raising=False)
    monkeypatch.delenv("DASHBOARD_SKIP_AUTH_CHECK", raising=False)

    with pytest.raises(SystemExit):
        server_module._startup_auth_check()


def test_com_senha_api_status_sem_sessao_retorna_401(monkeypatch):
    """(b) Com DASHBOARD_PASSWORD configurada, GET /api/status sem sessão -> 401."""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "segredo123")

    server_module.app.testing = True
    with server_module.app.test_client() as client:
        resp = client.get("/api/status")

    assert resp.status_code == 401
    assert "error" in resp.get_json()


def test_dashboard_publico_abre_sem_senha(monkeypatch):
    """(c) Com DASHBOARD_PUBLICO=1 e sem senha, o painel abre normalmente."""
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    monkeypatch.delenv("DASHBOARD_SKIP_AUTH_CHECK", raising=False)
    monkeypatch.setenv("DASHBOARD_PUBLICO", "1")
    monkeypatch.setattr(server_module, "DADOS_DIR", SAMPLE_DIR)

    # A checagem de startup não deve levantar SystemExit nesse cenário.
    server_module._startup_auth_check()

    server_module.app.testing = True
    with server_module.app.test_client() as client:
        resp = client.get("/api/status")

    assert resp.status_code == 200


def test_senha_sem_auth_secret_loga_warning(monkeypatch):
    """(F-16) Com auth ligada e sem DASHBOARD_AUTH_SECRET, loga aviso claro.

    Sem isso, a secret_key da sessão é regenerada a cada restart (derruba
    todas as sessões) e, com múltiplos workers gunicorn, cada worker gera a
    sua própria chave — login falha de forma intermitente.
    """
    monkeypatch.setenv("DASHBOARD_PASSWORD", "segredo123")
    monkeypatch.delenv("DASHBOARD_AUTH_SECRET", raising=False)
    monkeypatch.delenv("DASHBOARD_SKIP_AUTH_CHECK", raising=False)

    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = records.append
    server_module.LOGGER.addHandler(handler)
    try:
        server_module._startup_auth_check()
    finally:
        server_module.LOGGER.removeHandler(handler)

    assert any("DASHBOARD_AUTH_SECRET" in r.getMessage() for r in records)


def test_max_jobs_default_e_configuravel():
    """DASHBOARD_MAX_JOBS controla o teto do semáforo de jobs concorrentes."""
    assert server_module.DASHBOARD_MAX_JOBS >= 1
    assert isinstance(server_module._job_semaphore, threading.Semaphore)


def test_erro_antes_do_thread_start_libera_vaga_do_semaforo(monkeypatch):
    """Regressão: exceção entre o acquire e o t.start() não pode vazar a vaga.

    `_acquire_job_slot()` reserva a vaga no endpoint; ela só é liberada de
    volta dentro de `_run_command_slotted`, que roda DENTRO da thread. Se
    algo falhar antes de `t.start()` (ex.: `_registry.create_job` batendo
    em SQLite locked/disco cheio) sem devolver a vaga explicitamente, ela
    fica presa até o processo reiniciar — depois de DASHBOARD_MAX_JOBS
    ocorrências, todo /api/generate passa a responder 429 permanentemente.
    """
    max_jobs = server_module.DASHBOARD_MAX_JOBS

    def _boom(*args, **kwargs):
        raise RuntimeError("falha simulada no registry")

    monkeypatch.setattr(server_module._registry, "create_job", _boom)

    server_module.app.testing = True
    with server_module.app.test_client() as client:
        resp = client.post("/api/generate", json={"action": "status"})

    assert resp.status_code == 500

    # Se a vaga tivesse vazado, não seria possível reservar as `max_jobs`
    # vagas livres agora — o semáforo teria ficado com uma a menos.
    acquired = [server_module._job_semaphore.acquire(blocking=False) for _ in range(max_jobs)]
    try:
        assert all(acquired), "vaga do semáforo vazou após exceção pré-thread"
    finally:
        for ok in acquired:
            if ok:
                server_module._job_semaphore.release()
