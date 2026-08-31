from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier

from lotofacil.dominio.entidades import Draw
from lotofacil.infra.atributos.builder import FeatureBuilder
from lotofacil.experimentos.features.similarity import (
    find_similar, compute_similarity_weighted_freq,
)
from lotofacil.experimentos.features.padroes_similares import calcular_score_padroes21
from lotofacil.experimentos.analysis.gerador_melhor_jogo import (
    _frequencia_scores, _coocorrencia_scores, otimizar_deterministico,
    _score_filters,
)

logger = logging.getLogger(__name__)

ESTRATEGIAS = [
    ("RF (50%)",      {"rf": 0.50, "freq": 0.30, "cooc": 0.20, "sim": 0.00, "pad": 0.00}),
    ("Equilibrado",   {"rf": 0.20, "freq": 0.20, "cooc": 0.20, "sim": 0.20, "pad": 0.20}),
    ("Freq+Cooc",     {"rf": 0.00, "freq": 0.50, "cooc": 0.50, "sim": 0.00, "pad": 0.00}),
    ("RF Híbrido",    {"rf": 0.40, "freq": 0.10, "cooc": 0.05, "sim": 0.25, "pad": 0.20}),
    ("Sim+Padrões",   {"rf": 0.00, "freq": 0.00, "cooc": 0.00, "sim": 0.50, "pad": 0.50}),
]


def _score_ensemble_rapido(
    rf_s: np.ndarray, freq_s: np.ndarray, cooc_s: np.ndarray,
    sim_s: np.ndarray, pad_s: np.ndarray, pesos: Dict[str, float],
) -> np.ndarray:
    s = pesos["rf"] * rf_s + pesos["freq"] * freq_s + pesos["cooc"] * cooc_s
    s += pesos["sim"] * sim_s + pesos["pad"] * pad_s
    lo, hi = s.min(), s.max()
    if hi > lo:
        s = (s - lo) / (hi - lo)
    return s


def _parse_iso(data_str: str) -> Optional[str]:
    if "/" in data_str:
        parts = data_str.split("/")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    if "-" in data_str and len(data_str) == 10:
        return data_str
    return None


def rodar_backtest_walkforward(
    draws: List[Draw],
    start_concurso: int = 2000,
    retrain_every: int = 50,
) -> Dict[str, Any]:
    logger.info("Walk-forward: concursos %d-%d, %d estratégias",
                start_concurso, draws[-1].concurso, len(ESTRATEGIAS))

    resultados: Dict[str, List[Dict]] = {nome: [] for nome, _ in ESTRATEGIAS}

    last_rf_train = 0
    rf_model = None
    builder = FeatureBuilder()

    for idx, target_draw in enumerate(draws):
        if target_draw.concurso < start_concurso:
            continue
        if target_draw.concurso >= draws[-1].concurso:
            continue

        train_draws = draws[:idx]
        if len(train_draws) < 300:
            continue

        concurso = target_draw.concurso
        data_iso = _parse_iso(target_draw.data) or date.today().isoformat()

        if concurso - last_rf_train >= retrain_every or rf_model is None:
            try:
                X, y = builder.build_dataset(train_draws)
                x_infer = builder.build_inference(train_draws)
                rf = MultiOutputClassifier(
                    RandomForestClassifier(n_estimators=100, max_depth=8,
                                           min_samples_leaf=5, random_state=42, n_jobs=-1),
                    n_jobs=1,
                )
                rf.fit(X, y)
                probas_list = rf.predict_proba(x_infer)
                rf_s = np.empty(25, dtype=np.float32)
                for j, p in enumerate(probas_list):
                    rf_s[j] = p[0, 1] if p.shape[1] == 2 else (float(p[0, 0]) if p.shape[1] == 1 else 0.5)
                lo, hi = rf_s.min(), rf_s.max()
                if hi > lo:
                    rf_s = (rf_s - lo) / (hi - lo)
                else:
                    rf_s[:] = 0.5
                rf_model = rf_s
                last_rf_train = concurso
            except Exception as e:
                logger.warning("RF erro no concurso %d: %s", concurso, e)
                continue

        rf_s = rf_model
        freq_s = _frequencia_scores(train_draws, ultimos_k=50)
        cooc_s = _coocorrencia_scores(train_draws, ultimos_k=50)

        sim_r = find_similar(train_draws, target_date_iso=data_iso, top_n=10)
        sim_s = compute_similarity_weighted_freq(sim_r) if sim_r else np.ones(25, dtype=np.float32) * 0.5
        pad_s = calcular_score_padroes21(train_draws)

        real_set = set(target_draw.dezenas)

        for nome, pesos in ESTRATEGIAS:
            scores = _score_ensemble_rapido(rf_s, freq_s, cooc_s, sim_s, pad_s, pesos)
            jogo = otimizar_deterministico(scores)
            hits = len(set(jogo) & real_set)

            resultados[nome].append({
                "concurso": concurso,
                "data": target_draw.data,
                "jogo": jogo,
                "hits": hits,
                "filter_ok": _score_filters(jogo),
            })

        if concurso % 200 == 0:
            logger.info("Progresso: concurso %d/%d", concurso, draws[-1].concurso)

    return _consolidar_resultados(resultados)


