"""Flask dashboard for Quina — minimal data-only view."""
from __future__ import annotations

import hmac
import logging
import os
import secrets
import uuid
from datetime import timedelta
from pathlib import Path

from flask import (
    Flask, jsonify, redirect, render_template_string, request,
    send_from_directory, session, url_for,
)

from quina.dominio.regras import TOTAL_NUMEROS, custo_aposta
from quina.infra.dados.api_caixa import QuinaFetcher
from quina.infra.dados.banco import DatabaseManager
from quina.servicos import fechamento as fechamento_servico
from quina.servicos import portfolio as portfolio_servico
from quina.servicos.backtest import ESTRATEGIAS_DISPONIVEIS, rodar_backtest
from quina.servicos.estrategias import scoring
from quina.servicos.estrategias.frequencia_atraso import gerar_candidato_frequencia_atraso

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("DASHBOARD_AUTH_SECRET") or secrets.token_hex(32)
app.permanent_session_lifetime = timedelta(days=30)

STATIC_DIR = Path(__file__).resolve().parent / "static"


# ─── Limites de entrada ────────────────────────────────────────
# Este painel expoe endpoints POST que rodam backtest, geram jogos e calculam
# fechamentos — todos com custo computacional que cresce com os parametros.
# Sem teto, um unico request com `quantidade=10**9` ou um pool grande de
# fechamento consome CPU/memoria ate derrubar o processo. Os limites abaixo
# sao generosos para uso legitimo e fecham o vetor de DoS.
JANELA_MAX = 5_000
QUANTIDADE_MAX = 200
TAMANHO_APOSTA_MIN, TAMANHO_APOSTA_MAX = 5, 15
LIMITE_LISTAGEM_MAX = 500
POOL_FECHAMENTO_MAX = 25
ORCAMENTO_MAX = 1_000_000.0


def _inteiro_em_faixa(valor, nome, minimo, maximo, padrao):
    """Converte para int e valida a faixa. Levanta ValueError com mensagem util."""
    if valor is None:
        return padrao
    try:
        n = int(valor)
    except (ValueError, TypeError):
        raise ValueError(f"{nome} deve ser um numero inteiro")
    if not (minimo <= n <= maximo):
        raise ValueError(f"{nome} deve estar entre {minimo} e {maximo}")
    return n


# ─── Autenticacao (falha fechado) ──────────────────────────────
# Mesmo contrato de variaveis do painel do lotofacil, de proposito: quem opera
# os dois aprende um mecanismo so.
_LOGIN_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Login — Quina Dashboard</title>
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
  <h1>Quina Dashboard</h1>
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
    `python -m quina.interface.painel.server` quanto
    `gunicorn quina.interface.painel.server:app` passam antes de servir.
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
            "pessoa com acesso de rede pode ler os dados, disparar sincronizacao e "
            "rodar backtests. Use apenas atras de uma rede ou tunnel confiavel."
        )
        return

    raise SystemExit(
        "Dashboard da Quina nao iniciado: configuracao de seguranca ausente.\n"
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
    if request.endpoint in ("login_page", "logout"):
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "unauthorized"}), 401
    return redirect(url_for("login_page"))


@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "dashboard.html")


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
        fetcher = QuinaFetcher()
        novos = fetcher.sync_new_draws()
        return jsonify({"novos": novos})
    except Exception:
        # Detalhe fica no log; a resposta nao expoe stack/caminhos ao cliente.
        logger.exception("Falha ao sincronizar concursos da API")
        return jsonify({"error": "falha ao sincronizar concursos"}), 500


@app.route("/api/treinos/iniciar", methods=["POST"])
def api_treinos_iniciar():
    body = request.get_json(force=True, silent=True) or {}
    estrategia = body.get("estrategia", "filtros")
    try:
        janela = _inteiro_em_faixa(body.get("janela"), "janela", 1, JANELA_MAX, 300)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if estrategia not in ESTRATEGIAS_DISPONIVEIS:
        return jsonify({"error": f"estratégia desconhecida: {estrategia}"}), 400

    db = DatabaseManager()
    if db.count_concursos() < 2:
        return jsonify({"error": "dados insuficientes"}), 400

    metricas = rodar_backtest(estrategia=estrategia, janela=janela, db=db)
    db.salvar_backtest(estrategia, metricas["janela"], metricas)
    return jsonify({"job_id": str(uuid.uuid4()), "resultado": metricas})


