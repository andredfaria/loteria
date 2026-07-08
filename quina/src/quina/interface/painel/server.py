"""Flask dashboard for Quina — minimal data-only view."""
from __future__ import annotations

from flask import Flask, jsonify

from quina.dominio.regras import TOTAL_NUMEROS
from quina.infra.dados.banco import DatabaseManager

app = Flask(__name__)


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
