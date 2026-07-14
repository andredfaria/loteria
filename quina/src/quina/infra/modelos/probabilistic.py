from __future__ import annotations

import json
from pathlib import Path
from typing import List

import numpy as np

from quina.dominio.entidades import Sorteio as Draw
from quina.infra.config import TOTAL_NUMEROS
from quina.infra.modelos.base_model import BaseModel


class ProbabilisticModel(BaseModel):
    def __init__(self, alpha: float = 0.6, beta: float = 0.4, delay_k: int = 50):
        self._alpha = alpha
        self._beta = beta
        self._delay_k = delay_k
        self._frequencias: dict[int, float] | None = None
        self._atrasos: dict[int, int] | None = None
        self._total_draws: int = 0

    @property
    def name(self) -> str:
        return "probabilistico"

    def fit(self, draws: List[Draw]) -> None:
        self._total_draws = len(draws)
        counts = {n: 0 for n in range(1, TOTAL_NUMEROS + 1)}
        ultimo_indice = {}
        for i, d in enumerate(draws):
            for n in d.dezenas:
                counts[n] += 1
                ultimo_indice[n] = i
        self._frequencias = {n: counts[n] / self._total_draws for n in range(1, TOTAL_NUMEROS + 1)}
        self._atrasos = {
            n: min(self._delay_k, self._total_draws - 1 - ultimo_indice[n]) if n in ultimo_indice else self._delay_k
            for n in range(1, TOTAL_NUMEROS + 1)
        }

    def predict_proba(self) -> np.ndarray:
        if self._frequencias is None or self._atrasos is None:
            return np.full(TOTAL_NUMEROS, 1.0 / TOTAL_NUMEROS, dtype=np.float32)
        max_freq = max(self._frequencias.values()) or 1
        result = np.zeros(TOTAL_NUMEROS, dtype=np.float32)
        for n in range(1, TOTAL_NUMEROS + 1):
            freq_norm = self._frequencias[n] / max_freq
            delay_score = 1.0 / (1.0 + self._atrasos[n])
            result[n - 1] = self._alpha * freq_norm + self._beta * delay_score
        return result

    def save(self, path: Path) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        data = {
            "frequencias": self._frequencias,
            "atrasos": self._atrasos,
            "total_draws": self._total_draws,
            "alpha": self._alpha,
            "beta": self._beta,
            "delay_k": self._delay_k,
        }
        with open(path / "probabilistic_model.json", "w") as f:
            json.dump(data, f)

    def load(self, path: Path) -> None:
        path = Path(path)
        with open(path / "probabilistic_model.json") as f:
            data = json.load(f)
        self._frequencias = {int(k): v for k, v in data["frequencias"].items()}
        self._atrasos = {int(k): v for k, v in data["atrasos"].items()}
        self._total_draws = data["total_draws"]
        self._alpha = data.get("alpha", 0.6)
        self._beta = data.get("beta", 0.4)
        self._delay_k = data.get("delay_k", 50)