def _consolidar_resultados(resultados: Dict[str, List[Dict]]) -> Dict[str, Any]:
    consolidado = {}
    for nome, entries in resultados.items():
        hits_arr = np.array([e["hits"] for e in entries], dtype=np.int32)
        n = len(entries)
        if n == 0:
            consolidado[nome] = {"erro": "sem dados"}
            continue

        dist = {str(h): int((hits_arr >= h).sum()) for h in [11, 12, 13, 14, 15]}
        media_acertos_geral = float(hits_arr.mean())

        max_consecutivo = 0
        streak = 0
        for h in hits_arr:
            if h >= 11:
                streak += 1
                max_consecutivo = max(max_consecutivo, streak)
            else:
                streak = 0

        hit_details = []
        for entry in entries:
            if entry["hits"] >= 11:
                hit_details.append({
                    "concurso": entry["concurso"],
                    "data": entry["data"],
                    "hits": entry["hits"],
                })

        consolidado[nome] = {
            "total_concursos": n,
            "media_acertos": round(media_acertos_geral, 4),
            "distribuicao": dist,
            "taxa_acerto_11": round(dist["11"] / n * 100, 2),
            "taxa_acerto_12": round(dist["12"] / n * 100, 2),
            "taxa_acerto_13": round(dist["13"] / n * 100, 2),
            "taxa_acerto_14": round(dist["14"] / n * 100, 2),
            "taxa_acerto_15": round(dist["15"] / n * 100, 2),
            "concursos_para_acertar_11": round(n / dist["11"], 1) if dist["11"] > 0 else None,
            "maior_sequencia_acertos": max_consecutivo,
            "hit_details": hit_details,
        }

    return {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "estrategias": [nome for nome, _ in ESTRATEGIAS],
            "total_estrategias": len(ESTRATEGIAS),
        },
        "resultados": consolidado,
        "melhor_estrategia": _melhor_estrategia(consolidado),
    }


def _melhor_estrategia(consolidado: Dict) -> Dict:
    best = None
    best_score = -1
    for nome, dados in consolidado.items():
        if "erro" in dados:
            continue
        score = dados["taxa_acerto_11"] * 100 + dados["taxa_acerto_12"] * 1000 + dados["taxa_acerto_13"] * 10000
        if score > best_score:
            best_score = score
            best = {"nome": nome, "taxa_11": dados["taxa_acerto_11"], "taxa_13": dados["taxa_acerto_13"]}
    return best


def salvar_backtest(resultado: Dict[str, Any], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path