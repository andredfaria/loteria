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
