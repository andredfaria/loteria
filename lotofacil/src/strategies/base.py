"""Abstract base class for prediction strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

import numpy as np

from core.models import Draw, Prediction


class BaseStrategy(ABC):
    """Base class that all prediction strategies must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name (e.g. '11-numbers', '12-numbers')."""

    @property
    @abstractmethod
    def target_count(self) -> int:
        """Number of predictions to return (e.g. 11, 12, 13, 14)."""

    @property
    @abstractmethod
    def approaches(self) -> List[str]:
        """List of available approaches for this strategy."""

    @abstractmethod
    def predict(self, draws: List[Draw], approach: str = "all") -> Prediction:
        """Generate a prediction for the next draw."""

    @abstractmethod
    def predict_batch(self, draws: List[Draw], approach: str = "all") -> List[Prediction]:
        """Generate multiple predictions."""

    def select_numbers(self, probas: np.ndarray, n: int | None = None) -> List[int]:
        """Select top n numbers from probability array."""
        n = n or self.target_count
        indices = np.argsort(probas)[::-1][:n]
        return sorted(int(i + 1) for i in indices)

    def evaluate(self, prediction: Prediction, actual: List[int]) -> int:
        """Count hits between prediction and actual result."""
        return len(set(prediction.dezenas) & set(actual))
