"""Dashboard server — Flask + SSE for real-time command execution."""

import os
import sys
import json
import queue
import threading
import subprocess
import time
import re
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, Response, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dashboard.commands import COMMANDS, BASE  # noqa: E402
from lotofacil_ml.evaluation.metrics import LotofacilMetrics
from lotofacil_ml.evaluation.significance import compare_vs_baseline
from lotofacil_ml.config import NUMBERS_PER_DRAW, RANDOM_SEED, TOTAL_NUMBERS
import random
import statistics

_ANSI_RE = re.compile(r'\x1b(?:\[[0-9;]*[mGKHFABCDEFsuJKH]|[()][AB012])')


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub('', text)


app = Flask(__name__, static_folder=None)

TASKS: dict[str, queue.Queue] = {}
BASE_DIR = BASE
DADOS_DIR = BASE / "dados"
SAIDA_DIR = BASE / "saida"
DATA_DIR = BASE / "data"
MODELS_CORE_DIR = BASE / "output" / "models"
MODELS_LAB_DIR = BASE / "src" / "lotofacil_lab" / "saved_models"


# ─── Helper ────────────────────────────────────────────────────

def _last_concurso_info():
    jsons = sorted(DADOS_DIR.glob("concurso_*.json"))
    if not jsons:
        return {"latest": None, "total": 0}
    last = jsons[-1]
    try:
        with open(last) as f:
            data = json.load(f)
        return {
            "latest": {"concurso": data.get("concurso"), "data": data.get("data")},
            "total": len(jsons),
        }
    except Exception:
        return {"latest": {"concurso": last.stem.split("_")[1]}, "total": len(jsons)}


