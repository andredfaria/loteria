from __future__ import annotations

import math
from typing import Dict, List, Tuple

from quina.dominio.entidades import Sorteio as Draw

_NUMBERS = list(range(1, 81))


def freq_k(draws: List[Draw], idx: int, k: int) -> Dict[int, float]:
    window = draws[max(0, idx - k):idx]
    counts = {n: 0 for n in _NUMBERS}
    for d in window:
        for n in d.dezenas:
            counts[n] += 1
    total = len(window)
    if total == 0:
        return {n: 0.0 for n in _NUMBERS}
    return {n: counts[n] / total for n in _NUMBERS}


def atraso(draws: List[Draw], idx: int, max_atraso: int = 50) -> Dict[int, int]:
    result = {n: max_atraso for n in _NUMBERS}
    for n in _NUMBERS:
        for dist in range(1, min(idx, max_atraso) + 1):
            cidx = idx - dist
            if cidx < 0:
                break
            if n in draws[cidx].dezenas:
                result[n] = dist - 1
                break
    return result


def stats_soma(draws: List[Draw], idx: int, k: int) -> Dict[str, float]:
    window = draws[max(0, idx - k):idx]
    somas = [sum(d.dezenas) for d in window]
    if not somas:
        return {"mean": 0.0, "median": 0.0, "std": 0.0}
    n = len(somas)
    mean = sum(somas) / n
    sorted_s = sorted(somas)
    median = float(sorted_s[n // 2]) if n % 2 else (sorted_s[n // 2 - 1] + sorted_s[n // 2]) / 2.0
    std = math.sqrt(sum((s - mean) ** 2 for s in somas) / n)
    return {"mean": mean, "median": median, "std": std}


def stats_pares(draws: List[Draw], idx: int, k: int) -> Tuple[float, float]:
    window = draws[max(0, idx - k):idx]
    if not window:
        return 0.0, 0.0
    pares = [sum(1 for n in d.dezenas if n % 2 == 0) for d in window]
    mean_p = sum(pares) / len(pares)
    return mean_p, 5.0 - mean_p


def repeticao_media(draws: List[Draw], idx: int, k: int) -> float:
    start = max(1, idx - k)
    reps = []
    for i in range(start, idx):
        reps.append(len(set(draws[i - 1].dezenas) & set(draws[i].dezenas)))
    return sum(reps) / len(reps) if reps else 0.0


def consecutivos_media(draws: List[Draw], idx: int, k: int) -> float:
    window = draws[max(0, idx - k):idx]
    if not window:
        return 0.0

    def _count(dez: List[int]) -> int:
        s = sorted(dez)
        return sum(1 for i in range(len(s) - 1) if s[i + 1] == s[i] + 1)

    return sum(_count(d.dezenas) for d in window) / len(window)


def std_frequencias(freq_k30: Dict[int, float]) -> float:
    vals = list(freq_k30.values())
    if not vals:
        return 0.0
    mean = sum(vals) / len(vals)
    return math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))