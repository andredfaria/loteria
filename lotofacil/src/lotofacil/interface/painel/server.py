"""Dashboard server — Flask + SQLite-backed polling for command execution."""

import os
import sys
import json
import threading
import subprocess
import time
import re
import logging
import uuid
import hmac
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import secrets
from functools import wraps
from flask import (
    Flask, jsonify, request, send_from_directory, Response,
    session, redirect, url_for, render_template_string,
)

from lotofacil.interface.painel.commands import COMMANDS, BASE  # noqa: E402
from lotofacil.interface.painel.treino_registry import TreinoRegistry
from lotofacil.servicos.roi_lab import rodar_backtest_roi as _rodar_backtest_roi
from lotofacil.infra.avaliacao.metricas import LotofacilMetrics
from lotofacil.infra.avaliacao.significancia import compare_vs_baseline
from lotofacil.infra.config import (
    NUMEROS_POR_SORTEIO as NUMBERS_PER_DRAW,
    RANDOM_SEED,
    TOTAL_NUMEROS as TOTAL_NUMBERS,
    DADOS_DIR as _DADOS_DIR,
    SAIDA_DIR as _SAIDA_DIR,
    MODELOS_DIR,
    DB_PATH,
)
import random
import statistics

_ANSI_RE = re.compile(r'\x1b(?:\[[0-9;]*[mGKHFABCDEFsuJKH]|[()][AB012])')
_procs: dict[str, subprocess.Popen[str]] = {}
_freq_cache: dict = {}           # {"data": {...}, "ts": float}
_FREQ_TTL = 300                  # 5 minutes
_quality_cache: dict = {}        # {last_n: {"data": {...}, "ts": float}}
_QUALITY_TTL = 120               # 2 minutes
_SRC = Path(__file__).resolve().parent.parent.parent.parent.parent / "src"
_LOTOFACIL_BIN = str(Path(sys.executable).parent / "lotofacil")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub('', text)


app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("DASHBOARD_AUTH_SECRET") or secrets.token_hex(32)
app.permanent_session_lifetime = timedelta(days=30)

BASE_DIR = BASE
DADOS_DIR = _DADOS_DIR
SAIDA_DIR = _SAIDA_DIR
_ROI_STRATEGIES_PATH: Path = _SAIDA_DIR / "roi_strategies.json"
MODELS_CORE_DIR = MODELOS_DIR
MODELS_LAB_DIR = SAIDA_DIR / "experimentos"

# Lab experiment models: src/lotofacil/experimentos/saved_models/
_LAB_MODELS_DIR = Path(__file__).resolve().parents[2] / "experimentos" / "saved_models"

_registry = TreinoRegistry(SAIDA_DIR / "treinos.db")


