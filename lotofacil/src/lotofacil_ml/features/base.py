"""Base feature functions for Lotofácil ML pipeline.

All functions accept `draws: List[Draw]` and `idx: int`.
They use ONLY draws[:idx] — never draws[idx] or later (no leakage).
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from lotofacil_ml.data.loader import Draw

_NUMBERS = list(range(1, 26))
_MOLDURA = {1, 2, 3, 4, 5, 21, 22, 23, 24, 25}


def freq_k(draws: List[Draw], idx: int, k: int) -> Dict[int, float]:
    """Frequency of each number 1-25 in the k draws before idx."""
    window = draws[max(0, idx - k):idx]
    counts = {n: 0 for n in _NUMBERS}
    for d in window:
        for n in d.dezenas:
            counts[n] += 1
    total = len(window)
    if total == 0:
        return {n: 0.0 for n in _NUMBERS}
    return {n: counts[n] / total for n in _NUMBERS}


def atraso(draws: List[Draw], idx: int, max_atraso: int = 20) -> Dict[int, int]:
    """Draws since last appearance of each number (capped at max_atraso)."""
    result = {n: max_atraso for n in _NUMBERS}
    for n in _NUMBERS:
        for dist in range(1, min(idx, max_atraso) + 1):
            cidx = idx - dist
            if cidx < 0:
                break
            if n in draws[cidx].dezenas:
                result[n] = dist - 1  # 0 = appeared in draw immediately before idx
                break
    return result


def stats_soma(draws: List[Draw], idx: int, k: int) -> Dict[str, float]:
    """Mean, median, std of the sum of 15 dezenas in window k before idx."""
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
    """(mean_pares, mean_impares) in window k before idx."""
    window = draws[max(0, idx - k):idx]
    if not window:
        return 0.0, 0.0
    pares = [sum(1 for n in d.dezenas if n % 2 == 0) for d in window]
    mean_p = sum(pares) / len(pares)
    return mean_p, 15.0 - mean_p


def repeticao_media(draws: List[Draw], idx: int, k: int) -> float:
    """Average number of repeated dezenas between consecutive draws in window."""
    start = max(1, idx - k)
    reps = []
    for i in range(start, idx):
        reps.append(len(set(draws[i - 1].dezenas) & set(draws[i].dezenas)))
    return sum(reps) / len(reps) if reps else 0.0


def consecutivos_media(draws: List[Draw], idx: int, k: int) -> float:
    """Average count of consecutive-number pairs in window k before idx."""
    window = draws[max(0, idx - k):idx]
    if not window:
        return 0.0

    def _count(dez: List[int]) -> int:
        s = sorted(dez)
        return sum(1 for i in range(len(s) - 1) if s[i + 1] == s[i] + 1)

    return sum(_count(d.dezenas) for d in window) / len(window)


def std_frequencias(freq_k20: Dict[int, float]) -> float:
    """Std dev of frequency values (dispersion across numbers)."""
    vals = list(freq_k20.values())
    if not vals:
        return 0.0
    mean = sum(vals) / len(vals)
    return math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))


def ratio_moldura_miolo(draws: List[Draw], idx: int) -> float:
    """Ratio moldura/miolo for the draw immediately before idx."""
    if idx == 0:
        return 0.0
    dez = draws[idx - 1].dezenas
    moldura = sum(1 for n in dez if n in _MOLDURA)
    miolo = 15 - moldura
    return moldura / miolo if miolo > 0 else float(moldura)
