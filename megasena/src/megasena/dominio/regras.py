from __future__ import annotations

from itertools import combinations
from math import comb
from typing import Iterator

from loteria_nucleo.combinatoria import (
    combinacoes_por_aposta as _combinacoes_por_aposta,
    custo_aposta as _custo_aposta,
    total_combinacoes as _total_combinacoes,
)
from loteria_nucleo.spec import LoteriaSpec

MEGASENA_SPEC = LoteriaSpec(
    slug="megasena", nome="Mega-Sena", menor_numero=1, maior_numero=60,
    numeros_por_sorteio=6, aposta_minima=6, aposta_maxima=20,
    preco_aposta_simples=6.0, faixas={6: "sena", 5: "quina", 4: "quadra"},
)

TOTAL_NUMEROS = 60
NUMEROS_POR_SORTEIO = 6
VALID_NUMBERS = set(range(1, TOTAL_NUMEROS + 1))

FAIXAS_ACERTOS = [4, 5, 6]


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


def gerar_combinacoes(n: int) -> Iterator[tuple[int, ...]]:
    yield from combinations(VALID_NUMBERS, n)


def total_combinacoes(n: int = NUMEROS_POR_SORTEIO) -> int:
    if n == NUMEROS_POR_SORTEIO:
        return _total_combinacoes(MEGASENA_SPEC)
    return comb(TOTAL_NUMEROS, n)

# ─── Preço oficial ────────────────────────────────────────────
# A Caixa não dá desconto por volume: uma aposta de n dezenas custa exatamente
# C(n, 6) apostas simples.
PRECO_APOSTA_SIMPLES = 6.00
TAMANHO_APOSTA_MIN = NUMEROS_POR_SORTEIO
TAMANHO_APOSTA_MAX = 20


def combinacoes_por_aposta(n: int) -> int:
    """Quantas apostas simples de 6 dezenas um volante de n dezenas contém."""
    return _combinacoes_por_aposta(MEGASENA_SPEC, n)


def custo_aposta(n: int) -> float:
    """Custo oficial de um volante de n dezenas."""
    return _custo_aposta(MEGASENA_SPEC, n)
