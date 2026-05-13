"""Statistical approach for 11-numbers strategy.

Combines frequency analysis, delay (atraso), trend and co-occurrence patterns.
"""

from __future__ import annotations

from typing import List

import numpy as np

from lotofacil.infra.config import TOTAL_NUMBERS
from lotofacil.dominio.entidades import Draw
from lotofacil.infra.atributos.base import freq_k, atraso
from lotofacil.infra.atributos.advanced import coocorrencia_score, trend_score


class StatisticalApproach:
    """Predicts based on statistical patterns in historical draws."""

    def __init__(self):
        self._probas: np.ndarray | None = None

    def fit(self, draws: List[Draw]) -> None:
        n = len(draws)
        freq_scores = np.zeros(TOTAL_NUMBERS, dtype=np.float64)
        atraso_scores = np.zeros(TOTAL_NUMBERS, dtype=np.float64)
        trend_scores_arr = np.zeros(TOTAL_NUMBERS, dtype=np.float64)
        cooc_scores = np.zeros(TOTAL_NUMBERS, dtype=np.float64)

        for w, weight in [(10, 0.5), (30, 0.3), (100, 0.2)]:
            freq = freq_k(draws, n, k=w)
            for num in range(1, TOTAL_NUMBERS + 1):
                freq_scores[num - 1] += freq[num] * weight

        at = atraso(draws, n, max_atraso=20)
        for num in range(1, TOTAL_NUMBERS + 1):
            atraso_scores[num - 1] = 1.0 - (at[num] / 20.0)

        trend = trend_score(draws, n)
        for num in range(1, TOTAL_NUMBERS + 1):
            trend_scores_arr[num - 1] = max(0, trend[num] + 0.5)

        cooc = coocorrencia_score(draws, n, k=30)
        max_cooc = max(cooc.values()) if cooc else 1.0
        for num in range(1, TOTAL_NUMBERS + 1):
            cooc_scores[num - 1] = cooc[num] / max_cooc if max_cooc > 0 else 0

        combined = (
            0.40 * freq_scores
            + 0.25 * atraso_scores
            + 0.20 * trend_scores_arr
            + 0.15 * cooc_scores
        )

        if combined.sum() > 0:
            combined /= combined.sum()

        self._probas = combined

    def predict_proba(self) -> np.ndarray:
        if self._probas is None:
            raise RuntimeError("Approach not fitted. Call fit() first.")
        return self._probas

    @property
    def name(self) -> str:
        return "statistical"
