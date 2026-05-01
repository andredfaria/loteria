"""Data models for Lotofácil draws and predictions."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from core.config import NUMBERS_PER_DRAW, TOTAL_NUMBERS, VALID_NUMBERS


class Draw(BaseModel):
    """Represents a single Lotofácil draw."""
    concurso: int = Field(..., ge=1)
    data: str
    dezenas: list[int]

    @field_validator("dezenas", mode="after")
    @classmethod
    def validate_dezenas(cls, v: list[int]) -> list[int]:
        if len(v) != NUMBERS_PER_DRAW:
            raise ValueError(f"Expected {NUMBERS_PER_DRAW} dezenas, got {len(v)}")
        if len(set(v)) != NUMBERS_PER_DRAW:
            raise ValueError("Dezenas must be unique")
        if not all(1 <= d <= TOTAL_NUMBERS for d in v):
            raise ValueError(f"Dezenas must be in range 1-{TOTAL_NUMBERS}")
        return sorted(v)


class DrawRaw(BaseModel):
    """Raw API response for a Lotofácil draw."""
    concurso: int
    data: str
    dezenas: list[str]
    dezenasOrdemSorteio: Optional[list[str]] = None


class Prediction(BaseModel):
    """A prediction for an upcoming draw."""
    concurso_alvo: int
    dezenas: list[int]
    probabilidades: list[float]
    confianca_media: float
    strategy: str
    approach: str
    criado_em: str = Field(default_factory=lambda: datetime.now().isoformat())

    @field_validator("probabilidades", mode="after")
    @classmethod
    def validate_probabilities(cls, v: list[float]) -> list[float]:
        if len(v) != TOTAL_NUMBERS:
            raise ValueError(f"Expected {TOTAL_NUMBERS} probabilities, got {len(v)}")
        return v

    @field_validator("dezenas", mode="after")
    @classmethod
    def validate_dezenas(cls, v: list[int]) -> list[int]:
        if not all(1 <= d <= TOTAL_NUMBERS for d in v):
            raise ValueError(f"Dezenas must be in range 1-{TOTAL_NUMBERS}")
        return sorted(v)


class ValidationResult(BaseModel):
    """Result of validating a prediction against actual draw."""
    concurso_alvo: int
    dezenas_sugeridas: list[int]
    dezenas_reais: list[int]
    acertos: int
    acertos_validado_em: str = Field(default_factory=lambda: datetime.now().isoformat())


class BacktestResult(BaseModel):
    """Aggregated backtest results."""
    strategy: str
    approach: str
    concursos_testados: int
    acertos_media: float
    acertos_11: int
    acertos_12: int
    acertos_13: int
    acertos_14: int
    acertos_15: int
    roi_percent: float
    criado_em: str = Field(default_factory=lambda: datetime.now().isoformat())
