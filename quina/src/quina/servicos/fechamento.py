"""Fechamento/wheeling: cobertura combinatória aproximada (greedy set-cover).

Não é o mínimo matemático ótimo — cobertura exata é NP-difícil para pools
grandes. LIMITE_POOL mantém o espaço de busca tratável.
"""
from __future__ import annotations

import itertools

from quina.dominio.regras import NUMEROS_POR_SORTEIO, custo_aposta

LIMITE_POOL = 12


def gerar_fechamento(pool: list[int], garantia: tuple[int, int]) -> dict:
    k, faixa = garantia
    pool_ordenado = sorted(pool)

    if len(set(pool_ordenado)) != len(pool_ordenado):
        raise ValueError("pool não pode conter dezenas repetidas")
    if len(pool_ordenado) < NUMEROS_POR_SORTEIO:
        raise ValueError(f"pool deve ter pelo menos {NUMEROS_POR_SORTEIO} dezenas")
    if len(pool_ordenado) > LIMITE_POOL:
        raise ValueError(f"pool suporta no máximo {LIMITE_POOL} dezenas (limite de performance)")
    if not (2 <= faixa <= NUMEROS_POR_SORTEIO):
        raise ValueError(f"faixa de garantia deve estar entre 2 e {NUMEROS_POR_SORTEIO}")
    if not (faixa <= k <= len(pool_ordenado)):
        raise ValueError(f"k deve estar entre {faixa} e o tamanho do pool")

    combinacoes_garantia = list(itertools.combinations(pool_ordenado, k))
    combinacoes_bilhete = list(itertools.combinations(pool_ordenado, NUMEROS_POR_SORTEIO))

    nao_cobertas = set(range(len(combinacoes_garantia)))
    jogos_escolhidos: list[list[int]] = []

    while nao_cobertas:
        melhor_bilhete = None
        melhor_cobertura: set[int] = set()
        for bilhete in combinacoes_bilhete:
            bilhete_set = set(bilhete)
            cobertas = {
                i for i in nao_cobertas
                if len(bilhete_set & set(combinacoes_garantia[i])) >= faixa
            }
            if len(cobertas) > len(melhor_cobertura):
                melhor_cobertura = cobertas
                melhor_bilhete = bilhete

        if melhor_bilhete is None or not melhor_cobertura:
            raise ValueError("não foi possível cobrir todas as combinações de garantia com o pool informado")

        jogos_escolhidos.append(list(melhor_bilhete))
        nao_cobertas -= melhor_cobertura

    custo_total = round(len(jogos_escolhidos) * custo_aposta(NUMEROS_POR_SORTEIO), 2)
    return {"jogos": jogos_escolhidos, "quantidade": len(jogos_escolhidos), "custo_total": custo_total}
