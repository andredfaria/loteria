"""Abstract base class for all Lotofácil prediction models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

import numpy as np

from lotofacil_ml.data.loader import Draw


class BaseModel(ABC):

    @abstractmethod
    def fit(self, draws: List[Draw]) -> None:
        """Train the model on historical draws (no X/y arrays needed)."""

    @abstractmethod
    def predict_proba(self) -> np.ndarray:
        """Return probability array of shape (25,) — index 0 = number 1."""

    def select_top_15(self, probas: np.ndarray | None = None) -> List[int]:
        """Return 15 numbers (1-indexed) with highest probability."""
        p = probas if probas is not None else self.predict_proba()
        indices = np.argsort(p)[::-1][:15]
        return sorted(int(i + 1) for i in indices)

    @abstractmethod
    def save(self, path: Path) -> None:
        """Persist model artefacts to disk."""

    @abstractmethod
    def load(self, path: Path) -> None:
        """Load model artefacts from disk."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Model identifier string."""
