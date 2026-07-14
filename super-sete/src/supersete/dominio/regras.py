from __future__ import annotations

from typing import Set

NUM_COLUNAS = 7
DIGITOS = set(range(10))
TOTAL_COMBINACOES = 10 ** NUM_COLUNAS

VALOR_APOSTA = 2.50


def validar_digitos(digitos: list[int]) -> bool:
    if len(digitos) != NUM_COLUNAS:
        return False
    return all(d in DIGITOS for d in digitos)


def contar_acertos(aposta: list[int], resultado: list[int]) -> int:
    return sum(1 for a, r in zip(aposta, resultado) if a == r)


def colunas_zeradas(digitos: list[int]) -> int:
    return sum(1 for d in digitos if d == 0)
