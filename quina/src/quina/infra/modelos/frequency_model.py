from __future__ import annotations

import json
from pathlib import Path
from typing import List

import numpy as np

from quina.dominio.entidades import Sorteio as Draw
from quina.infra.config import TOTAL_NUMEROS
from quina.infra.modelos.base_model import BaseModel


class FrequencyModel(BaseModel):
    def __init__(self):
        self._frequencias: dict[int, float] | None = None
        self._total_draws: int = 0

    @property
    def name(self) -> str:
        return "frequencia"

    def fit(self, draws: List[Draw]) -> None:
        self._total_draws = len(draws)
        counts = {n: 0 for n in range(1, TOTAL_NUMEROS + 1)}
        for d in draws:
            for n in d.dezenas:
                counts[n] += 1
        self._frequencias = {n: counts[n] / self._total_draws for n in range(1, TOTAL_NUMEROS + 1)}

    def predict_proba(self) -> np.ndarray:
        if self._frequencias is None:
            return np.full(TOTAL_NUMEROS, 1.0 / TOTAL_NUMEROS, dtype=np.float32)
        return np.array([self._frequencias[n] for n in range(1, TOTAL_NUMEROS + 1)], dtype=np.float32)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        data = {
            "frequencias": self._frequencias,
            "total_draws": self._total_draws,
        }
        with open(path / "frequency_model.json", "w") as f:
            json.dump(data, f)

    def load(self, path: Path) -> None:
        path = Path(path)
        with open(path / "frequency_model.json") as f:
            data = json.load(f)
        self._frequencias = {int(k): v for k, v in data["frequencias"].items()}
        self._total_draws = data["total_draws"]