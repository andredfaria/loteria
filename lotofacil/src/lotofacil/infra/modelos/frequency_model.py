"""Stateless frequency-based model."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import numpy as np

from lotofacil.infra.config import TOTAL_NUMBERS
from lotofacil.infra.dados.leitor import Draw
from lotofacil.infra.modelos.base_model import BaseModel

logger = logging.getLogger(__name__)

_WEIGHTS = {"k10": 0.5, "k30": 0.3, "all": 0.2}


class FrequencyModel(BaseModel):
    """Scores numbers by weighted recent frequencies. Stateless — no sklearn."""

    def __init__(self):
        self._freq_k10 = np.ones(TOTAL_NUMBERS, dtype=np.float32) / TOTAL_NUMBERS
        self._freq_k30 = np.ones(TOTAL_NUMBERS, dtype=np.float32) / TOTAL_NUMBERS
        self._freq_all = np.ones(TOTAL_NUMBERS, dtype=np.float32) / TOTAL_NUMBERS
        self._fitted = False

    @property
    def name(self) -> str:
        return "frequency"

    def fit(self, draws: List[Draw]) -> None:
        n = len(draws)
        binary = np.zeros((n, TOTAL_NUMBERS), dtype=np.float32)
        for i, d in enumerate(draws):
            for num in d.dezenas:
                binary[i, num - 1] = 1.0

        def _window_freq(k: int) -> np.ndarray:
            tail = binary[-k:] if n >= k else binary
            return tail.mean(axis=0)

        self._freq_k10 = _window_freq(10)
        self._freq_k30 = _window_freq(30)
        self._freq_all = binary.mean(axis=0)
        self._fitted = True
        logger.debug("FrequencyModel fitted on %d draws", n)

    def predict_proba(self) -> np.ndarray:
        score = (
            _WEIGHTS["k10"] * self._freq_k10
            + _WEIGHTS["k30"] * self._freq_k30
            + _WEIGHTS["all"] * self._freq_all
        )
        lo, hi = score.min(), score.max()
        if hi > lo:
            score = (score - lo) / (hi - lo)
        return score.astype(np.float32)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        data = {
            "freq_k10": self._freq_k10.tolist(),
            "freq_k30": self._freq_k30.tolist(),
            "freq_all": self._freq_all.tolist(),
        }
        (path / "frequency_model.json").write_text(json.dumps(data))

    def load(self, path: Path) -> None:
        data = json.loads((Path(path) / "frequency_model.json").read_text())
        self._freq_k10 = np.array(data["freq_k10"], dtype=np.float32)
        self._freq_k30 = np.array(data["freq_k30"], dtype=np.float32)
        self._freq_all = np.array(data["freq_all"], dtype=np.float32)
        self._fitted = True