def _configure_logging() -> logging.Logger:
    log_dir = SAIDA_DIR / "logs"
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
    jsons = sorted(DADOS_DIR.glob("concurso_*.json"), key=lambda p: int(p.stem.split("_")[1]) if p.stem.count("_") >= 1 else 0)
    if not jsons:
        return {"latest": None, "total": 0}
    last = jsons[-1]
    try:
        with open(last) as f:
            data = json.load(f)
        dezenas_raw = data.get("dezenas", [])
        dezenas = [int(n) for n in dezenas_raw if str(n).strip().isdigit()] if dezenas_raw else []
        return {
            "latest": {"concurso": data.get("concurso"), "data": data.get("data"), "dezenas": dezenas or None},
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
    path = SAIDA_DIR / "relatorios" / "kpi_report.json"
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
    out = SAIDA_DIR / "alertas"
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

        hit_dist = LotofacilMetrics.distribution_of_hits(results)

        models.append({
            "model": approach,
            "mean_hits": round(baseline["model_mean"], 3),
            "improvement_pct": round(baseline["improvement_pct"], 2),
            "p_value": round(sig.p_value, 4),
            "stability": {"std_hits": round(std_hits, 3), "var_hits": round(var_hits, 3)},
            "sample_size": len(grp_sorted),
            "hit_distribution": {str(k): v for k, v in hit_dist.items()},
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


_DRAW_HOUR = 21  # sorteio ocorre às 21h (índice no array horário do Open-Meteo)


def _concurso_num(p: Path) -> int:
    try:
        return int(p.stem.split("_")[1])
    except Exception:
        return 0


def _phase_label(phase: float) -> str:
    """Converte fase lunar [0,1] para rótulo em português.

    Limiares: nova<0.125, crescente<0.375, cheia<0.625, minguante<0.875.
    """
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
                        temp_21 = temps[_DRAW_HOUR] if len(temps) > _DRAW_HOUR else None
                        precip_21 = precips[_DRAW_HOUR] if len(precips) > _DRAW_HOUR else None
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
                    dt = datetime.strptime(data_str, "%d/%m/%Y")
                    lua_file = lua_dir / dt.strftime("%Y-%m-%d.json")
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

    clima_total = sum(1 for _ in clima_dir.glob("clima_concurso*.json")) if clima_dir.exists() else 0
    lua_total = sum(1 for _ in lua_dir.glob("*.json")) if lua_dir.exists() else 0

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

_LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Login — Lotofácil Dashboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0f1117;color:#e2e8f0;font-family:monospace;display:flex;
     align-items:center;justify-content:center;height:100vh}
.card{background:#1a1f2e;border:1px solid #2d3748;border-radius:10px;padding:2rem;width:320px}
h1{font-size:1.1rem;margin-bottom:1.5rem;color:#60a5fa}
label{font-size:0.78rem;color:#94a3b8;display:block;margin-bottom:0.3rem}
input[type=password]{width:100%;padding:0.5rem 0.75rem;background:#0f1117;color:#e2e8f0;
  border:1px solid #2d3748;border-radius:5px;font-family:monospace;font-size:0.9rem;margin-bottom:1rem}
input[type=password]:focus{outline:none;border-color:#60a5fa}
button{width:100%;padding:0.55rem;background:#1e3a5f;color:#60a5fa;border:1px solid #60a5fa;
  border-radius:5px;font-family:monospace;font-size:0.9rem;cursor:pointer}
button:hover{background:#2d4a6f}
.error{color:#f87171;font-size:0.78rem;margin-bottom:0.75rem}
</style>
</head>
<body>
<div class="card">
  <h1>🎰 Lotofácil Dashboard</h1>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  <form method="post">
    <label>Senha</label>
    <input type="password" name="password" autofocus autocomplete="current-password">
    <button type="submit">Entrar</button>
  </form>
</div>
</body>
</html>"""


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
    password = os.environ.get("DASHBOARD_PASSWORD", "")
    if not password:
        return None
    if session.get("authenticated"):
        return None
    if request.endpoint in ("login_page", "logout", "static"):
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "unauthorized"}), 401
    return redirect(url_for("login_page"))


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
    latest = info["latest"]
    if latest and latest.get("concurso"):
        dezenas = _get_draw_dezenas(int(latest["concurso"]))
        if dezenas:
            latest["dezenas"] = dezenas
    return jsonify({
        "last_concurso": latest,
        "total_draws": info["total"],
        "games_count": len(_list_game_files()),
        "timestamp": datetime.now().isoformat(),
        "auth_enabled": bool(os.environ.get("DASHBOARD_PASSWORD", "")),
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
    cached = _quality_cache.get(last_n)
    if cached and (time.time() - cached["ts"]) < _QUALITY_TTL:
        return jsonify(cached["data"])
    result = _build_quality_payload(window_size=last_n)
    _quality_cache[last_n] = {"data": result, "ts": time.time()}
    return jsonify(result)


def _invalidate_quality_cache() -> None:
    _quality_cache.clear()




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


@app.route("/api/dados/frequencia")
def api_dados_frequencia():
    if _freq_cache and (time.time() - _freq_cache.get("ts", 0)) < _FREQ_TTL:
        return jsonify(_freq_cache["data"])
    freq: dict[int, int] = {i: 0 for i in range(1, 26)}
    total = 0
    for f in sorted(DADOS_DIR.glob("concurso_*.json"), key=_concurso_num):
        try:
            data = json.loads(f.read_text())
            for n in data.get("dezenas", []):
                n = int(n)
                if 1 <= n <= 25:
                    freq[n] += 1
            total += 1
        except Exception:
            pass
    avg = round((total * 15) / 25, 1) if total else 0
    result = {"frequency": freq, "total_draws": total, "expected_avg": avg}
    _freq_cache["data"] = result
    _freq_cache["ts"] = time.time()
    return jsonify(result)


@app.route("/api/dados/export-csv")
def api_dados_export_csv():
    files = sorted(DADOS_DIR.glob("concurso_*.json"), key=_concurso_num, reverse=True)
    def generate():
        yield "concurso,data,dezenas\n"
        for f in files:
            try:
                data = json.loads(f.read_text())
                c = data.get("concurso", "")
                d = data.get("data", "")
                dez = " ".join(str(n) for n in data.get("dezenas", []))
                yield f"{c},{d},{dez}\n"
            except Exception:
                pass
    return Response(generate(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=sorteios.csv"})


@app.route("/api/dados/page-for-concurso")
def api_dados_page_for_concurso():
    concurso = request.args.get("concurso", type=int)
    per_page = request.args.get("per_page", default=25, type=int)
    if not concurso:
        return jsonify({"error": "concurso required"}), 400
    files = sorted(DADOS_DIR.glob("concurso_*.json"), key=_concurso_num, reverse=True)
    for i, f in enumerate(files):
        if _concurso_num(f) == concurso:
            page = (i // per_page) + 1
            return jsonify({"page": page, "found": True, "concurso": concurso})
    return jsonify({"found": False, "concurso": concurso})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    body = request.get_json(force=True) or {}
    action = body.get("action")
    if not action:
        return jsonify({"error": "Missing 'action' field"}), 400

    for cat in COMMANDS.values():
        for item in cat["items"]:
            if item["id"] == action:
                task_id = f"task_{int(time.time() * 1000)}_{action}"
                _registry.create_job(task_id)
                t = threading.Thread(
                    target=_run_command,
                    args=(task_id, _registry, item["cmd"], item["cwd"]),
                    daemon=True,
                )
                t.start()
                return jsonify({"task_id": task_id})
    return jsonify({"error": f"Unknown action: {action}"}), 400


# ─── Command Runner ────────────────────────────────────────────

def _run_command(
    task_id: str,
    registry: "TreinoRegistry",
    cmd: list[str],
    cwd: str,
    on_complete=None,
):
    LOGGER.info("TASK %s started cmd=%s cwd=%s", task_id, " ".join(cmd), cwd)

    cmd = [
        sys.executable if c == "python"
        else _LOTOFACIL_BIN if c == "lotofacil"
        else c
        for c in cmd
    ]
    env = {
        **os.environ,
        "PYTHONPATH": str(_SRC),
        "CUDA_VISIBLE_DEVICES": "-1",   # força CPU; evita erro cuInit em máquinas sem GPU
        "TF_CPP_MIN_LOG_LEVEL": "3",    # suprime INFO/WARNING/ERROR do TF (só FATAL)
    }
    output_lines: list[str] = []
    ret = -1

    try:
        first = f"$ {' '.join(cmd)}"
        registry.write_line(task_id, first)
        output_lines.append(first)

        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        _procs[task_id] = proc
        for line in iter(proc.stdout.readline, ""):
            clean = _strip_ansi(line.rstrip("\n"))
            LOGGER.info("TASK %s output: %s", task_id, clean)
            output_lines.append(clean)
            registry.write_line(task_id, clean)
        proc.stdout.close()
        ret = proc.wait()
        LOGGER.info("TASK %s finished exit_code=%s", task_id, ret)
        if ret == 0:
            registry.write_line(task_id, "")
            registry.write_line(task_id, "✅ Comando concluído com sucesso.")
            if on_complete:
                on_complete(success=True, output_lines=output_lines)
        else:
            registry.write_line(task_id, "")
            registry.write_line(task_id, f"⚠️  Comando finalizou com código {ret}.")
            if on_complete:
                on_complete(success=False, output_lines=output_lines)
    except Exception as e:
        LOGGER.exception("TASK %s failed", task_id)
        registry.write_line(task_id, f"❌ Erro: {e}")
        if on_complete:
            on_complete(success=False, output_lines=output_lines)
    finally:
        _procs.pop(task_id, None)
        registry.finish_job(task_id, ret == 0)


# ─── Treino Registry — helpers ─────────────────────────────────

_CONFIG_SIG_MAP = {
    "base": "base+temp+priors",
    "lua": "base+temp+priors+lua",
    "clima": "base+temp+priors+clima",
    "lua_clima": "base+temp+priors+lua+clima",
}


def _slug(text: str) -> str:
    """Sanitize a string to safe filename characters."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^\w]+", "_", ascii_str).strip("_")[:40] or "treino"


def _extract_model_path_from_output(lines: list[str]) -> str | None:
    for line in lines:
        if line.startswith("TREINO_MODELO_PATH:"):
            return line.split(":", 1)[1].strip()
    return None


def _read_meta_from_keras(keras_path: str) -> dict:
    meta_path = Path(keras_path).with_suffix(".meta.json")
    if not meta_path.exists():
        return {}
    try:
        raw = json.loads(meta_path.read_text())
        hist = raw.get("history", {})
        val_loss = hist.get("val_loss", [])
        return {
            "val_loss_final": round(val_loss[-1], 5) if val_loss else None,
            "epochs_trained": len(hist.get("loss", [])),
        }
    except Exception:
        return {}


# ─── Treino Registry — API routes ──────────────────────────────

@app.route("/api/treinos/iniciar", methods=["POST"])
def api_treinos_iniciar():
    body = request.get_json(force=True) or {}
    nome = (body.get("nome") or "treino").strip()
    tipo_config = body.get("tipo_config", "base")
    params = body.get("parametros") or {}

    config_sig = _CONFIG_SIG_MAP.get(tipo_config, tipo_config)
    treino_id = uuid.uuid4().hex[:8]
    nome_slug = _slug(nome)
    model_name = f"{treino_id}_{nome_slug}"

    _registry.criar(treino_id, nome, tipo_config, params)

    cmd = ["lotofacil", "lab", "train", "--config", config_sig, "--name", model_name]
    if params.get("epochs"):
        cmd += ["--epochs", str(params["epochs"])]
    if params.get("n_draws"):
        cmd += ["--n-draws", str(params["n_draws"])]
    if params.get("seed"):
        cmd += ["--seed", str(params["seed"])]
    if params.get("window_size"):
        cmd += ["--window-size", str(params["window_size"])]

    task_id = f"treino_{int(time.time() * 1000)}_{treino_id}"
    _registry.create_job(task_id)

    def on_done(success: bool, output_lines: list[str]):
        if success:
            keras_path = _extract_model_path_from_output(output_lines)
            if not keras_path:
                keras_path = str(_LAB_MODELS_DIR / f"neural_{model_name}.keras")
            metricas = _read_meta_from_keras(keras_path)
            _registry.registrar_modelo(treino_id, keras_path, metricas)
            LOGGER.info("TREINO %s registered: %s", treino_id, keras_path)
            _invalidate_quality_cache()
        else:
            _registry.marcar_falha(treino_id)
            LOGGER.warning("TREINO %s failed", treino_id)

    t = threading.Thread(
        target=_run_command,
        args=(task_id, _registry, cmd, str(BASE_DIR)),
        kwargs={"on_complete": on_done},
        daemon=True,
    )
    t.start()
    return jsonify({"treino_id": treino_id, "task_id": task_id})


@app.route("/api/treinos")
def api_treinos_listar():
    return jsonify(_registry.listar())


@app.route("/api/treinos/comparar")
def api_treinos_comparar():
    id_a = request.args.get("a")
    id_b = request.args.get("b")
    if not id_a or not id_b:
        return jsonify({"error": "Parâmetros 'a' e 'b' são obrigatórios"}), 400
    ta = _registry.buscar(id_a)
    tb = _registry.buscar(id_b)
    if not ta:
        return jsonify({"error": f"Treino '{id_a}' não encontrado"}), 404
    if not tb:
        return jsonify({"error": f"Treino '{id_b}' não encontrado"}), 404

    def _met(t, key):
        m = t.get("metricas") or {}
        return m.get(key)

    delta = {
        "val_loss_final": (
            round((_met(ta, "val_loss_final") or 0) - (_met(tb, "val_loss_final") or 0), 5)
            if _met(ta, "val_loss_final") is not None and _met(tb, "val_loss_final") is not None
            else None
        ),
        "epochs_trained": (
            (_met(ta, "epochs_trained") or 0) - (_met(tb, "epochs_trained") or 0)
        ),
    }
    return jsonify({"a": ta, "b": tb, "delta": delta})


@app.route("/api/jobs/<task_id>/poll")
def api_jobs_poll(task_id: str):
    offset = request.args.get("offset", default=0, type=int)
    return jsonify(_registry.poll_job(task_id, offset))


@app.route("/api/jobs/<task_id>/cancel", methods=["POST"])
def api_jobs_cancel(task_id: str):
    proc = _procs.get(task_id)
    if proc is None:
        return jsonify({"error": "Processo não encontrado ou já finalizado"}), 404
    try:
        proc.terminate()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})


@app.route("/api/treinos/<treino_id>")
def api_treino_detalhe(treino_id: str):
    t = _registry.buscar(treino_id)
    if not t:
        return jsonify({"error": "Não encontrado"}), 404
    return jsonify(t)


@app.route("/api/treinos/<treino_id>", methods=["PATCH"])
def api_treino_renomear(treino_id: str):
    body = request.get_json(force=True) or {}
    nome = (body.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Nome não pode ser vazio"}), 400
    if not _registry.renomear(treino_id, nome):
        return jsonify({"error": "Não encontrado"}), 404
    return jsonify({"ok": True, "nome": nome})


@app.route("/api/treinos/<treino_id>", methods=["DELETE"])
def api_treino_deletar(treino_id: str):
    t = _registry.buscar(treino_id)
    if not t:
        return jsonify({"error": "Não encontrado"}), 404
    if t.get("status") == "running":
        # Cancel the running job before deleting
        task_key = next((k for k in _procs if treino_id in k), None)
        if task_key:
            try:
                _procs[task_key].terminate()
            except Exception:
                pass
        _registry.atualizar_status(treino_id, "cancelled")
    arquivo = t.get("arquivo_modelo")
    if arquivo:
        keras_path = Path(arquivo)
        for p in [keras_path, keras_path.with_suffix(".meta.json")]:
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
    deleted = _registry.deletar(treino_id)
    if not deleted:
        return jsonify({"error": "Falha ao remover"}), 500
    return jsonify({"ok": True})


def _get_draw_dezenas(concurso: int) -> list[int] | None:
    try:
        import sqlite3 as _sqlite3
        with _sqlite3.connect(str(DB_PATH)) as conn:
            row = conn.execute(
                "SELECT dezenas FROM concursos WHERE concurso = ?", (concurso,)
            ).fetchone()
        if row:
            return json.loads(row[0])
    except Exception:
        pass
    return None


def _compute_acertos(jogos: list[list[int]], dezenas_reais: list[int] | None) -> list[int] | None:
    if not dezenas_reais:
        return None
    real_set = set(dezenas_reais)
    return [len(set(j) & real_set) for j in jogos]


@app.route("/api/jogos-gerados")
def api_jogos_gerados():
    limit = request.args.get("limit", default=100, type=int)
    items = _registry.listar_jogos(limit=max(1, min(limit, 500)))
    # enrich with actual draw results when available
    cache: dict[int, list[int] | None] = {}
    for item in items:
        concurso = item.get("concurso")
        if concurso not in cache:
            cache[concurso] = _get_draw_dezenas(concurso)
        real = cache[concurso]
        if real:
            item["dezenas_reais"] = real
            jogos = item.get("jogos") or []
            item["acertos_por_jogo"] = [
                len(set(jogo) & set(real)) for jogo in jogos
            ]
    return jsonify(items)


@app.route("/api/treinos/<treino_id>/gerar", methods=["POST"])
def api_treino_gerar(treino_id: str):
    t = _registry.buscar(treino_id)
    if not t:
        return jsonify({"error": "Treino não encontrado"}), 404
    if t.get("status") != "completed":
        return jsonify({"error": "Treino ainda não concluído"}), 400

    arquivo_modelo = t.get("arquivo_modelo")
    if not arquivo_modelo or not Path(arquivo_modelo).exists():
        return jsonify({"error": "Arquivo do modelo não encontrado"}), 404

    body = request.get_json(force=True) or {}
    n_jogos = max(1, min(int(body.get("n_jogos", 1)), 20))
    n_numeros = max(11, min(int(body.get("n_numeros", 15)), 15))
    concurso_alvo_raw = body.get("concurso_alvo")

    try:
        import sys as _sys
        _sys.path.insert(0, str(_SRC))
        from lotofacil.experimentos.data.feature_flags import FeatureConfig
        from lotofacil.experimentos.data.draws_loader import load_draws_last_n
        from lotofacil.experimentos.models.neural_modular import NeuralModular

        tipo_config = t.get("tipo_config", "base")
        config_sig = _CONFIG_SIG_MAP.get(tipo_config, tipo_config)
        cfg = FeatureConfig.from_signature(config_sig)

        draws = load_draws_last_n(500)
        if not draws:
            return jsonify({"error": "Sem dados de sorteios disponíveis"}), 500

        model = NeuralModular(cfg)
        model.load(Path(arquivo_modelo))
        proba = model.predict_proba(draws)  # shape (25,)

        rng = np.random.default_rng()
        jogos = []
        for _ in range(n_jogos):
            noise = rng.normal(0, 0.02, size=proba.shape)
            scores = proba + noise
            top_idx = np.argsort(scores)[::-1][:n_numeros]
            jogos.append(sorted(int(i + 1) for i in top_idx))

        try:
            next_concurso = int(concurso_alvo_raw) if concurso_alvo_raw and int(concurso_alvo_raw) >= 1 else draws[-1].concurso + 1
        except (TypeError, ValueError):
            next_concurso = draws[-1].concurso + 1

        # Persist each game to filesystem
        jogos_dir = SAIDA_DIR / "jogos"
        jogos_dir.mkdir(parents=True, exist_ok=True)
        for i, jogo in enumerate(jogos, 1):
            out_path = jogos_dir / f"predicao_lab_{treino_id}_j{i}_{next_concurso}.json"
            out_path.write_text(
                json.dumps({
                    "concurso": next_concurso,
                    "abordagem": f"lab_{treino_id}",
                    "dezenas": jogo,
                    "confianca": None,
                    "treino_id": treino_id,
                    "treino_nome": t.get("nome"),
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        # Persist to registry for history tab
        _registry.salvar_jogo(treino_id, t.get("nome", treino_id), next_concurso, jogos)

        dezenas_reais = _get_draw_dezenas(next_concurso)
        acertos_por_jogo = _compute_acertos(jogos, dezenas_reais)

        return jsonify({
            "treino_id": treino_id,
            "treino_nome": t.get("nome"),
            "concurso": next_concurso,
            "n_jogos": n_jogos,
            "n_numeros": n_numeros,
            "jogos": jogos,
            "dezenas_reais": dezenas_reais,
            "acertos_por_jogo": acertos_por_jogo,
        })

    except Exception as exc:
        LOGGER.exception("Erro ao gerar jogos para treino %s", treino_id)
        return jsonify({"error": str(exc)}), 500


# ─── ROI Lab ──────────────────────────────────────────────────


def _load_roi_strategies() -> list[dict]:
    if not _ROI_STRATEGIES_PATH.exists():
        return []
    try:
        return json.loads(_ROI_STRATEGIES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_roi_strategies(strategies: list[dict]) -> None:
    _ROI_STRATEGIES_PATH.write_text(
        json.dumps(strategies, indent=2, ensure_ascii=False), encoding="utf-8"
    )


@app.route("/api/roi/backtest", methods=["POST"])
def api_roi_backtest():
    body = request.get_json(force=True) or {}
    filtros: dict = {k: v for k, v in (body.get("filtros") or {}).items() if v is not None}
    n_jogos = max(1, min(int(body.get("n_jogos", 5)), 20))
    janela = body.get("janela")
    if janela is not None:
        janela = max(10, min(int(janela), 5000))
    try:
        holdout_pct = float(body.get("holdout_pct", 0.0))
        holdout_pct = max(0.0, min(holdout_pct, 0.9))
    except (TypeError, ValueError):
        holdout_pct = 0.0
    try:
        result = _rodar_backtest_roi(
            filtros,
            n_jogos_por_sorteio=n_jogos,
            janela=janela,
            holdout_pct=holdout_pct,
        )
        return jsonify(result)
    except Exception as exc:
        LOGGER.exception("roi backtest error")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/roi/strategies", methods=["GET"])
def api_roi_strategies_list():
    return jsonify(_load_roi_strategies())


@app.route("/api/roi/strategies", methods=["POST"])
def api_roi_strategies_save():
    body = request.get_json(force=True) or {}
    nome = (body.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "nome é obrigatório"}), 400
    strategies = _load_roi_strategies()
    strategies = [s for s in strategies if s.get("nome") != nome]
    strategies.append({
        "nome": nome,
        "filtros": body.get("filtros") or {},
        "resumo": body.get("resumo") or {},
    })
    _save_roi_strategies(strategies)
    return jsonify({"ok": True})


@app.route("/api/roi/strategies/<nome>", methods=["DELETE"])
def api_roi_strategies_delete(nome: str):
    strategies = [s for s in _load_roi_strategies() if s.get("nome") != nome]
    _save_roi_strategies(strategies)
    return jsonify({"ok": True})


@app.route("/api/jobs/<task_id>/stream")
def api_job_stream(task_id: str):
    def generate():
        offset = 0
        while True:
            result = _registry.poll_job(task_id, offset)
            for line in result["lines"]:
                yield f"data: {json.dumps({'text': line})}\n\n"
            offset = result["next_offset"]
            if result["done"]:
                success = result.get("success", False)
                yield f"event: done\ndata: {json.dumps({'success': bool(success)})}\n\n"
                return
            time.sleep(0.15)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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
