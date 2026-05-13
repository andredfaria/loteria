from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from lotofacil.dominio.regras import NUMEROS_POR_SORTEIO, TOTAL_NUMEROS, VALID_NUMBERS


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


class Predicao(BaseModel):
    concurso_alvo: int
    dezenas: list[int]
    probabilidades: list[float]
    confianca_media: float
    estrategia: str
    abordagem: str
    criado_em: str = Field(default_factory=lambda: datetime.now().isoformat())

    @field_validator("probabilidades", mode="after")
    @classmethod
    def validar_probabilidades(cls, v: list[float]) -> list[float]:
        if len(v) != TOTAL_NUMEROS:
            raise ValueError(f"Esperado {TOTAL_NUMEROS} probabilidades, obtido {len(v)}")
        return v

    @field_validator("dezenas", mode="after")
    @classmethod
    def validar_dezenas(cls, v: list[int]) -> list[int]:
        if not all(1 <= d <= TOTAL_NUMEROS for d in v):
            raise ValueError(f"Dezenas devem estar entre 1-{TOTAL_NUMEROS}")
        return sorted(v)


class Portfolio(BaseModel):
    concurso_alvo: int
    jogos: list[list[int]]
    estrategia: str
    criado_em: str = Field(default_factory=lambda: datetime.now().isoformat())


class ResultadoValidacao(BaseModel):
    concurso_alvo: int
    dezenas_sugeridas: list[int]
    dezenas_reais: list[int]
    acertos: int
    validado_em: str = Field(default_factory=lambda: datetime.now().isoformat())


class ResultadoBacktest(BaseModel):
    estrategia: str
    abordagem: str
    concursos_testados: int
    acertos_media: float
    acertos_11: int
    acertos_12: int
    acertos_13: int
    acertos_14: int
    acertos_15: int
    roi_percent: float
    criado_em: str = Field(default_factory=lambda: datetime.now().isoformat())


Draw = Sorteio
Prediction = Predicao
