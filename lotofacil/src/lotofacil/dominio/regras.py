from __future__ import annotations

import itertools
from math import comb
from typing import Iterator

TOTAL_NUMEROS = 25
NUMEROS_POR_SORTEIO = 15
VALID_NUMBERS = set(range(1, TOTAL_NUMEROS + 1))

FAIXAS_ACERTOS = [11, 12, 13, 14, 15]
CUSTO_POR_JOGO: float = 3.50

TABELA_PREMIOS: dict[int, float] = {
    11: 7.00,
    12: 14.00,
    13: 35.00,
    14: 2_000.00,
    15: 1_500_000.00,
}

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
    if len(dezenas) != NUMEROS_POR_SORTEIO:
        return False
    if len(set(dezenas)) != NUMEROS_POR_SORTEIO:
        return False
    return all(d in VALID_NUMBERS for d in dezenas)


def contar_acertos(aposta: list[int], resultado: list[int]) -> int:
    return len(set(aposta) & set(resultado))


def contar_pares(dezenas: list[int]) -> int:
    return sum(1 for d in dezenas if d % 2 == 0)


def contar_impares(dezenas: list[int]) -> int:
    return NUMEROS_POR_SORTEIO - contar_pares(dezenas)


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


def distribuicao_quadrantes(dezenas: list[int]) -> dict[int, int]:
    return {q: sum(1 for d in dezenas if d in nums) for q, nums in QUADRANTES.items()}


def distribuicao_faixas(dezenas: list[int]) -> dict[int, int]:
    return {f: sum(1 for d in dezenas if d in nums) for f, nums in FAIXAS.items()}


def estatisticas_dezenas(dezenas: list[int]) -> dict:
    return {
        "pares": contar_pares(dezenas),
        "impares": contar_impares(dezenas),
        "soma": soma_dezenas(dezenas),
        "primos": contar_primos(dezenas),
        "fibonacci": contar_fibonacci(dezenas),
        "moldura": contar_moldura(dezenas),
        "consecutivos": contar_consecutivos(dezenas),
        "quadrantes": distribuicao_quadrantes(dezenas),
        "faixas": distribuicao_faixas(dezenas),
    }


def gerar_combinacoes(n: int) -> Iterator[tuple[int, ...]]:
    yield from itertools.combinations(VALID_NUMBERS, n)


def total_combinacoes(n: int = NUMEROS_POR_SORTEIO) -> int:
    return comb(TOTAL_NUMEROS, n)
