"""ROI Lab: statistical filter backtest service."""
from __future__ import annotations

import dataclasses
import json
import random
from pathlib import Path
from typing import Any

from lotofacil.infra.avaliacao.financeiro import FinancialSimulator
from lotofacil.infra.config import SAIDA_DIR
from lotofacil.infra.dados.banco import DatabaseManager

MOLDURA: frozenset[int] = frozenset({1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25})
PRIMOS: frozenset[int] = frozenset({2, 3, 5, 7, 11, 13, 17, 19, 23})
FIBONACCI: frozenset[int] = frozenset({1, 2, 3, 5, 8, 13, 21})
_TODOS_NUMEROS: list[int] = list(range(1, 26))
_MAX_TENTATIVAS: int = 200


def _valida_filtros(
    numeros: list[int],
    filtros: dict[str, Any],
    anterior: list[int] | None,
) -> bool:
    soma = sum(numeros)
    if (f := filtros.get("soma")) is not None and not (f[0] <= soma <= f[1]):
        return False

    pares = sum(1 for n in numeros if n % 2 == 0)
    if (f := filtros.get("pares")) is not None and not (f[0] <= pares <= f[1]):
        return False

    primos = sum(1 for n in numeros if n in PRIMOS)
    if (f := filtros.get("primos")) is not None and not (f[0] <= primos <= f[1]):
        return False

    fibs = sum(1 for n in numeros if n in FIBONACCI)
    if (f := filtros.get("fibonacci")) is not None and not (f[0] <= fibs <= f[1]):
        return False

    moldura = sum(1 for n in numeros if n in MOLDURA)
    if (f := filtros.get("moldura")) is not None and not (f[0] <= moldura <= f[1]):
        return False

    if anterior is not None and (f := filtros.get("repeticoes")) is not None:
        rep = len(set(numeros) & set(anterior))
        if not (f[0] <= rep <= f[1]):
            return False

    if (f := filtros.get("consecutivos")) is not None:
        s = sorted(numeros)
        consec = sum(1 for i in range(len(s) - 1) if s[i + 1] - s[i] == 1)
        if consec < f:
            return False

    return True


def _gerar_jogo_filtrado(
    filtros: dict[str, Any],
    anterior: list[int] | None,
    rng: random.Random,
) -> list[int] | None:
    for _ in range(_MAX_TENTATIVAS):
        candidato = sorted(rng.sample(_TODOS_NUMEROS, 15))
        if _valida_filtros(candidato, filtros, anterior):
            return candidato
    return None
