"""Abstract base interface for all lab models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class BaseLabModel(ABC):
    """Minimal interface that walk-forward and runner expect."""

    @abstractmethod
    def fit(self, draws: list) -> None:
        """Train on a list of Draw objects."""

    @abstractmethod
    def predict(self, draws: list) -> List[int]:
        """Return a sorted list of 15 (or target_numbers) dezenas in [1,25]."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for reporting."""
