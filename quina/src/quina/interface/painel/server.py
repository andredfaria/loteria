"""Flask dashboard for Quina — minimal data-only view."""
from __future__ import annotations

import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from quina.dominio.regras import TOTAL_NUMEROS, custo_aposta
from quina.infra.dados.api_caixa import QuinaFetcher
from quina.infra.dados.banco import DatabaseManager
from quina.servicos import fechamento as fechamento_servico
from quina.servicos import portfolio as portfolio_servico
from quina.servicos.backtest import ESTRATEGIAS_DISPONIVEIS, rodar_backtest
from quina.servicos.estrategias import scoring
from quina.servicos.estrategias.frequencia_atraso import gerar_candidato_frequencia_atraso

app = Flask(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


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
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/treinos/iniciar", methods=["POST"])
def api_treinos_iniciar():
    body = request.get_json(force=True, silent=True) or {}
    estrategia = body.get("estrategia", "filtros")
    try:
        janela = int(body.get("janela", 300))
    except (ValueError, TypeError):
        return jsonify({"error": "janela deve ser um número inteiro"}), 400

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
        tamanho = int(body.get("tamanho_aposta", 5))
        quantidade = int(body.get("quantidade", 5))
    except (ValueError, TypeError):
        return jsonify({"error": "tamanho_aposta e quantidade devem ser números inteiros"}), 400
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
        limite = int(request.args.get("limite", 50))
        offset = int(request.args.get("offset", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "limite e offset devem ser números inteiros"}), 400
    db = DatabaseManager()
    return jsonify({"jogos": db.listar_jogos_gerados(limite=limite, offset=offset)})


@app.route("/api/fechamento", methods=["POST"])
def api_fechamento():
    body = request.get_json(force=True, silent=True) or {}
    pool = body.get("dezenas", [])
    k = body.get("k")
    faixa = body.get("faixa")
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
        resultado = portfolio_servico.gerar_portfolio(orcamento=float(orcamento), perfil=perfil, draws=draws)
        return jsonify(resultado)
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400
