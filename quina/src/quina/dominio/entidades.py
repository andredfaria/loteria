from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from quina.dominio.regras import NUMEROS_POR_SORTEIO, TOTAL_NUMEROS


class Sorteio(BaseModel):
    concurso: int = Field(..., ge=1)
    data: str
    dezenas: list[int]

    @field_validator("dezenas", mode="after")
    @classmethod
    def validar_dezenas(cls, v: list[int]) -> list[int]:
        if len(v) != NUMEROS_POR_SORTEIO:
            raise ValueError(f"Esperado {NUMEROS_POR_SORTEIO} dezenas, obtido {len(v)}")
        if len(set(v)) != NUMEROS_POR_SORTEIO:
            raise ValueError("Dezenas devem ser unicas")
        if not all(1 <= d <= TOTAL_NUMEROS for d in v):
            raise ValueError(f"Dezenas devem estar entre 1-{TOTAL_NUMEROS}")
        return sorted(v)


class SorteioBruto(BaseModel):
    concurso: int
    data: str
    dezenas: list[str]
    dezenasOrdemSorteio: Optional[list[str]] = None


Draw = Sorteio
