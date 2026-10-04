"""Descrição declarativa das regras de cada loteria."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class LoteriaSpec:
    slug: str
    nome: str
    menor_numero: int
    maior_numero: int
    numeros_por_sorteio: int
    aposta_minima: int
    aposta_maxima: int
    preco_aposta_simples: float | None
    faixas: Mapping[int, str]
    posicional: bool = False
    campos_extras: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.slug or not self.slug.replace("-", "").isalnum():
            raise ValueError("slug deve conter apenas letras, números e hífens")
        if self.menor_numero > self.maior_numero:
            raise ValueError("faixa de números inválida")
        if self.numeros_por_sorteio < 1:
            raise ValueError("numeros_por_sorteio deve ser positivo")
        if not 1 <= self.aposta_minima <= self.aposta_maxima:
            raise ValueError("limites de aposta inválidos")

    @property
    def total_numeros(self) -> int:
        return self.maior_numero - self.menor_numero + 1

    @property
    def numeros_validos(self) -> range:
        return range(self.menor_numero, self.maior_numero + 1)

    @property
    def prefixo_env(self) -> str:
        return self.slug.replace("-", "").upper()
