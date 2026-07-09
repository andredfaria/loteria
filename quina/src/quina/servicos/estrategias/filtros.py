"""Filtros estatísticos puros para pontuação de candidatos de jogos da Quina.

Cada score_* retorna um valor em [0, 1]: quanto maior, mais o candidato se
aproxima do padrão observado nos sorteios reais — exceto anti_popularidade,
que mede aproximação ao padrão que maximiza valor esperado de prêmio (menos
rateio), não um padrão de frequência histórica.
"""
from __future__ import annotations

import statistics

from quina.dominio.regras import NUMEROS_POR_SORTEIO, TOTAL_NUMEROS

_PRIMOS = frozenset({2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79})
_PROPORCAO_PRIMOS_UNIVERSO = len(_PRIMOS) / TOTAL_NUMEROS

_LIMITE_POPULAR = 31
_PROPORCAO_POPULAR_ESPERADA = _LIMITE_POPULAR / TOTAL_NUMEROS


def score_soma(dezenas: list[int], draws: list[dict]) -> float:
    n = len(dezenas)
    somas_historicas = [sum(d["dezenas"]) for d in draws]
    media_5 = statistics.mean(somas_historicas)
    desvio_5 = statistics.pstdev(somas_historicas) or 1.0

    fator = n / NUMEROS_POR_SORTEIO
    media_esperada = media_5 * fator
    desvio_esperado = desvio_5 * (fator ** 0.5)

    diferenca = abs(sum(dezenas) - media_esperada)
    return max(0.0, 1.0 - diferenca / (2 * desvio_esperado))


def score_paridade(dezenas: list[int]) -> float:
    n = len(dezenas)
    pares = sum(1 for d in dezenas if d % 2 == 0)
    ideal = n / 2
    max_desvio = ideal or 1.0
    return max(0.0, 1.0 - abs(pares - ideal) / max_desvio)


def score_quadrantes(dezenas: list[int]) -> float:
    n = len(dezenas)
    quadrantes = [0, 0, 0, 0]
    for d in dezenas:
        indice = min((d - 1) // 20, 3)
        quadrantes[indice] += 1
    ideal = n / 4
    desvio_total = sum(abs(c - ideal) for c in quadrantes)
    desvio_maximo = 1.5 * n
    return max(0.0, 1.0 - desvio_total / desvio_maximo)


def score_primos(dezenas: list[int]) -> float:
    n = len(dezenas)
    primos = sum(1 for d in dezenas if d in _PRIMOS)
    ideal = n * _PROPORCAO_PRIMOS_UNIVERSO
    max_desvio = max(ideal, n - ideal) or 1.0
    return max(0.0, 1.0 - abs(primos - ideal) / max_desvio)


def score_repeticao(dezenas: list[int], draws: list[dict]) -> float:
    n = len(dezenas)
    if len(draws) < 2:
        taxa_historica = 0.0
    else:
        total_overlap = sum(
            len(set(a["dezenas"]) & set(b["dezenas"]))
            for a, b in zip(draws, draws[1:])
        )
        taxa_historica = total_overlap / (len(draws) - 1) / NUMEROS_POR_SORTEIO

    ultimo_sorteio = set(draws[-1]["dezenas"])
    overlap = len(set(dezenas) & ultimo_sorteio)
    esperado = taxa_historica * n
    max_desvio = max(esperado, n - esperado, 1.0)
    return max(0.0, 1.0 - abs(overlap - esperado) / max_desvio)


def score_consecutivos(dezenas: list[int], draws: list[dict]) -> float:
    n = len(dezenas)
    pares_possiveis = max(n - 1, 1)
    ordenado = sorted(dezenas)
    consecutivos_candidato = sum(1 for a, b in zip(ordenado, ordenado[1:]) if b - a == 1)

    if not draws:
        taxa_historica = 0.0
    else:
        total_consecutivos = 0
        for sorteio in draws:
            ord_s = sorted(sorteio["dezenas"])
            total_consecutivos += sum(1 for a, b in zip(ord_s, ord_s[1:]) if b - a == 1)
        taxa_historica = total_consecutivos / len(draws) / (NUMEROS_POR_SORTEIO - 1)

    esperado = taxa_historica * pares_possiveis
    max_desvio = max(esperado, pares_possiveis - esperado, 1.0)
    return max(0.0, 1.0 - abs(consecutivos_candidato - esperado) / max_desvio)


def score_anti_popularidade(dezenas: list[int]) -> float:
    n = len(dezenas)
    populares = sum(1 for d in dezenas if d <= _LIMITE_POPULAR)
    proporcao = populares / n
    if proporcao <= _PROPORCAO_POPULAR_ESPERADA:
        return 1.0
    excesso = proporcao - _PROPORCAO_POPULAR_ESPERADA
    maximo_excesso = 1.0 - _PROPORCAO_POPULAR_ESPERADA
    return max(0.0, 1.0 - excesso / maximo_excesso)
