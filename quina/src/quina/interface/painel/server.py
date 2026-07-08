"""Flask dashboard for Quina — minimal data-only view."""
from __future__ import annotations

from flask import Flask, jsonify

from quina.infra.dados.banco import DatabaseManager

app = Flask(__name__)


@app.route("/api/status")
def api_status():
    db = DatabaseManager()
    return jsonify({
        "total_concursos": db.count_concursos(),
        "ultimo_concurso": db.get_latest_concurso(),
    })
