"""Frequency-based prediction model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import numpy as np

from core.config import FREQ_WINDOWS, RANDOM_SEED
from core.models import Draw
from models.base import BaseModel


class FrequencyModel(BaseModel):
    """Predicts based on weighted frequency analysis across multiple windows."""

    def __init__(self, weights: dict | None = None, windows: list | None = None):
        self.weights = weights or {"freq_30": 0.5, "freq_100": 0.3, "freq_all": 0.2}
        self.windows = windows or FREQ_WINDOWS
        self._probas: np.ndarray | None = None
        self._fitted = False

    def fit(self, draws: List[Draw]) -> None:
        n = len(draws)
        probas = np.zeros(25, dtype=np.float64)

        for w in self.windows:
            window = draws[max(0, n - w):n]
            counts = np.zeros(25, dtype=np.float64)
            for d in window:
                for num in d.dezenas:
                    counts[num - 1] += 1
            freq = counts / len(window) if window else counts
            probas += freq

        if probas.sum() > 0:
            probas /= probas.sum()

        self._probas = probas
        self._fitted = True

    def predict_proba(self) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        return self._probas

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "weights": self.weights,
            "windows": self.windows,
            "probas": self._probas.tolist() if self._probas is not None else None,
        }
        with open(path, "w") as f:
            json.dump(data, f)

    def load(self, path: Path) -> None:
        with open(path) as f:
            data = json.load(f)
        self.weights = data["weights"]
        self.windows = data["windows"]
        self._probas = np.array(data["probas"]) if data["probas"] else None
        self._fitted = self._probas is not None

    @property
    def name(self) -> str:
        return "frequency"
