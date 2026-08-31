from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

import numpy as np

from diadesorte.dominio.entidades import Sorteio as Draw

TOTAL_NUMEROS = 31


class BaseModel(ABC):

    @abstractmethod
    def fit(self, draws: List[Draw]) -> None:
        ...

    @abstractmethod
    def score(self) -> np.ndarray:
        """Score de ordenação em [0, 1] para cada número (1..TOTAL_NUMEROS).

        NÃO é uma probabilidade estatística. Os modelos concretos aplicam
        normalização min-max, que força o número mais bem colocado a valer
        exatamente 1.0 por construção — independente da chance real de
        sorteio, que é sempre NUMEROS_POR_SORTEIO / TOTAL_NUMEROS para
        qualquer número. Serve apenas para ranquear números entre si.
        """
        ...

    def predict_proba(self) -> np.ndarray:
        """Alias legado de `score()`, mantido para compatibilidade.

        O nome sugere uma probabilidade estatística, o que o valor retornado
        não é — ver a docstring de `score()`. Prefira `score()`.
        """
        warnings.warn(
            "predict_proba() está depreciado; use score(). O valor retornado é "
            "um score de ordenação em [0,1], não uma probabilidade estatística.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.score()

    def select_top_7(self, probas: np.ndarray | None = None) -> List[int]:
        p = probas if probas is not None else self.score()
        indices = np.argsort(p)[::-1][:7]
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
