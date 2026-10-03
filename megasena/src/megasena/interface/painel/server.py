"""Flask dashboard for Mega-Sena — minimal data-only view."""
from __future__ import annotations

import hmac
import logging
import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import (
    Flask, jsonify, redirect, render_template_string, request,
    send_from_directory, session, url_for,
)

from megasena.dominio.regras import TAMANHO_APOSTA_MAX, TAMANHO_APOSTA_MIN, TOTAL_NUMEROS
from megasena.infra.dados.api_caixa import MegasenaFetcher
from megasena.infra.dados.banco import DatabaseManager
from megasena.servicos.bolao import avaliar_bolao, comparar_boloes

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("DASHBOARD_AUTH_SECRET") or secrets.token_hex(32)
app.permanent_session_lifetime = timedelta(days=30)

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Teto generoso para entradas do avaliador de bolão. O cálculo é O(1), mas
# números absurdos só geram respostas sem sentido.
APOSTAS_MAX = 10_000
COTAS_MAX = 10_000
VALOR_MAX = 100_000_000.0
BOLOES_COMPARAR_MAX = 10
NOME_BOLAO_MAX = 60


# ─── Autenticacao (falha fechado) ──────────────────────────────
# Mesmo contrato de variaveis dos paineis do lotofacil e da quina, de
# proposito: quem opera os tres aprende um mecanismo so.
_LOGIN_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Login — Mega-Sena Dashboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0f1117;color:#e2e8f0;font-family:monospace;display:flex;
     align-items:center;justify-content:center;min-height:100vh;padding:1rem}
