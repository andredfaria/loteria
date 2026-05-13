"""Ensemble of frequency windows — combines multiple lookback periods by weighted average."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Union

import numpy as np

from lotofacil.infra.config import TOTAL_NUMBERS
from lotofacil.infra.dados.leitor import Draw
from lotofacil.infra.modelos.base_model import BaseModel

logger = logging.getLogger(__name__)

_DEFAULT_WINDOWS: Dict[Union[int, str], float] = {
    5: 0.30,
    15: 0.25,
    30: 0.20,
    50: 0.15,
    100: 0.10,
}


class FrequencyEnsembleModel(BaseModel):
    """Scores numbers by weighted average of multiple frequency windows.

    Each window k contributes freq_k = mean of last k draws (binary matrix).
    If n < k, uses all available draws for that window.
    The special key "all" uses the full history.
    """

    def __init__(self, windows: Dict[Union[int, str], float] | None = None):
        self._windows = windows if windows is not None else dict(_DEFAULT_WINDOWS)
        self._scores: np.ndarray = np.ones(TOTAL_NUMBERS, dtype=np.float32) / TOTAL_NUMBERS
        self._fitted = False

    @property
    def name(self) -> str:
        return "frequency_ensemble"

    def fit(self, draws: List[Draw]) -> None:
        if not draws:
            logger.warning("FrequencyEnsembleModel.fit() called with empty draws list; model not fitted")
            return
        n = len(draws)
        binary = np.zeros((n, TOTAL_NUMBERS), dtype=np.float32)
        for i, d in enumerate(draws):
            for num in d.dezenas:
                binary[i, num - 1] = 1.0

        combined = np.zeros(TOTAL_NUMBERS, dtype=np.float32)
        total_weight = 0.0

        for key, weight in self._windows.items():
            if key == "all":
                freq = binary.mean(axis=0)
            else:
                k = int(key)
                tail = binary[-k:] if n >= k else binary
                freq = tail.mean(axis=0)
            combined += weight * freq
            total_weight += weight

        if total_weight > 0:
            combined /= total_weight

        lo, hi = combined.min(), combined.max()
        if hi > lo:
            self._scores = ((combined - lo) / (hi - lo)).astype(np.float32)
        else:
            self._scores = np.ones(TOTAL_NUMBERS, dtype=np.float32) * 0.5

        self._fitted = True
        logger.debug("FrequencyEnsembleModel fitted on %d draws with %d windows", n, len(self._windows))

    def predict_proba(self) -> np.ndarray:
        if not self._fitted:
            logger.warning("FrequencyEnsembleModel.predict_proba() called before fit(); returning uniform prior")
        return self._scores.copy()

    def save(self, path: Path) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        data = {
            "windows": {str(k): v for k, v in self._windows.items()},
            "scores": self._scores.tolist(),
        }
        (path / "frequency_ensemble_model.json").write_text(json.dumps(data))

    def load(self, path: Path) -> None:
        raw = json.loads((Path(path) / "frequency_ensemble_model.json").read_text())
        # Restore int keys where possible
        self._windows = {}
        for k, v in raw["windows"].items():
            self._windows[int(k) if k.isdigit() else k] = v
        self._scores = np.array(raw["scores"], dtype=np.float32)
        self._fitted = True
