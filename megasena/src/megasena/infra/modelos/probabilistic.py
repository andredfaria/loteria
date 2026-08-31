from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import numpy as np

from megasena.dominio.entidades import Sorteio as Draw
from megasena.infra.atributos.base import atraso, freq_k
from megasena.infra.modelos.base_model import BaseModel

logger = logging.getLogger(__name__)

TOTAL_NUMEROS = 60
NUMEROS = list(range(1, TOTAL_NUMEROS + 1))


class ProbabilisticModel(BaseModel):
    def __init__(self, alpha: float = 0.6, beta: float = 0.4, k: int = 50):
        self._alpha = alpha
        self._beta = beta
        self._k = k
        self._scores: np.ndarray = np.ones(TOTAL_NUMEROS, dtype=np.float32) / TOTAL_NUMEROS
        self._fitted = False

    @property
    def name(self) -> str:
        return "probabilistic"

    def fit(self, draws: List[Draw]) -> None:
        idx = len(draws)
        fk = freq_k(draws, idx, self._k)
        at = atraso(draws, idx, max_atraso=50)

        freq_arr = np.array([fk[n] for n in NUMEROS], dtype=np.float32)
        delay_arr = np.array([1.0 / (1.0 + at[n]) for n in NUMEROS], dtype=np.float32)

        def _norm(arr: np.ndarray) -> np.ndarray:
            lo, hi = arr.min(), arr.max()
            return (arr - lo) / (hi - lo) if hi > lo else np.ones_like(arr) * 0.5

        self._scores = self._alpha * _norm(freq_arr) + self._beta * _norm(delay_arr)
        self._fitted = True

    def score(self) -> np.ndarray:
        return self._scores.copy()

    def save(self, path: Path) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        data = {"scores": self._scores.tolist(), "alpha": self._alpha, "beta": self._beta, "k": self._k}
        (path / "probabilistic_model.json").write_text(json.dumps(data))

    def load(self, path: Path) -> None:
        data = json.loads((Path(path) / "probabilistic_model.json").read_text())
        self._scores = np.array(data["scores"], dtype=np.float32)
        self._alpha = data["alpha"]
        self._beta = data["beta"]
        self._k = data["k"]
        self._fitted = True