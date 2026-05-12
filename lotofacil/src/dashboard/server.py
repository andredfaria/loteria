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



def _load_draws_by_concurso() -> dict[int, list[int]]:
    draws: dict[int, list[int]] = {}
    for f in DADOS_DIR.glob("concurso_*.json"):
        try:
            payload = json.loads(f.read_text())
            concurso = int(payload.get("concurso"))
            dezenas = payload.get("dezenas") or payload.get("numeros")
            if isinstance(dezenas, list):
                draws[concurso] = [int(n) for n in dezenas]
        except Exception:
            continue
    return draws


def _calc_calibration_bins(points: list[tuple[float, float]], n_bins: int = 5) -> list[dict]:
    if not points:
        return []
    bins = [{"count": 0, "conf_sum": 0.0, "acc_sum": 0.0} for _ in range(n_bins)]
    for conf, acc in points:
        c = min(max(float(conf), 0.0), 1.0)
        idx = min(int(c * n_bins), n_bins - 1)
        b = bins[idx]
        b["count"] += 1
        b["conf_sum"] += c
        b["acc_sum"] += float(acc)

    out = []
    for i, b in enumerate(bins):
        if b["count"] == 0:
            continue
        lo = i / n_bins
        hi = (i + 1) / n_bins
        out.append({
            "bin": f"{lo:.1f}-{hi:.1f}",
            "count": b["count"],
            "avg_confidence": round(b["conf_sum"] / b["count"], 4),
            "avg_real_accuracy": round(b["acc_sum"] / b["count"], 4),
            "gap": round((b["conf_sum"] - b["acc_sum"]) / b["count"], 4),
        })
    return out


def _build_model_trend(window_short: int = 20, window_long: int = 50) -> dict:
    draws = _load_draws_by_concurso()
    series = []
    calibration_points: list[tuple[float, float]] = []

    games_dir = SAIDA_DIR / "jogos"
    for f in sorted(games_dir.glob("predicao_*.json"), key=lambda p: p.stat().st_mtime):
        try:
            data = json.loads(f.read_text())
            concurso = int(data.get("concurso"))
            predicted = data.get("dezenas", [])
            if not isinstance(predicted, list) or concurso not in draws:
                continue
            actual = draws[concurso]
            hits = len(set(int(n) for n in predicted) & set(actual))
            conf_raw = data.get("confianca")
            confidence = None
            if conf_raw is not None:
                confidence = float(conf_raw)
                if confidence > 1:
                    confidence = confidence / 100.0
                confidence = min(max(confidence, 0.0), 1.0)
                calibration_points.append((confidence, hits / 15.0))
            series.append({"concurso": concurso, "hits": hits, "confidence": confidence})
        except Exception:
            continue

    if not series:
        return {"series": [], "rolling": {}, "calibration": [], "summary": {}}

    series.sort(key=lambda r: r["concurso"])
    hits_values = [r["hits"] for r in series]

    for i, row in enumerate(series):
        short_slice = hits_values[max(0, i - window_short + 1):i + 1]
        long_slice = hits_values[max(0, i - window_long + 1):i + 1]
        row["rolling_mean_20"] = round(float(sum(short_slice) / len(short_slice)), 4)
        row["rolling_mean_50"] = round(float(sum(long_slice) / len(long_slice)), 4)

    tail_short = series[-window_short:]
    hit_rate_11_short = sum(1 for r in tail_short if r["hits"] >= 11) / len(tail_short)
    tail_long = series[-window_long:]
    hit_rate_11_long = sum(1 for r in tail_long if r["hits"] >= 11) / len(tail_long)

    recent = [r["hits"] for r in series[-6:]]
    drift_streak = 0
    for i in range(1, len(recent)):
        if recent[i] < recent[i - 1]:
            drift_streak += 1
        else:
            drift_streak = 0
    drift_alert = drift_streak >= 3

    return {
        "series": series,
        "calibration": _calc_calibration_bins(calibration_points, n_bins=5),
        "summary": {
            "n_evaluated": len(series),
            "mean_hits": round(float(sum(hits_values) / len(hits_values)), 4),
            "hit_rate_ge_11_w20": round(hit_rate_11_short, 4),
            "hit_rate_ge_11_w50": round(hit_rate_11_long, 4),
            "drift": {"decline_streak": drift_streak, "alert": drift_alert, "window": len(recent)},
        },
    }

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




@app.route("/api/models/trend")
def api_models_trend():
    return jsonify(_build_model_trend())

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
