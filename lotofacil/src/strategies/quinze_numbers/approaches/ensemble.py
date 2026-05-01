"""Ensemble approach: combines Neural + Frequency predictions.

Weights: Neural (60%) + Frequency (40%)
The neural model captures temporal patterns, frequency captures statistical trends.
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np

from core.models import Draw

logger = logging.getLogger(__name__)


class EnsembleApproach:
    """Ensemble of Neural LSTM + Frequency model."""

    def __init__(self, neural_weight: float = 0.6, freq_weight: float = 0.4):
        self.neural_weight = neural_weight
        self.freq_weight = freq_weight
        self._neural = None
        self._freq_probas = None
        self._probas: np.ndarray | None = None
        self._fitted = False
        self._last_draws = None

    def _get_neural(self):
        if self._neural is None:
            from strategies.quinze_numbers.approaches.neural import NeuralApproach
            self._neural = NeuralApproach()
        return self._neural

    def _compute_freq_probas(self, draws: List[Draw]) -> np.ndarray:
        """Compute frequency probabilities from draws."""
        n = len(draws)
        freq_probas = np.zeros(25, dtype=np.float64)
        for w in [10, 30, 100]:
            window = draws[max(0, n - w):n]
            counts = np.zeros(25, dtype=np.float64)
            for d in window:
                for num in d.dezenas:
                    counts[num - 1] += 1
            freq = counts / len(window) if window else counts
            freq_probas += freq
        if freq_probas.sum() > 0:
            freq_probas /= freq_probas.sum()
        return freq_probas

    def fit(self, draws: List[Draw]) -> None:
        """Train neural model and compute frequency probabilities."""
        neural = self._get_neural()
        neural.fit(draws)
        neural_probas = neural.predict_proba()

        self._freq_probas = self._compute_freq_probas(draws)
        self._last_draws = draws

        self._probas = (
            self.neural_weight * neural_probas +
            self.freq_weight * self._freq_probas
        )
        if self._probas.sum() > 0:
            self._probas /= self._probas.sum()

        self._fitted = True
        logger.info("Ensemble fitted: neural_w=%.2f freq_w=%.2f",
                     self.neural_weight, self.freq_weight)

    def predict_proba(self, draws: List[Draw] | None = None) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Approach not fitted. Call fit() first.")

        if draws is not None and self._last_draws != draws:
            neural = self._get_neural()
            neural_probas = neural.predict_proba(draws)
            freq_probas = self._compute_freq_probas(draws)
            probas = (
                self.neural_weight * neural_probas +
                self.freq_weight * freq_probas
            )
            if probas.sum() > 0:
                probas /= probas.sum()
            return probas

        return self._probas

    def predict_with_filters(self, draws: List[Draw]) -> List[int]:
        """Predict 15 numbers combining ensemble probabilities with SA optimization."""
        if not self._fitted:
            raise RuntimeError("Approach not fitted. Call fit() first.")

        from strategies.quinze_numbers.post_processor import optimize

        probas = self.predict_proba(draws)
        last_draw = draws[-1].dezenas if draws else None
        optimized = optimize(probas, last_draw=last_draw)

        return optimized

    def save(self, path=None) -> None:
        neural = self._get_neural()
        if neural.is_fitted:
            neural.save()

    def load(self, path=None) -> None:
        neural = self._get_neural()
        neural.load()
        self._fitted = True

    @property
    def name(self) -> str:
        return "ensemble"

    @property
    def is_fitted(self) -> bool:
        return self._fitted