@app.route("/api/treinos")
def api_treinos_listar():
    db = DatabaseManager()
    return jsonify({"backtests": db.listar_backtests()})


@app.route("/api/jogos/gerar", methods=["POST"])
def api_jogos_gerar():
    body = request.get_json(force=True, silent=True) or {}
    estrategia = body.get("estrategia", "filtros")
    try:
        tamanho = _inteiro_em_faixa(
            body.get("tamanho_aposta"), "tamanho_aposta",
            TAMANHO_APOSTA_MIN, TAMANHO_APOSTA_MAX, 5,
        )
        quantidade = _inteiro_em_faixa(
            body.get("quantidade"), "quantidade", 1, QUANTIDADE_MAX, 5,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    concurso_alvo = body.get("concurso_alvo")

    db = DatabaseManager()
    draws = db.get_all_concursos()
    if len(draws) < 2:
        return jsonify({"error": "dados insuficientes"}), 400

    try:
        custo_unitario = custo_aposta(tamanho)
        if estrategia == "filtros":
            candidatos = scoring.gerar_candidatos(
                quantidade=max(200, quantidade * 20), tamanho_aposta=tamanho, draws=draws
            )
            selecionados = scoring.top_k(candidatos, quantidade)
        elif estrategia == "frequencia_atraso":
            selecionados = [gerar_candidato_frequencia_atraso(draws, tamanho) for _ in range(quantidade)]
        else:
            return jsonify({"error": f"estratégia desconhecida: {estrategia}"}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    jogos = []
    for jogo in selecionados:
        jogo_id = db.salvar_jogo_gerado(
            estrategia=estrategia, tamanho_aposta=tamanho, dezenas=jogo["dezenas"],
            score=jogo.get("score"), custo=custo_unitario, concurso_alvo_validacao=concurso_alvo,
        )
        jogos.append({"id": jogo_id, "dezenas": jogo["dezenas"], "score": jogo.get("score"), "custo": custo_unitario})

    return jsonify({"job_id": str(uuid.uuid4()), "jogos": jogos})


@app.route("/api/jogos")
def api_jogos_listar():
    try:
        limite = _inteiro_em_faixa(
            request.args.get("limite"), "limite", 1, LIMITE_LISTAGEM_MAX, 50,
        )
        offset = _inteiro_em_faixa(
            request.args.get("offset"), "offset", 0, 10_000_000, 0,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    db = DatabaseManager()
    return jsonify({"jogos": db.listar_jogos_gerados(limite=limite, offset=offset)})


@app.route("/api/fechamento", methods=["POST"])
def api_fechamento():
    body = request.get_json(force=True, silent=True) or {}
    pool = body.get("dezenas", [])
    k = body.get("k")
    faixa = body.get("faixa")
    # O fechamento enumera combinacoes do pool: o custo cresce como C(len,k).
    # Sem teto, um pool grande trava o worker.
    if not isinstance(pool, list):
        return jsonify({"error": "dezenas deve ser uma lista"}), 400
    if len(pool) > POOL_FECHAMENTO_MAX:
        return jsonify({
            "error": f"dezenas deve ter no maximo {POOL_FECHAMENTO_MAX} numeros"
        }), 400
    try:
        resultado = fechamento_servico.gerar_fechamento(pool, (int(k), int(faixa)))
        return jsonify(resultado)
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/portfolio", methods=["POST"])
def api_portfolio():
    body = request.get_json(force=True, silent=True) or {}
    orcamento = body.get("orcamento")
    perfil = body.get("perfil", "equilibrado")

    db = DatabaseManager()
    draws = db.get_all_concursos()
    if len(draws) < 2:
        return jsonify({"error": "dados insuficientes"}), 400

    try:
        orcamento_f = float(orcamento)
    except (ValueError, TypeError):
        return jsonify({"error": "orcamento deve ser um numero"}), 400
    if not (0 < orcamento_f <= ORCAMENTO_MAX):
        return jsonify({
            "error": f"orcamento deve ser maior que zero e no maximo {ORCAMENTO_MAX:.0f}"
        }), 400

    try:
        resultado = portfolio_servico.gerar_portfolio(orcamento=orcamento_f, perfil=perfil, draws=draws)
        return jsonify(resultado)
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400
