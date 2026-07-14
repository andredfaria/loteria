from __future__ import annotations

from itertools import combinations
from math import comb
from typing import Iterator

TOTAL_NUMEROS = 31
NUMEROS_POR_SORTEIO = 7
VALID_NUMBERS = set(range(1, TOTAL_NUMEROS + 1))

TODOS_MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

FAIXAS_ACERTOS = [4, 5, 6, 7]


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


def mes_valido(mes: str) -> bool:
    return mes in TODOS_MESES


def gerar_combinacoes(n: int) -> Iterator[tuple[int, ...]]:
    yield from combinations(VALID_NUMBERS, n)


def total_combinacoes(n: int = NUMEROS_POR_SORTEIO) -> int:
    return comb(TOTAL_NUMEROS, n)
