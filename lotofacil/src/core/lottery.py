"""Lotofácil rules, validation and combinatorics."""

from __future__ import annotations

import itertools
from typing import Iterator

from core.config import NUMBERS_PER_DRAW, TOTAL_NUMBERS, VALID_NUMBERS

MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
FIBONACCI = {1, 2, 3, 5, 8, 13, 21}
QUADRANTES = {
    1: set(range(1, 7)),
    2: set(range(7, 13)),
    3: set(range(13, 19)),
    4: set(range(19, 26)),
}
FAIXAS = {
    1: set(range(1, 6)),
    2: set(range(6, 11)),
    3: set(range(11, 16)),
    4: set(range(16, 21)),
    5: set(range(21, 26)),
}


def validar_dezenas(dezenas: list[int]) -> bool:
    """Check if a list of numbers is a valid Lotofácil bet."""
    if len(dezenas) != NUMBERS_PER_DRAW:
        return False
    if len(set(dezenas)) != NUMBERS_PER_DRAW:
        return False
    return all(d in VALID_NUMBERS for d in dezenas)


def contar_acertos(aposta: list[int], resultado: list[int]) -> int:
    """Count matches between a bet and a result."""
    return len(set(aposta) & set(resultado))


def contar_pares(dezenas: list[int]) -> int:
    return sum(1 for d in dezenas if d % 2 == 0)


def contar_impares(dezenas: list[int]) -> int:
    return NUMBERS_PER_DRAW - contar_pares(dezenas)


def soma_dezenas(dezenas: list[int]) -> int:
    return sum(dezenas)


def contar_primos(dezenas: list[int]) -> int:
    return sum(1 for d in dezenas if d in PRIMOS)


def contar_fibonacci(dezenas: list[int]) -> int:
    return sum(1 for d in dezenas if d in FIBONACCI)


def contar_moldura(dezenas: list[int]) -> int:
    return sum(1 for d in dezenas if d in MOLDURA)


def contar_consecutivos(dezenas: list[int]) -> int:
    s = sorted(dezenas)
    return sum(1 for i in range(len(s) - 1) if s[i + 1] == s[i] + 1)


def repetidos_anterior(atual: list[int], anterior: list[int]) -> int:
    return len(set(atual) & set(anterior))


def quadrantes_distribution(dezenas: list[int]) -> dict[int, int]:
    return {q: sum(1 for d in dezenas if d in nums) for q, nums in QUADRANTES.items()}


def faixas_distribution(dezenas: list[int]) -> dict[int, int]:
    return {f: sum(1 for d in dezenas if d in nums) for f, nums in FAIXAS.items()}


def estatisticas_dezenas(dezenas: list[int]) -> dict:
    """Compute all standard statistics for a set of dezenas."""
    return {
        "pares": contar_pares(dezenas),
        "impares": contar_impares(dezenas),
        "soma": soma_dezenas(dezenas),
        "primos": contar_primos(dezenas),
        "fibonacci": contar_fibonacci(dezenas),
        "moldura": contar_moldura(dezenas),
        "consecutivos": contar_consecutivos(dezenas),
        "quadrantes": quadrantes_distribution(dezenas),
        "faixas": faixas_distribution(dezenas),
    }


def gerar_combinacoes(n: int) -> Iterator[tuple[int, ...]]:
    """Generate all C(25, n) combinations."""
    yield from itertools.combinations(VALID_NUMBERS, n)


def total_combinacoes(n: int = NUMBERS_PER_DRAW) -> int:
    """Total number of possible combinations C(25, n)."""
    from math import comb
    return comb(TOTAL_NUMBERS, n)
