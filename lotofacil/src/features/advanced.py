"""Advanced feature functions for Lotofácil ML."""

from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List

from core.models import Draw
from features.base import freq_k, atraso as calc_atraso

_NUMBERS = list(range(1, 26))
_FAIXAS = {1: range(1, 6), 2: range(6, 11), 3: range(11, 16), 4: range(16, 21), 5: range(21, 26)}


def coocorrencia_score(draws: List[Draw], idx: int, k: int = 30) -> Dict[int, float]:
    """For each number N, count co-occurrences with other numbers in window k."""
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
    """freq_k5 - freq_k20: positive = heating up, negative = cooling down."""
    f5 = freq_k(draws, idx, k=5)
    f20 = freq_k(draws, idx, k=20)
    return {n: f5[n] - f20[n] for n in _NUMBERS}


def volatilidade_score(draws: List[Draw], idx: int, outer_k: int = 50, inner_k: int = 10) -> Dict[int, float]:
    """Std dev of frequency in non-overlapping windows."""
    window = draws[max(0, idx - outer_k):idx]
    n_windows = max(1, len(window) // inner_k)
    scores = {n: [] for n in _NUMBERS}

    for w in range(n_windows):
        sub = window[w * inner_k:(w + 1) * inner_k]
        if not sub:
            continue
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
    """Faixa (1-5) with most numbers in the draw immediately before idx."""
    if idx == 0:
        return 1
    dez = set(draws[idx - 1].dezenas)
    counts = {f: sum(1 for n in dez if n in rng) for f, rng in _FAIXAS.items()}
    return max(counts, key=counts.get)


def par_quente_score(draws: List[Draw], idx: int, k: int = 30) -> float:
    """Count of top-10 frequent numbers that also have atraso <= 3."""
    fk = freq_k(draws, idx, k=k)
    top10 = sorted(fk, key=fk.get, reverse=True)[:10]
    at = calc_atraso(draws, idx, max_atraso=20)
    return float(sum(1 for n in top10 if at[n] <= 3))
