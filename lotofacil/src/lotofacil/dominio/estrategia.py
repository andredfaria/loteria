from __future__ import annotations

from typing import List, Protocol

import numpy as np

from lotofacil.dominio.entidades import Predicao, Sorteio


class EstrategiaBase(Protocol):
    @property
    def nome(self) -> str: ...

    @property
    def quantidade_alvo(self) -> int: ...

    @property
    def abordagens(self) -> List[str]: ...

    def predizer(self, sorteios: List[Sorteio], abordagem: str = "todas") -> Predicao: ...

    def predizer_lote(self, sorteios: List[Sorteio], abordagem: str = "todas") -> List[Predicao]: ...

    def selecionar_numeros(self, probabilidades: np.ndarray, n: int | None = None) -> List[int]: ...

    def avaliar(self, predicao: Predicao, resultado: List[int]) -> int: ...


BaseStrategy = EstrategiaBase
