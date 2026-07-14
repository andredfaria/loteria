from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from supersete.dominio.regras import DIGITOS, NUM_COLUNAS


class Sorteio(BaseModel):
    concurso: int = Field(..., ge=1)
    data: str
    digitos: list[int]

    @field_validator("digitos", mode="after")
    @classmethod
    def validar_digitos(cls, v: list[int]) -> list[int]:
        if len(v) != NUM_COLUNAS:
            raise ValueError(f"Esperado {NUM_COLUNAS} digitos, obtido {len(v)}")
        if not all(d in DIGITOS for d in v):
            raise ValueError(f"Digitos devem estar entre 0-9")
        return v


class SorteioBruto(BaseModel):
    concurso: int
    data: str
    dezenas: list[str]
    dezenasOrdemSorteio: Optional[list[str]] = None
