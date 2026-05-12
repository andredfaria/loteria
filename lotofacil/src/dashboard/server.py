"""Dashboard server — Flask + SSE for real-time command execution."""

import os
import sys
import json
import queue
import threading
import subprocess
import time
import re
import logging
from logging.handlers import RotatingFileHandler
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


def _configure_logging() -> logging.Logger:
    log_dir = BASE / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "dashboard_server.log"

    logger = logging.getLogger("lotofacil.dashboard")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_path, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger


LOGGER = _configure_logging()

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
            pass
    return draws


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


def _concurso_num(p: Path) -> int:
    try:
        return int(p.stem.split("_")[1])
    except Exception:
        return 0


def _phase_label(phase: float) -> str:
    if phase < 0.125 or phase >= 0.875:
        return "Nova"
    if phase < 0.375:
        return "Crescente"
    if phase < 0.625:
        return "Cheia"
    return "Minguante"


def _build_dados_page(page: int, per_page: int) -> dict:
    all_files = sorted(DADOS_DIR.glob("concurso_*.json"), key=_concurso_num, reverse=True)
    total = len(all_files)
    start = (page - 1) * per_page
    page_files = all_files[start: start + per_page]

    clima_dir = DADOS_DIR / "clima"
    lua_dir = DADOS_DIR / "lua"

    items = []
    for f in page_files:
        try:
            data = json.loads(f.read_text())
            concurso = data.get("concurso")
            data_str = data.get("data", "")
            dezenas = data.get("dezenas", [])

            # Climate
            clima = None
            if clima_dir.exists():
                matches = list(clima_dir.glob(f"clima_concurso{concurso}-*.json"))
                if matches:
                    try:
                        c = json.loads(matches[0].read_text())
                        hourly = c.get("hourly", {})
                        temps = hourly.get("temperature_2m", [])
                        precips = hourly.get("precipitation", [])
                        temp_21 = temps[21] if len(temps) > 21 else None
                        precip_21 = precips[21] if len(precips) > 21 else None
                        clima = {
                            "temp_c": round(temp_21, 1) if temp_21 is not None else None,
                            "precip_mm": round(precip_21, 1) if precip_21 is not None else None,
                        }
                    except Exception:
                        pass

            # Lunar
            lua = None
            if data_str and lua_dir.exists():
                try:
                    parts = data_str.split("/")
                    if len(parts) == 3:
                        date_iso = f"{parts[2]}-{parts[1]}-{parts[0]}"
                        lua_file = lua_dir / f"{date_iso}.json"
                        if lua_file.exists():
                            lua_data = json.loads(lua_file.read_text())
                            feats = lua_data.get("features", {})
                            phase = float(feats.get("phase", 0))
                            lua = {
                                "fase": _phase_label(phase),
                                "phase": round(phase, 3),
                            }
                except Exception:
                    pass

            items.append({
                "concurso": concurso,
                "data": data_str,
                "dezenas": dezenas,
                "clima": clima,
                "lua": lua,
            })
        except Exception:
            continue

    clima_total = len(list(clima_dir.glob("clima_concurso*.json"))) if clima_dir.exists() else 0
    lua_total = len(list(lua_dir.glob("*.json"))) if lua_dir.exists() else 0

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "clima_total": clima_total,
        "lua_total": lua_total,
        "items": items,
    }

def _extract_numbers(raw):
    """Extract game arrays from multiple known payload structures."""
    if raw is None:
        return []
    if isinstance(raw, list):
        if raw and isinstance(raw[0], (int, float)):
            return [raw]
        if raw and isinstance(raw[0], list):
            return [g for g in raw if isinstance(g, list) and len(g) > 0]
        if raw and isinstance(raw[0], dict):
            return [g.get("dezenas") for g in raw if isinstance(g.get("dezenas"), list) and len(g.get("dezenas")) > 0]
    if isinstance(raw, dict):
        dezenas = raw.get("dezenas")
        if isinstance(dezenas, list):
            return [dezenas]
        jogos = raw.get("jogos")
        if isinstance(jogos, dict):
            games = []
            for tier in jogos.values():
                if isinstance(tier, list):
                    for g in tier:
                        if isinstance(g, list) and len(g) > 0:
                            games.append(g)
                        elif isinstance(g, dict) and isinstance(g.get("dezenas"), list) and len(g.get("dezenas")) > 0:
                            games.append(g["dezenas"])
            return games
    return []


def _normalize_game_preview(filename: str):
    safe = Path(filename).name
    path = SAIDA_DIR / "jogos" / safe
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {
            "filename": safe,
            "preview_dezenas": [],
            "games_count": 0,
            "preview_status": "corrupted",
        }
    all_games = _extract_numbers(data)
    first_game = all_games[0] if all_games else []
    normalized = []
    for n in first_game:
        try:
            normalized.append(int(n))
        except Exception:
            continue
    return {
        "filename": safe,
        "preview_dezenas": normalized,
        "games_count": len(all_games),
        "preview_status": "ok" if normalized else "empty",
    }


# ─── API Endpoints ─────────────────────────────────────────────



@app.before_request
def _log_request():
    if request.path.startswith('/api'):
        LOGGER.info("REQ %s %s from=%s", request.method, request.path, request.remote_addr)


@app.after_request
def _log_response(response):
    if request.path.startswith('/api'):
        LOGGER.info("RES %s %s status=%s", request.method, request.path, response.status_code)
    return response


@app.errorhandler(Exception)
def _handle_uncaught_exception(exc):
    from werkzeug.exceptions import HTTPException
    if isinstance(exc, HTTPException):
        return exc
    LOGGER.exception("Unhandled server error on %s %s", request.method, request.path)
    return jsonify({"error": "Erro interno no servidor", "details": str(exc)}), 500

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


@app.route("/api/games/previews")
def api_games_previews():
    previews = []
    for game in _list_game_files()[:12]:
        item = _normalize_game_preview(game["filename"])
        if item is None:
            continue
        previews.append({
            **game,
            **item,
        })
    return jsonify(previews)


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
        return jsonify({
            "filename": safe,
            "games": _extract_numbers(data),
            "raw": data,
        })
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


@app.route("/api/dados")
def api_dados():
    page = max(1, request.args.get("page", default=1, type=int))
    per_page = min(max(1, request.args.get("per_page", default=50, type=int)), 100)
    return jsonify(_build_dados_page(page, per_page))


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

    LOGGER.info("TASK %s started cmd=%s cwd=%s", task_id, " ".join(cmd), cwd)

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
            clean_line = _strip_ansi(line.rstrip("\n"))
            LOGGER.info("TASK %s output: %s", task_id, clean_line)
            emit(clean_line)
        proc.stdout.close()
        ret = proc.wait()
        LOGGER.info("TASK %s finished exit_code=%s", task_id, ret)
        if ret == 0:
            emit("")
            emit("✅ Comando concluído com sucesso.")
        else:
            emit("")
            emit(f"⚠️  Comando finalizou com código {ret}.")
    except Exception as e:
        LOGGER.exception("TASK %s failed", task_id)
        emit(f"❌ Erro: {e}")
    finally:
        q.put(None)


# ─── Main ──────────────────────────────────────────────────────

def main():
    host = os.environ.get("DASHBOARD_HOST", "0.0.0.0")
    port = int(os.environ.get("DASHBOARD_PORT", "5000"))
    LOGGER.info("🎰 Lotofácil Dashboard")
    LOGGER.info("Servidor: http://%s:%s", host, port)
    LOGGER.info("Pressione Ctrl+C para parar.")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
