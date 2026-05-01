"""Predictor for the 11-numbers strategy.

Orchestrates statistical, ML and neural approaches to predict 11 numbers.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List

import numpy as np

from core.models import Draw, Prediction
from core.config import TOTAL_NUMBERS
from strategies.base import BaseStrategy
from strategies.eleven_numbers.config import (
    TARGET_NUMBERS,
    APPROACH_WEIGHTS,
    STRATEGY_NAME,
)
from strategies.eleven_numbers.approaches.statistical import StatisticalApproach
from strategies.eleven_numbers.approaches.ml import MLApproach
from strategies.eleven_numbers.approaches.neural import NeuralApproach

logger = logging.getLogger(__name__)


class ElevenNumbersStrategy(BaseStrategy):
    """Strategy that predicts 11 numbers for the next Lotofácil draw."""

    def __init__(self):
        self._statistical = StatisticalApproach()
        self._ml = MLApproach()
        self._neural = NeuralApproach()

    @property
    def name(self) -> str:
        return STRATEGY_NAME

    @property
    def target_count(self) -> int:
        return TARGET_NUMBERS

    @property
    def approaches(self) -> List[str]:
        return ["statistical", "ml", "neural", "all"]

    def predict(self, draws: List[Draw], approach: str = "all") -> Prediction:
        """Generate a prediction for the next draw."""
        if approach == "all":
            probas = self._ensemble_predict(draws)
            approach_used = "ensemble"
        elif approach == "statistical":
            self._statistical.fit(draws)
            probas = self._statistical.predict_proba()
            approach_used = "statistical"
        elif approach == "ml":
            if not self._ml.is_fitted:
                self._ml.fit(draws)
            probas = self._ml.predict_proba(draws)
            approach_used = "ml"
        elif approach == "neural":
            if not self._neural.is_fitted:
                try:
                    self._neural.load()
                except Exception:
                    self._neural.fit(draws)
            probas = self._neural.predict_proba(draws)
            approach_used = "neural"
        else:
            raise ValueError(f"Unknown approach: {approach}")

        selected = self.select_numbers(probas, TARGET_NUMBERS)
        confianca = float(np.mean([probas[n - 1] for n in selected]))

        target_concurso = (draws[-1].concurso + 1) if draws else 0

        return Prediction(
            concurso_alvo=target_concurso,
            dezenas=selected,
            probabilidades=probas.tolist(),
            confianca_media=confianca,
            strategy=self.name,
            approach=approach_used,
        )

    def predict_batch(self, draws: List[Draw], approach: str = "all") -> List[Prediction]:
        """Generate predictions with different approaches for comparison."""
        predictions = []
        for app in ["statistical", "ml", "neural"]:
            try:
                pred = self.predict(draws, approach=app)
                predictions.append(pred)
            except Exception as e:
                logger.warning("Failed to predict with %s: %s", app, e)

        if predictions:
            predictions.append(self.predict(draws, approach="all"))

        return predictions

    def _ensemble_predict(self, draws: List[Draw]) -> np.ndarray:
        """Combine all approaches using weighted ensemble."""
        probas = np.zeros(TOTAL_NUMBERS, dtype=np.float64)
        total_weight = 0.0

        try:
            self._statistical.fit(draws)
            p = self._statistical.predict_proba()
            w = APPROACH_WEIGHTS.get("statistical", 0.3)
            probas += w * p
            total_weight += w
        except Exception as e:
            logger.warning("Statistical approach failed: %s", e)

        try:
            self._ml.fit(draws)
            p = self._ml.predict_proba(draws)
            w = APPROACH_WEIGHTS.get("ml", 0.45)
            probas += w * p
            total_weight += w
        except Exception as e:
            logger.warning("ML approach failed: %s", e)

        try:
            self._neural.fit(draws)
            p = self._neural.predict_proba()
            w = APPROACH_WEIGHTS.get("neural", 0.25)
            probas += w * p
            total_weight += w
        except Exception as e:
            logger.warning("Neural approach failed: %s", e)

        if total_weight > 0:
            probas /= total_weight
        if probas.sum() > 0:
            probas /= probas.sum()

        return probas
