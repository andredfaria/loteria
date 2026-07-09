"""Geração e pontuação de candidatos de jogos da Quina."""
from __future__ import annotations

import random
from typing import Optional

from quina.dominio.regras import TOTAL_NUMEROS
from quina.servicos.estrategias import filtros

FILTROS_PADRAO = {
    "soma": filtros.score_soma,
    "paridade": filtros.score_paridade,
    "quadrantes": filtros.score_quadrantes,
    "primos": filtros.score_primos,
    "repeticao": filtros.score_repeticao,
    "consecutivos": filtros.score_consecutivos,
    "anti_popularidade": filtros.score_anti_popularidade,
}

_FILTROS_QUE_USAM_DRAWS = {"soma", "repeticao", "consecutivos"}


def _pontuar_candidato(
    dezenas: list[int], draws: list[dict], pesos: dict[str, float]
) -> tuple[float, dict[str, float]]:
    detalhes = {}
    for nome in pesos:
        funcao = FILTROS_PADRAO[nome]
        detalhes[nome] = funcao(dezenas, draws) if nome in _FILTROS_QUE_USAM_DRAWS else funcao(dezenas)

    total_pesos = sum(pesos.values())
    score = sum(detalhes[nome] * peso for nome, peso in pesos.items()) / total_pesos
    return round(score, 4), detalhes


def gerar_candidatos(
    quantidade: int,
    tamanho_aposta: int,
    draws: list[dict],
    pesos: Optional[dict[str, float]] = None,
) -> list[dict]:
    if pesos is None:
        pesos = {nome: 1.0 for nome in FILTROS_PADRAO}

    universo = range(1, TOTAL_NUMEROS + 1)
    candidatos = []
    for _ in range(quantidade):
        dezenas = sorted(random.sample(universo, tamanho_aposta))
        score, detalhes = _pontuar_candidato(dezenas, draws, pesos)
        candidatos.append({"dezenas": dezenas, "score": score, "detalhes": detalhes})

    candidatos.sort(key=lambda c: c["score"], reverse=True)
    return candidatos


def top_k(candidatos: list[dict], k: int) -> list[dict]:
    return sorted(candidatos, key=lambda c: c["score"], reverse=True)[:k]
