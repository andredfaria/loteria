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
    get_target_moon, get_target_climate,
)
from lotofacil.experimentos.features.padroes_similares import calcular_score_padroes21
from lotofacil.infra.estrategias.quinze_dezenas.post_processor import (
    sa_with_restarts, filter_score,
)

logger = logging.getLogger(__name__)

NUMBERS = list(range(1, 26))
ENSEMBLE_WEIGHTS = {
    "rf": 0.35,
    "frequencia": 0.20,
    "coocorrencia": 0.10,
    "similaridade": 0.20,
    "padroes21": 0.15,
}


def _frequencia_scores(draws: List[Draw], ultimos_k: int = 50) -> np.ndarray:
    if len(draws) > ultimos_k:
        window = draws[-ultimos_k:]
    else:
        window = draws
    scores = np.zeros(25, dtype=np.float32)
    for d in window:
        for n in d.dezenas:
            scores[n - 1] += 1
    total = len(window)
    if total > 0:
        scores /= total
    lo, hi = scores.min(), scores.max()
    if hi > lo:
        scores = (scores - lo) / (hi - lo)
    return scores


def _coocorrencia_scores(draws: List[Draw], ultimos_k: int = 50) -> np.ndarray:
    if len(draws) > ultimos_k:
        window = draws[-ultimos_k:]
    else:
        window = draws
    cooc_matrix = np.zeros((25, 25), dtype=np.float32)
    for d in window:
        nums = list(d.dezenas)
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                a, b = nums[i] - 1, nums[j] - 1
                cooc_matrix[a, b] += 1
                cooc_matrix[b, a] += 1
    scores = cooc_matrix.sum(axis=1)
    total = len(window)
    if total > 0:
        scores /= total
    lo, hi = scores.min(), scores.max()
    if hi > lo:
        scores = (scores - lo) / (hi - lo)
    return scores


def _rf_scores(draws: List[Draw]) -> np.ndarray:
    builder = FeatureBuilder()
    X, y = builder.build_dataset(draws)
    x_infer = builder.build_inference(draws)

    rf = MultiOutputClassifier(
        RandomForestClassifier(
            n_estimators=100, max_depth=8, min_samples_leaf=5,
            random_state=42, n_jobs=-1,
        ),
        n_jobs=1,
    )
    rf.fit(X, y)
    probas_list = rf.predict_proba(x_infer)

    probas = np.empty(25, dtype=np.float32)
    for j, p in enumerate(probas_list):
        if p.shape[1] == 2:
            probas[j] = p[0, 1]
        else:
            probas[j] = float(p[0, 0]) if p.shape[1] == 1 else 0.5

    lo, hi = probas.min(), probas.max()
    if hi > lo:
        probas = (probas - lo) / (hi - lo)
    else:
        probas[:] = 0.5
    return probas


def gerar_score_ensemble(
    draws: List[Draw],
    target_date_iso: Optional[str] = None,
) -> np.ndarray:
    if target_date_iso is None:
        target_date_iso = date.today().isoformat()

    scores = np.zeros(25, dtype=np.float32)

    logger.info("Calculando RF scores...")
    rf_s = _rf_scores(draws)
    logger.info("Calculando scores de frequência...")
    freq_s = _frequencia_scores(draws, ultimos_k=50)
    logger.info("Calculando scores de co-ocorrência...")
    cooc_s = _coocorrencia_scores(draws, ultimos_k=50)
    logger.info("Calculando similaridade lua+clima...")
    similar_results = find_similar(draws, target_date_iso=target_date_iso, top_n=10)
    sim_s = compute_similarity_weighted_freq(similar_results) if similar_results else np.ones(25, dtype=np.float32) * 0.5
    logger.info("Calculando padrões21...")
    pad_s = calcular_score_padroes21(draws)

    scores += ENSEMBLE_WEIGHTS["rf"] * rf_s
    scores += ENSEMBLE_WEIGHTS["frequencia"] * freq_s
    scores += ENSEMBLE_WEIGHTS["coocorrencia"] * cooc_s
    scores += ENSEMBLE_WEIGHTS["similaridade"] * sim_s
    scores += ENSEMBLE_WEIGHTS["padroes21"] * pad_s

    lo, hi = scores.min(), scores.max()
    if hi > lo:
        scores = (scores - lo) / (hi - lo)

    return scores


def avaliar_jogo_historico(jogo: List[int], draws: List[Draw]) -> Dict[str, Any]:
    jogo_set = set(jogo)
    hits_per_draw = []
    for d in draws:
        hits = len(jogo_set & set(d.dezenas))
        hits_per_draw.append(hits)

    arr = np.array(hits_per_draw, dtype=np.int32)
    return {
        "jogo": sorted(jogo),
        "soma": sum(jogo),
        "media_acertos": round(float(arr.mean()), 2),
        "mediana_acertos": int(np.median(arr)),
        "max_acertos": int(arr.max()),
        "distribuicao": {str(h): int((arr >= h).sum()) for h in [11, 12, 13, 14, 15]},
        "prob_acertos_11": round(float((arr >= 11).sum()) / len(arr) * 100, 2),
        "prob_acertos_15": round(float((arr == 15).sum()) / len(arr) * 100, 2),
    }


