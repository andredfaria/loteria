"""Frequency baseline: selects the top N dezenas by weighted rolling frequency."""

from __future__ import annotations

from typing import List

import numpy as np

from lotofacil.experimentos.config import TOTAL_NUMBERS
from lotofacil.experimentos.models.base import BaseLabModel
from lotofacil.experimentos.features.base import binary_matrix, sliding_frequency


class FrequencyBaseline(BaseLabModel):
    """Selects top target_numbers dezenas by weighted frequency over multiple windows."""

    def __init__(
        self,
        target_numbers: int = 15,
        windows: tuple = (5, 15, 30, 100),
        weights: tuple = (0.5, 0.25, 0.15, 0.10),
    ):
        self.target_numbers = target_numbers
        self.windows = windows
        self.weights = weights
        self._scores: np.ndarray | None = None

    def fit(self, draws: list) -> None:
        if not draws:
            self._scores = np.ones(TOTAL_NUMBERS) / TOTAL_NUMBERS
            return

        binary = binary_matrix(draws)
        scores = np.zeros(TOTAL_NUMBERS, dtype=np.float64)

        for window, weight in zip(self.windows, self.weights):
            freq = sliding_frequency(binary, window)
            scores += weight * freq[-1]  # last row = current state

        total = scores.sum()
        self._scores = (scores / total).astype(np.float32) if total > 0 else np.ones(TOTAL_NUMBERS) / TOTAL_NUMBERS

    def predict(self, draws: list) -> List[int]:
        if self._scores is None:
            self.fit(draws)
        top = np.argsort(self._scores)[::-1][:self.target_numbers]
        return sorted(int(i + 1) for i in top)

    @property
    def name(self) -> str:
        return "frequency"
