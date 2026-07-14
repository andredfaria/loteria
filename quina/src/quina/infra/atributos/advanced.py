from __future__ import annotations

import math
from typing import Dict, List

from quina.dominio.entidades import Sorteio as Draw
from quina.infra.atributos.base import freq_k, atraso as calc_atraso

_NUMBERS = list(range(1, 81))
_FAIXAS = {
    1: range(1, 17),
    2: range(17, 33),
    3: range(33, 49),
    4: range(49, 65),
    5: range(65, 81),
}


def coocorrencia_score(draws: List[Draw], idx: int, k: int = 50) -> Dict[int, float]:
    window = draws[max(0, idx - k):idx]
    score = {n: 0.0 for n in _NUMBERS}
    for d in window:
        dez_set = set(d.dezenas)
        co_count = len(dez_set) - 1
        for n in dez_set:
            score[n] += co_count
    total = len(window)
    if total > 0:
        score = {n: v / total for n, v in score.items()}
    return score


def trend_score(draws: List[Draw], idx: int) -> Dict[int, float]:
    f10 = freq_k(draws, idx, k=10)
    f50 = freq_k(draws, idx, k=50)
    return {n: f10[n] - f50[n] for n in _NUMBERS}


def volatilidade_score(
    draws: List[Draw], idx: int, outer_k: int = 100, inner_k: int = 20
) -> Dict[int, float]:
    window = draws[max(0, idx - outer_k):idx]
    n_windows = max(1, len(window) // inner_k)
    scores = {n: [] for n in _NUMBERS}

    for w in range(n_windows):
        sub = window[w * inner_k:(w + 1) * inner_k]
        if not sub:
            continue
        from collections import Counter
        counts = Counter()
        for d in sub:
            counts.update(d.dezenas)
        for n in _NUMBERS:
            scores[n].append(counts[n] / len(sub))

    result = {}
    for n in _NUMBERS:
        vals = scores[n]
        if len(vals) < 2:
            result[n] = 0.0
        else:
            mean = sum(vals) / len(vals)
            result[n] = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
    return result


def faixa_dominante(draws: List[Draw], idx: int) -> int:
    if idx == 0:
        return 1
    dez = set(draws[idx - 1].dezenas)
    counts = {f: sum(1 for n in dez if n in rng) for f, rng in _FAIXAS.items()}
    return max(counts, key=counts.get)


def par_quente_score(draws: List[Draw], idx: int, k: int = 50) -> float:
    fk = freq_k(draws, idx, k=k)
    top20 = sorted(fk, key=fk.get, reverse=True)[:20]
    at = calc_atraso(draws, idx, max_atraso=50)
    return float(sum(1 for n in top20 if at[n] <= 5))