.card{background:#1a1f2e;border:1px solid #2d3748;border-radius:10px;padding:2rem;width:min(320px,100%)}
h1{font-size:1.1rem;margin-bottom:1.5rem;color:#60a5fa}
label{font-size:0.78rem;color:#94a3b8;display:block;margin-bottom:0.3rem}
input[type=password]{width:100%;padding:0.5rem 0.75rem;background:#0f1117;color:#e2e8f0;
  border:1px solid #2d3748;border-radius:5px;font-family:monospace;font-size:0.9rem;margin-bottom:1rem}
input[type=password]:focus{outline:2px solid #60a5fa;outline-offset:1px}
button{width:100%;padding:0.55rem;background:#1e3a5f;color:#60a5fa;border:1px solid #60a5fa;
  border-radius:5px;font-family:monospace;font-size:0.9rem;cursor:pointer}
button:hover{background:#2d4a6f}
.error{color:#f87171;font-size:0.78rem;margin-bottom:0.75rem}
</style>
</head>
<body>
<div class="card">
  <h1>Mega-Sena Dashboard</h1>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  <form method="post">
    <label for="password">Senha</label>
    <input id="password" type="password" name="password" autofocus autocomplete="current-password">
    <button type="submit">Entrar</button>
  </form>
</div>
</body>
</html>"""


def _decidir_auth_startup(password: str, publico: bool, pular: bool) -> str:
    """Decisao pura sobre como a inicializacao deve proceder.

    "skipped" | "ok_authenticated" | "ok_public" | "blocked"
    """
    if pular:
        return "skipped"
    if password:
        return "ok_authenticated"
    if publico:
        return "ok_public"
    return "blocked"


def _startup_auth_check() -> None:
    """Recusa iniciar o painel sem uma decisao explicita de seguranca.

    Roda na importacao do modulo — o unico ponto por onde tanto
    `python -m megasena.interface.painel.server` quanto
    `gunicorn megasena.interface.painel.server:app` passam antes de servir.
    `DASHBOARD_SKIP_AUTH_CHECK=1` pula a checagem e existe apenas para a suite
    de testes; nenhum Dockerfile ou entrypoint deste repositorio a define.
    """
    password = os.environ.get("DASHBOARD_PASSWORD", "")
    publico = os.environ.get("DASHBOARD_PUBLICO", "") == "1"
    pular = os.environ.get("DASHBOARD_SKIP_AUTH_CHECK", "") == "1"

    decisao = _decidir_auth_startup(password, publico, pular)

    if decisao == "skipped":
        return
    if decisao == "ok_authenticated":
        if not os.environ.get("DASHBOARD_AUTH_SECRET"):
            logger.warning(
                "DASHBOARD_AUTH_SECRET nao definida: a secret_key da sessao e gerada "
                "aleatoriamente a cada inicio do processo, entao todo restart invalida "
                "os logins. Com '--workers' > 1 no gunicorn, cada worker gera a sua e o "
                "login falha de forma intermitente. Defina um valor fixo e secreto."
            )
        return
    if decisao == "ok_public":
        logger.warning(
            "DASHBOARD_PUBLICO=1: o painel esta rodando SEM AUTENTICACAO. Qualquer "
            "pessoa com acesso de rede pode ler os dados e disparar sincronizacao. "
            "Use apenas atras de uma rede ou tunnel confiavel."
        )
        return

    raise SystemExit(
        "Dashboard da Mega-Sena nao iniciado: configuracao de seguranca ausente.\n"
        "Defina uma das duas variaveis de ambiente antes de subir o servidor:\n"
        "  DASHBOARD_PASSWORD=<senha>   -> exige login por senha (recomendado)\n"
        "  DASHBOARD_PUBLICO=1          -> confirma explicitamente que o painel\n"
        "                                  deve ficar acessivel sem senha\n"
        "Por padrao o painel nao inicia sem uma delas, para evitar expor dados e "
        "disparar processamento publicamente por omissao."
    )


_startup_auth_check()


@app.route("/login", methods=["GET", "POST"])
def login_page():
    password = os.environ.get("DASHBOARD_PASSWORD", "")
    if not password:
        return redirect(url_for("index"))
    if request.method == "POST":
        if hmac.compare_digest(request.form.get("password", ""), password):
            session.clear()
            session.permanent = True
            session["authenticated"] = True
            return redirect(url_for("index"))
        return render_template_string(_LOGIN_HTML, error="Senha incorreta.")
    return render_template_string(_LOGIN_HTML, error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.before_request
def _check_auth():
    """Guarda de autenticacao.

    O ramo `if not password: return None` so e alcancavel com
    DASHBOARD_PUBLICO=1, porque `_startup_auth_check()` impede o processo de
    subir sem senha e sem essa confirmacao. Remover ou pular aquela checagem
    fora dos testes reabre o painel inteiro sem autenticacao.
    """
    password = os.environ.get("DASHBOARD_PASSWORD", "")
    if not password:
        return None
    if session.get("authenticated"):
        return None
    if request.endpoint in ("login_page", "logout", "healthz"):
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "unauthorized"}), 401
    return redirect(url_for("login_page"))


@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "dashboard.html")


@app.route("/healthz")
def healthz():
    """Liveness do container: sem login, sem banco e sem dados na resposta.

    O HEALTHCHECK do Dockerfile consulta esta rota. Antes ele consultava
    /api/status, que responde 401 quando DASHBOARD_PASSWORD está definida,
    e o container ficava marcado como unhealthy.
    """
    return jsonify({"status": "ok"})


@app.route("/api/status")
def api_status():
    db = DatabaseManager()
    return jsonify({
        "total_concursos": db.count_concursos(),
        "ultimo_concurso": db.get_latest_concurso(),
    })


@app.route("/api/frequencia")
def api_frequencia():
    db = DatabaseManager()
    concursos = db.get_all_concursos()
    frequencia = {str(n): 0 for n in range(1, TOTAL_NUMEROS + 1)}
    for c in concursos:
        for n in c["dezenas"]:
            frequencia[str(n)] += 1
    return jsonify({"frequencia": frequencia, "total_concursos": len(concursos)})


@app.route("/api/atraso")
def api_atraso():
    db = DatabaseManager()
    concursos = db.get_all_concursos()  # ordered ascending by concurso
    total = len(concursos)
    ultimo_indice: dict[int, int] = {}
    for i, c in enumerate(concursos):
        for n in c["dezenas"]:
            ultimo_indice[n] = i

    atraso = {}
    for n in range(1, TOTAL_NUMEROS + 1):
        if n in ultimo_indice:
            idx = ultimo_indice[n]
            atraso[str(n)] = {
                "atraso": total - 1 - idx,
                "ultimo_concurso": concursos[idx]["concurso"],
            }
        else:
            atraso[str(n)] = {"atraso": total, "ultimo_concurso": None}

    return jsonify({"atraso": atraso, "total_concursos": total})


@app.route("/api/atualizar", methods=["POST"])
def api_atualizar():
    try:
        fetcher = MegasenaFetcher()
        novos = fetcher.sync_new_draws()
        return jsonify({"novos": novos})
    except Exception:
        # Detalhe fica no log; a resposta nao expoe stack/caminhos ao cliente.
        logger.exception("Falha ao sincronizar concursos da API")
        return jsonify({"error": "falha ao sincronizar concursos"}), 500


@app.route("/api/bolao/avaliar", methods=["POST"])
def api_bolao_avaliar():
    body = request.get_json(force=True, silent=True) or {}
    try:
        bolao = _ler_bolao(body)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(avaliar_bolao(**bolao))


@app.route("/comparar")
def comparar():
    return send_from_directory(str(STATIC_DIR), "comparar.html")


@app.route("/api/bolao/comparar", methods=["POST"])
def api_bolao_comparar():
    body = request.get_json(force=True, silent=True) or {}
    lista = body.get("boloes")
    if not isinstance(lista, list) or not (2 <= len(lista) <= BOLOES_COMPARAR_MAX):
        return jsonify({"error": f"boloes deve ser uma lista com 2 a {BOLOES_COMPARAR_MAX} itens"}), 400

    boloes = []
    for i, item in enumerate(lista, start=1):
        if not isinstance(item, dict):
            return jsonify({"error": f"bolão {i}: formato invalido"}), 400
        try:
            bolao = _ler_bolao(item)
        except ValueError as exc:
            return jsonify({"error": f"bolão {i}: {exc}"}), 400
        nome = str(item.get("nome") or "").strip()[:NOME_BOLAO_MAX]
        boloes.append({**bolao, "nome": nome or None})

    return jsonify(comparar_boloes(boloes))


def _ler_bolao(body: dict) -> dict:
    """Valida os campos de um bolão vindos do JSON. Levanta ValueError."""
    try:
        valor_total = float(body.get("valor_total"))
    except (ValueError, TypeError):
        raise ValueError("valor_total deve ser um numero")
    if not (0 < valor_total <= VALOR_MAX):
        raise ValueError(f"valor_total deve ser maior que zero e no maximo {VALOR_MAX:.0f}")

    apostas = _inteiro_em_faixa(body.get("apostas"), "apostas", 1, APOSTAS_MAX)
    dezenas = _inteiro_em_faixa(
        body.get("dezenas"), "dezenas", TAMANHO_APOSTA_MIN, TAMANHO_APOSTA_MAX,
    )
    cotas = None
    if body.get("cotas") not in (None, ""):
        cotas = _inteiro_em_faixa(body.get("cotas"), "cotas", 1, COTAS_MAX)
    return {"valor_total": valor_total, "apostas": apostas, "dezenas": dezenas, "cotas": cotas}


def _inteiro_em_faixa(valor, nome, minimo, maximo):
    """Converte para int e valida a faixa. Levanta ValueError com mensagem util."""
    if valor is None or isinstance(valor, bool):
        raise ValueError(f"{nome} e obrigatorio")
    try:
        n = int(valor)
    except (ValueError, TypeError):
        raise ValueError(f"{nome} deve ser um numero inteiro")
    if not (minimo <= n <= maximo):
        raise ValueError(f"{nome} deve estar entre {minimo} e {maximo}")
    return n
