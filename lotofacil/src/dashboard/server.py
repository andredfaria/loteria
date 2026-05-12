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




def _load_kpi_report():
    path = BASE / "output" / "kpi_report.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _extract_model_metrics(report: dict):
    baseline = (report.get("random_baseline") or {}).get("mean_hits")
    models = []
    for key, value in report.items():
        if not isinstance(value, dict):
            continue
        if "mean_hits" not in value or key == "random_baseline":
            continue
        mean_hits = value.get("mean_hits")
        improvement = None
        if baseline not in (None, 0) and mean_hits is not None:
            improvement = ((mean_hits - baseline) / baseline) * 100
        models.append({
            "id": key,
            "label": value.get("label", key),
            "mean_hits": mean_hits,
            "improvement_pct": improvement,
            "p_value": value.get("t_pvalue_mean", value.get("binomial_p_value")),
            "std_hits": value.get("std_hits"),
            "hits_distribution": value.get("hits_distribution", {}),
        })
    return models


def _alert_history_path():
    out = BASE / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out / "alert_history.json"


def _load_alert_history():
    path = _alert_history_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def _save_alert_history(items):
    _alert_history_path().write_text(json.dumps(items, indent=2, ensure_ascii=False))


def _evaluate_alerts(models, pvalue_threshold=0.05, moving_avg_drop_limit=0.15):
    alerts = []
    history = _load_alert_history()
    previous = {h.get("model_id"): h for h in history if h.get("type") == "snapshot"}
    snapshots = []
    now = datetime.utcnow().isoformat()

    for m in models:
        if m.get("improvement_pct") is not None and m["improvement_pct"] < 0:
            alerts.append({"type": "negative_improvement", "severity": "error", "model_id": m["id"], "message": f"{m['label']}: improvement_pct negativo ({m['improvement_pct']:.2f}%)", "timestamp": now})
        if m.get("p_value") is not None and m["p_value"] > pvalue_threshold:
            alerts.append({"type": "pvalue_above_threshold", "severity": "warn", "model_id": m["id"], "message": f"{m['label']}: p_value {m['p_value']:.4f} > {pvalue_threshold:.4f}", "timestamp": now})
        prev = previous.get(m["id"], {})
        prev_ma = prev.get("moving_avg_mean_hits", m.get("mean_hits") or 0)
        curr = m.get("mean_hits") or 0
        ma = ((prev_ma * 2) + curr) / 3
        snapshots.append({"type": "snapshot", "model_id": m["id"], "moving_avg_mean_hits": ma, "timestamp": now})
        if prev_ma and (prev_ma - ma) / prev_ma > moving_avg_drop_limit:
            alerts.append({"type": "moving_avg_drop", "severity": "error", "model_id": m["id"], "message": f"{m['label']}: queda da média móvel acima do limite", "timestamp": now})

    fingerprints = {(h.get("type"), h.get("model_id"), h.get("message")) for h in history if h.get("type") != "snapshot"}
    new_alerts = [a for a in alerts if (a.get("type"), a.get("model_id"), a.get("message")) not in fingerprints]
    kept = [h for h in history if h.get("type") != "snapshot"]
    merged = kept + new_alerts + snapshots
    _save_alert_history(merged)
    return alerts

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




@app.route("/api/leaderboard")
def api_leaderboard():
    report = _load_kpi_report()
    models = _extract_model_metrics(report)
    rank = sorted(models, key=lambda m: ((m.get("mean_hits") or 0), (m.get("improvement_pct") or -999), -(m.get("p_value") or 1), -(m.get("std_hits") or 999)), reverse=True)
    return jsonify(rank)


@app.route("/api/compare")
def api_compare():
    a = request.args.get("model_a")
    b = request.args.get("model_b")
    models = {m["id"]: m for m in _extract_model_metrics(_load_kpi_report())}
    if a not in models or b not in models:
        return jsonify({"error": "model_a/model_b inválidos"}), 400
    ma, mb = models[a], models[b]
    delta = {
        "mean_hits": (ma.get("mean_hits") or 0) - (mb.get("mean_hits") or 0),
        "improvement_pct": (ma.get("improvement_pct") or 0) - (mb.get("improvement_pct") or 0),
        "p_value": (ma.get("p_value") or 0) - (mb.get("p_value") or 0),
        "std_hits": (ma.get("std_hits") or 0) - (mb.get("std_hits") or 0),
    }
    return jsonify({"model_a": ma, "model_b": mb, "delta": delta, "distribution": {"a": ma.get("hits_distribution", {}), "b": mb.get("hits_distribution", {})}})


@app.route("/api/alerts")
def api_alerts():
    pvalue_threshold = float(request.args.get("pvalue_threshold", 0.05))
    moving_avg_drop_limit = float(request.args.get("moving_avg_drop_limit", 0.15))
    alerts = _evaluate_alerts(_extract_model_metrics(_load_kpi_report()), pvalue_threshold, moving_avg_drop_limit)
    return jsonify({"active": alerts, "count": len(alerts)})


@app.route("/api/alerts/history")
def api_alerts_history():
    return jsonify([h for h in _load_alert_history() if h.get("type") != "snapshot"])


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