def _list_game_files():
    games_dir = SAIDA_DIR / "jogos"
    if not games_dir.exists():
        return []
    files = sorted(games_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    result = []
    for f in files[:20]:
        try:
            concurso = f.stem.split("_")[-1]
        except Exception:
            concurso = "?"
        result.append({
            "filename": f.name,
            "concurso": concurso,
            "size": f.stat().st_size,
            "mtime": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return result


def _infer_approach(stem: str) -> str:
    """Infer approach from filename like 'predicao_{approach}_{concurso}'."""
    parts = stem.split("_")
    if len(parts) >= 3:
        return "_".join(parts[1:-1])
    return "ensemble"


def _list_predictions():
    """Read saida/jogos/predicao_*.json and group by concurso."""
    games_dir = SAIDA_DIR / "jogos"
    if not games_dir.exists():
        return []
    by_concurso: dict = {}
    for f in sorted(games_dir.glob("predicao_*.json"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            concurso_val = data.get("concurso")
            if concurso_val is None:
                continue
            key = str(concurso_val)
            if key not in by_concurso:
                by_concurso[key] = {
                    "concurso": concurso_val,
                    "mtime": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    "abordagens": [],
                }
            by_concurso[key]["abordagens"].append({
                "abordagem": data.get("abordagem", _infer_approach(f.stem)),
                "dezenas": data.get("dezenas", []),
                "confianca": data.get("confianca"),
            })
        except Exception:
            pass
    return list(by_concurso.values())


def _scan_models():
    """Scan model directories for .keras files and read their metadata."""
    models = []
    scan_dirs = [
        (MODELS_CORE_DIR, "core"),
        (MODELS_LAB_DIR, "lab"),
    ]
    for d, group in scan_dirs:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.keras"), key=lambda p: p.stat().st_mtime, reverse=True):
            meta: dict = {}
            meta_file = f.with_suffix(".meta.json")
            if meta_file.exists():
                try:
                    raw = json.loads(meta_file.read_text())
                    hist = raw.get("history", {})
                    val_loss = hist.get("val_loss", [])
                    meta = {
                        "epochs_trained": len(hist.get("loss", [])),
                        "val_loss_final": round(val_loss[-1], 5) if val_loss else None,
                        "config": raw.get("config", raw.get("hp_overrides", {})),
                    }
                except Exception:
                    pass
            models.append({
                "name": f.name,
                "group": group,
                "size_mb": round(f.stat().st_size / 1_048_576, 1),
                "trained_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                **meta,
            })
    return models


def _load_draw_by_concurso() -> dict[int, list[int]]:
    draws: dict[int, list[int]] = {}
    for f in sorted(DADOS_DIR.glob("concurso_*.json")):
        try:
            data = json.loads(f.read_text())
            concurso = int(data.get("concurso"))
            dezenas = [int(n) for n in data.get("dezenas", [])]
            if len(dezenas) == NUMBERS_PER_DRAW:
                draws[concurso] = dezenas
        except Exception:
            continue
    return draws


def _predict_rows_with_hits(window_size: int = 120) -> tuple[list[dict], int]:
    draws = _load_draw_by_concurso()
    rows = []
    for f in sorted((SAIDA_DIR / "jogos").glob("predicao_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            concurso = int(data.get("concurso"))
            dezenas = [int(n) for n in data.get("dezenas", [])]
            actual = draws.get(concurso)
            if actual and len(dezenas) == NUMBERS_PER_DRAW:
                hits = len(set(dezenas) & set(actual))
                rows.append({
                    "concurso": concurso,
                    "abordagem": data.get("abordagem", _infer_approach(f.stem)),
                    "predicted": dezenas,
                    "actual": actual,
                    "hits": hits,
                })
        except Exception:
            continue

    # keep latest per abordagem+concurso and then clip temporal window
    dedup: dict[tuple[str, int], dict] = {}
    for r in rows:
        dedup[(r["abordagem"], r["concurso"])] = r
    filtered = sorted(dedup.values(), key=lambda x: x["concurso"], reverse=True)[:window_size]
    return filtered, window_size


def _classify_quality(improvement_pct: float, p_value: float) -> tuple[str, str]:
    if improvement_pct > 0 and p_value < 0.05:
        return "Bom", "good"
    if improvement_pct > 0 and p_value >= 0.05:
        return "Atenção", "warning"
    return "Ruim", "bad"


def _build_quality_payload(window_size: int = 120) -> dict:
    rows, configured_window = _predict_rows_with_hits(window_size=window_size)
    by_approach: dict[str, list[dict]] = {}
    for r in rows:
        by_approach.setdefault(r["abordagem"], []).append(r)

    rng = random.Random(RANDOM_SEED)
    all_numbers = list(range(1, TOTAL_NUMBERS + 1))

    models = []
    for approach, grp in sorted(by_approach.items()):
        grp_sorted = sorted(grp, key=lambda x: x["concurso"])
        results = [{"predicted": g["predicted"], "actual": g["actual"], "hits": g["hits"]} for g in grp_sorted]
        baseline = LotofacilMetrics.vs_random_baseline(results, n_simulations=200)

        model_hits = [g["hits"] for g in grp_sorted]
        baseline_hits = [len(set(rng.sample(all_numbers, NUMBERS_PER_DRAW)) & set(g["actual"])) for g in grp_sorted]
        sig = compare_vs_baseline(model_hits, baseline_hits)

        std_hits = float(statistics.pstdev(model_hits)) if len(model_hits) > 1 else 0.0
        var_hits = float(statistics.pvariance(model_hits)) if len(model_hits) > 1 else 0.0
        label, level = _classify_quality(baseline["improvement_pct"], sig.p_value)

        models.append({
            "model": approach,
            "mean_hits": round(baseline["model_mean"], 3),
            "improvement_pct": round(baseline["improvement_pct"], 2),
            "p_value": round(sig.p_value, 4),
            "stability": {"std_hits": round(std_hits, 3), "var_hits": round(var_hits, 3)},
            "sample_size": len(grp_sorted),
            "window": {
                "requested_last_n": configured_window,
                "used_draws": len(rows),
                "from_concurso": grp_sorted[0]["concurso"],
                "to_concurso": grp_sorted[-1]["concurso"],
            },
            "classification": {"label": label, "level": level},
            "interpretation": sig.interpretation,
        })

    return {"models": models, "window": {"requested_last_n": configured_window, "used_draws": len(rows)}}


# ─── API Endpoints ─────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(
        str(Path(__file__).resolve().parent / "static"), "dashboard.html"
    )


@app.route("/api/commands")
def api_commands():
    return jsonify(COMMANDS)


@app.route("/api/status")
def api_status():
    info = _last_concurso_info()
    return jsonify({
        "last_concurso": info["latest"],
        "total_draws": info["total"],
        "games_count": len(_list_game_files()),
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/games")
def api_games():
    return jsonify(_list_game_files())


@app.route("/api/predictions")
def api_predictions():
    return jsonify(_list_predictions())


@app.route("/api/models/status")
def api_models_status():
    return jsonify(_scan_models())


@app.route("/api/models/quality")
def api_models_quality():
    last_n = request.args.get("last_n", default=120, type=int)
    last_n = max(10, min(last_n or 120, 500))
    return jsonify(_build_quality_payload(window_size=last_n))


@app.route("/api/games/<path:filename>")
def api_game_file(filename):
    safe = Path(filename).name
    path = SAIDA_DIR / "jogos" / safe
    if not path.exists():
        return jsonify({"error": "not found"}), 404
    try:
        data = json.loads(path.read_text())
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e), "content": path.read_text()}), 200


@app.route("/api/generate", methods=["POST"])
def api_generate():
    body = request.get_json(force=True) or {}
    action = body.get("action", "gerar_jogos")

    for cat in COMMANDS.values():
        for item in cat["items"]:
            if item["id"] == action:
                task_id = f"task_{int(time.time() * 1000)}_{action}"
                q: queue.Queue = queue.Queue()
                TASKS[task_id] = q
                t = threading.Thread(
                    target=_run_command,
                    args=(task_id, q, item["cmd"], item["cwd"]),
                    daemon=True,
                )
                t.start()
                return jsonify({"task_id": task_id})
    return jsonify({"error": f"Unknown action: {action}"}), 400


@app.route("/api/stream/<task_id>")
def api_stream(task_id):
    def generate():
        q = TASKS.get(task_id)
        if q is None:
            yield f"data: {json.dumps({'type': 'error', 'text': 'Task not found'})}\n\n"
            return
        try:
            while True:
                try:
                    line = q.get(timeout=0.5)
                    if line is None:
                        yield f"event: done\ndata: {json.dumps({'type': 'done'})}\n\n"
                        break
                    yield f"data: {json.dumps({'type': 'stdout', 'text': line})}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except GeneratorExit:
            pass
        finally:
            TASKS.pop(task_id, None)

    return Response(generate(), mimetype="text/event-stream")


# ─── Command Runner ────────────────────────────────────────────

def _run_command(task_id: str, q: queue.Queue, cmd: list[str], cwd: str):
    def emit(line: str):
        q.put(line)

    cmd = [sys.executable if c == "python" else c for c in cmd]
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parent.parent)}

    try:
        emit(f"$ {' '.join(cmd)}\n")
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        for line in iter(proc.stdout.readline, ""):
            emit(_strip_ansi(line.rstrip("\n")))
        proc.stdout.close()
        ret = proc.wait()
        if ret == 0:
            emit("")
            emit("✅ Comando concluído com sucesso.")
        else:
            emit("")
            emit(f"⚠️  Comando finalizou com código {ret}.")
    except Exception as e:
        emit(f"❌ Erro: {e}")
    finally:
        q.put(None)


# ─── Main ──────────────────────────────────────────────────────

def main():
    host = os.environ.get("DASHBOARD_HOST", "0.0.0.0")
    port = int(os.environ.get("DASHBOARD_PORT", "5000"))
    print("🎰 Lotofácil Dashboard")
    print(f"   Servidor: http://{host}:{port}")
    print(f"   Pressione Ctrl+C para parar.")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
