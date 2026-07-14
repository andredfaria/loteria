from __future__ import annotations

import json
from pathlib import Path
from typing import List

import numpy as np

from quina.dominio.entidades import Sorteio as Draw
from quina.infra.config import TOTAL_NUMEROS
from quina.infra.modelos.base_model import BaseModel


_DEFAULT_WINDOWS = {5: 0.30, 15: 0.25, 30: 0.20, 50: 0.15, 100: 0.10}


class FrequencyEnsembleModel(BaseModel):
    def __init__(self, windows: dict[int, float] | None = None):
        self._windows = windows or _DEFAULT_WINDOWS
        self._weights: dict[int, dict[int, float]] | None = None
        self._total_draws: int = 0

    @property
    def name(self) -> str:
        return "frequencia_ensemble"

    def fit(self, draws: List[Draw]) -> None:
        self._total_draws = len(draws)
        self._weights = {}
        for w in self._windows:
            window = draws[-w:] if w < len(draws) else draws
            counts = {n: 0 for n in range(1, TOTAL_NUMEROS + 1)}
            for d in window:
                for n in d.dezenas:
                    counts[n] += 1
            self._weights[w] = {n: counts[n] / len(window) for n in range(1, TOTAL_NUMEROS + 1)}

    def predict_proba(self) -> np.ndarray:
        if self._weights is None:
            return np.full(TOTAL_NUMEROS, 1.0 / TOTAL_NUMEROS, dtype=np.float32)
        probas = np.zeros(TOTAL_NUMEROS, dtype=np.float32)
        for w, weight_dict in self._weights.items():
            wgt = self._windows[w]
            for n in range(1, TOTAL_NUMEROS + 1):
                probas[n - 1] += wgt * weight_dict[n]
        return probas

    def save(self, path: Path) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        data = {
            "windows": self._windows,
            "weights": {str(w): v for w, v in self._weights.items()},
            "total_draws": self._total_draws,
        }
        with open(path / "frequency_ensemble.json", "w") as f:
            json.dump(data, f)

    def load(self, path: Path) -> None:
        path = Path(path)
        with open(path / "frequency_ensemble.json") as f:
            data = json.load(f)
        self._windows = {int(k): v for k, v in data["windows"].items()}
        self._weights = {int(k): {int(n): p for n, p in v.items()} for k, v in data["weights"].items()}
        self._total_draws = data["total_draws"]