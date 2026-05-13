"""Random baseline: selects 15 distinct dezenas uniformly at random."""

from __future__ import annotations

from typing import List

import numpy as np

from lotofacil.experimentos.config import TOTAL_NUMBERS, RANDOM_SEED
from lotofacil.experimentos.models.base import BaseLabModel


class RandomBaseline(BaseLabModel):
    """Selects target_numbers dezenas uniformly at random. No learning."""

    def __init__(self, target_numbers: int = 15, seed: int = RANDOM_SEED):
        self.target_numbers = target_numbers
        self._rng = np.random.default_rng(seed)

    def fit(self, draws: list) -> None:
        pass  # stateless

    def predict(self, draws: list) -> List[int]:
        chosen = self._rng.choice(TOTAL_NUMBERS, self.target_numbers, replace=False)
        return sorted(int(c + 1) for c in chosen)

    @property
    def name(self) -> str:
        return "random"

    def predict_many(self, n: int) -> List[List[int]]:
        """Generate n independent random games."""
        return [self.predict([]) for _ in range(n)]