def gerar_melhor_jogo(
    draws: List[Draw],
    target_concurso: int,
    target_date_iso: Optional[str] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    if target_date_iso is None:
        target_date_iso = date.today().isoformat()

    logger.info("Gerando score ensemble...")
    scores = gerar_score_ensemble(draws, target_date_iso)

    ultimo_concurso = draws[-1].dezenas if draws else []

    logger.info("Otimizando com Simulated Annealing (seed=%d)...", seed)
    import random as rnd
    rng = rnd.Random(seed)
    jogo_otimizado = sa_with_restarts(
        scores,
        last_draw=ultimo_concurso,
        n_restarts=8,
        iterations_per_restart=10000,
        rng=rng,
    )

    logger.info("Avaliando jogo contra histórico...")
    avaliacao = avaliar_jogo_historico(jogo_otimizado, draws)

    logger.info("Buscando similares lua+clima...")
    similar_results = find_similar(draws, target_date_iso=target_date_iso, top_n=10)

    logger.info("Obtendo dados de lua e clima do dia alvo...")
    moon = get_target_moon(target_date_iso)
    climate = get_target_climate(target_date_iso)

    score_por_sinal = {
        "rf": round(float(_rf_scores(draws).sum() / 25), 4),
        "frequencia": round(float(_frequencia_scores(draws).sum() / 25), 4),
        "coocorrencia": round(float(_coocorrencia_scores(draws).sum() / 25), 4),
        "similaridade": 0.0,
        "padroes21": round(float(calcular_score_padroes21(draws).sum() / 25), 4),
    }
    if similar_results:
        sim_s = compute_similarity_weighted_freq(similar_results)
        score_por_sinal["similaridade"] = round(float(sim_s.sum() / 25), 4)

    jogo_set = set(jogo_otimizado)
    filter_s = filter_score(jogo_set, ultimo_concurso)

    result = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "target_concurso": target_concurso,
            "target_data": target_date_iso,
            "total_draws": len(draws),
            "ultimo_concurso": draws[-1].concurso if draws else None,
        },
        "jogo": sorted(jogo_otimizado),
        "estatisticas": {
            "soma": int(sum(jogo_otimizado)),
            "pares": int(sum(1 for n in jogo_otimizado if n % 2 == 0)),
            "impares": int(sum(1 for n in jogo_otimizado if n % 2 == 1)),
            "moldura": int(sum(1 for n in jogo_otimizado if n in {1,2,3,4,5,6,10,11,15,16,20,21,22,23,24,25})),
            "primos": int(sum(1 for n in jogo_otimizado if n in {2,3,5,7,11,13,17,19,23})),
            "fibonacci": int(sum(1 for n in jogo_otimizado if n in {1,2,3,5,8,13,21})),
            "consecutivos": int(sum(1 for i in range(len(jogo_otimizado)-1) if jogo_otimizado[i+1] == jogo_otimizado[i] + 1)),
            "filter_score": round(float(filter_s), 3),
        },
        "avaliacao_historica": avaliacao,
        "pesos_ensemble": ENSEMBLE_WEIGHTS.copy(),
        "score_por_sinal": score_por_sinal,
        "lua_hoje": {
            "phase": round(float(moon[0]), 4),
            "illumination": round(float(moon[3]), 4),
            "is_new": bool(moon[5]),
            "is_full": bool(moon[6]),
        },
        "clima_hoje": {
            k: round(float(v), 4)
            for k, v in zip(
                ["temp_sorteio", "precip_sorteio", "wcode_sorteio"],
                [climate[3], climate[5], climate[6]],
            )
        },
        "top_similares": [
            {
                "rank": r["rank"],
                "concurso": r["concurso"],
                "data": r["data"],
                "similaridade": r["similaridade"],
            }
            for r in (similar_results or [])[:5]
        ],
        "explicacao": (
            f"Jogo otimizado por ensemble de 5 sinais: "
            f"RandomForest ({ENSEMBLE_WEIGHTS['rf']*100}%) + "
            f"Frequência ({ENSEMBLE_WEIGHTS['frequencia']*100}%) + "
            f"Co-ocorrência ({ENSEMBLE_WEIGHTS['coocorrencia']*100}%) + "
            f"Similaridade Lua+Clima ({ENSEMBLE_WEIGHTS['similaridade']*100}%) + "
            f"Padrões21 ({ENSEMBLE_WEIGHTS['padroes21']*100}%). "
            f"Otimizado via Simulated Annealing com filtros estatísticos."
        ),
    }

    return result


MOLDURA_SET = {1,2,3,4,5,6,10,11,15,16,20,21,22,23,24,25}
PRIMOS_SET = {2,3,5,7,11,13,17,19,23}
FIB_SET = {1,2,3,5,8,13,21}


def _score_filters(numeros: List[int]) -> int:
    s = sum(numeros)
    pares = sum(1 for n in numeros if n % 2 == 0)
    mold = sum(1 for n in numeros if n in MOLDURA_SET)
    prim = sum(1 for n in numeros if n in PRIMOS_SET)
    fib = sum(1 for n in numeros if n in FIB_SET)
    consec = sum(1 for i in range(len(numeros) - 1) if numeros[i + 1] == numeros[i] + 1)
    return sum([171 <= s <= 220, 7 <= pares <= 8, 9 <= mold <= 10, 4 <= prim <= 7, 3 <= fib <= 5, consec >= 2])


def otimizar_deterministico(scores: np.ndarray) -> List[int]:
    ranking = np.argsort(scores)[::-1]
    current = sorted(int(i + 1) for i in ranking[:15])
    outside = sorted(int(i + 1) for i in ranking[15:])
    best_ok = _score_filters(current)
    improved = True
    while improved:
        improved = False
        for i, dentro in enumerate(current):
            for j, fora in enumerate(outside):
                candidate = current[:i] + current[i + 1:] + [fora]
                candidate.sort()
                ok = _score_filters(candidate)
                if ok > best_ok or (ok == best_ok and scores[fora - 1] > scores[dentro - 1]):
                    current = candidate
                    outside = sorted([dentro] + [n for n in outside if n != fora])
                    best_ok = ok
                    improved = True
                    break
            if improved:
                break
    return current


def salvar_resultado(resultado: Dict[str, Any], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return path