from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

import numpy as np

from megasena.dominio.entidades import Sorteio as Draw

TOTAL = 60
BAIXO_MAX = 30
NUMEROS_POR_SORTEIO = 6
NUMEROS = list(range(1, TOTAL + 1))


def _check_filters(numeros: List[int], ultimo_sorteio: List[int] | None = None) -> Dict[str, bool]:
    pares = sum(1 for n in numeros if n % 2 == 0)
    baixos = sum(1 for n in numeros if n <= BAIXO_MAX)
    soma = sum(numeros)

    pares_ok = 2 <= pares <= 4
    baixos_ok = 1 <= baixos <= 5
    soma_ok = 120 <= soma <= 240
    consec_ok = any(numeros[i + 1] == numeros[i] + 1 for i in range(len(numeros) - 1))
    repet_ok = True
    if ultimo_sorteio is not None:
        rep = len(set(numeros) & set(ultimo_sorteio))
        repet_ok = rep <= 2

    return {
        "pares": pares_ok,
        "baixos": baixos_ok,
        "soma": soma_ok,
        "consecutivos": consec_ok,
        "repeticoes": repet_ok,
    }


def _filter_score(numeros: List[int], ultimo_sorteio: List[int] | None = None) -> float:
    checks = _check_filters(numeros, ultimo_sorteio)
    return sum(1 for v in checks.values() if v) / len(checks)


def _proba_score(numeros: List[int], probas: np.ndarray) -> float:
    return float(np.mean([probas[n - 1] for n in numeros]))


def _generate_neighbor(current: List[int], pool: List[int]) -> List[int]:
    candidate = list(current)
    idx = random.randrange(len(candidate))
    remaining = [n for n in pool if n not in candidate]
    if remaining:
        candidate[idx] = random.choice(remaining)
    return sorted(candidate)


def simulated_annealing(
    probas: np.ndarray,
    pool: List[int],
    ultimo_sorteio: List[int] | None = None,
    n_restarts: int = 5,
    n_iterations: int = 3000,
    initial_temp: float = 5.0,
    cooling_rate: float = 0.997,
) -> Tuple[List[int], float]:
    best_overall = None
    best_score = -1.0

    for _ in range(n_restarts):
        current = sorted(random.sample(pool, NUMEROS_POR_SORTEIO))
        current_score = _proba_score(current, probas) * 0.7 + _filter_score(current, ultimo_sorteio) * 0.3
        best_local = list(current)
        best_local_score = current_score
        temp = initial_temp

        for i in range(n_iterations):
            neighbor = _generate_neighbor(current, pool)
            neighbor_score = _proba_score(neighbor, probas) * 0.7 + _filter_score(neighbor, ultimo_sorteio) * 0.3
            delta = neighbor_score - current_score

            if delta > 0 or random.random() < math.exp(delta / max(temp, 0.001)):
                current = neighbor
                current_score = neighbor_score
                if current_score > best_local_score:
                    best_local = list(current)
                    best_local_score = current_score

            temp *= cooling_rate

        if best_local_score > best_score:
            best_overall = best_local
            best_score = best_local_score

    return best_overall, best_score


def gerar_jogo(
    ensemble,
    draws: List[Draw],
    ultimo_sorteio: List[int] | None = None,
    top_n_pool: int = 12,
) -> dict:
    """Gera um jogo otimizado via simulated annealing.

    O campo "score" do retorno é o score de aderência aos critérios de
    otimização (filtros + ranking do ensemble), não uma chance de acerto.
    O campo "scores" traz o score de ordenação (0-100) de cada número
    escolhido — também não é probabilidade. Ver `BaseModel.score()`.
    """
    scores = ensemble.score()
    scores_dict = ensemble.score_dict()

    sorted_nums = sorted(NUMEROS, key=lambda n: scores_dict[n], reverse=True)
    pool = sorted_nums[:top_n_pool]

    numeros_otimizados, score = simulated_annealing(
        probas=scores,
        pool=pool,
        ultimo_sorteio=ultimo_sorteio,
    )

    checks = _check_filters(numeros_otimizados, ultimo_sorteio)
    pares = sum(1 for n in numeros_otimizados if n % 2 == 0)
    baixos = sum(1 for n in numeros_otimizados if n <= BAIXO_MAX)

    razoes = {}
    for n in numeros_otimizados:
        partes = []
        num_score = scores_dict[n]
        rank = sorted_nums.index(n) + 1
        partes.append(f"score: {num_score:.4f} (#{rank})")
        if n % 2 == 0:
            partes.append("par")
        else:
            partes.append("ímpar")
        if n <= BAIXO_MAX:
            partes.append("baixo")
        else:
            partes.append("alto")
        razoes[n] = " | ".join(partes)

    return {
        "numeros": sorted(numeros_otimizados),
        "razoes": razoes,
        "score": round(score * 100, 2),
        "filtros": checks,
        "metricas_jogo": {
            "pares": pares,
            "impares": NUMEROS_POR_SORTEIO - pares,
            "baixos": baixos,
            "altos": NUMEROS_POR_SORTEIO - baixos,
            "soma": sum(numeros_otimizados),
        },
        "scores": {n: round(scores_dict[n] * 100, 2) for n in sorted(numeros_otimizados)},
    }