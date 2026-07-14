from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

import numpy as np

from quina.dominio.entidades import Sorteio as Draw


class BaseModel(ABC):

    @abstractmethod
    def fit(self, draws: List[Draw]) -> None:
        ...

    @abstractmethod
    def predict_proba(self) -> np.ndarray:
        ...

    def select_top_5(self, probas: np.ndarray | None = None) -> List[int]:
        p = probas if probas is not None else self.predict_proba()
        indices = np.argsort(p)[::-1][:5]
        return sorted(int(i + 1) for i in indices)

    @abstractmethod
    def save(self, path: Path) -> None:
        ...

    @abstractmethod
    def load(self, path: Path) -> None:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...