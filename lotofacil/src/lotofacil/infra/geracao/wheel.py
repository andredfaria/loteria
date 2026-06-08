"""Núcleo combinatório de fechamento (covering design) para Lotofácil.

Representação por bitmask: a dezena ``n`` (1..25) ocupa o bit ``n-1``.
Os acertos entre um jogo e um sorteio são ``(jogo & sorteio).bit_count()``.

O verificador de garantia (:func:`curva_garantia`) é **exato**: dado um conjunto
de jogos e um pool de N dezenas, para cada ``p`` (quantas das N são sorteadas) ele
retorna o ``g`` garantido = o pior caso (mínimo, sobre todos os p-subconjuntos do
pool) do melhor jogo (máximo de acertos). Essa é a parte *provável* — a garantia
reportada é sempre a verificada, independente de como os jogos foram gerados.

O gerador (:func:`gerar_fechamento`) é heurístico (covering guloso + busca binária
no nível de garantia); só a *quantidade* de jogos é heurística, não a garantia.
"""
from __future__ import annotations

import itertools
from typing import Iterable

TAMANHO_JOGO_PADRAO = 15


# ─── conversão bitmask ─────────────────────────────────────────────────────────

def para_bitmask(dezenas: Iterable[int]) -> int:
    mask = 0
    for d in dezenas:
        mask |= 1 << (d - 1)
    return mask


def para_dezenas(mask: int) -> list[int]:
    return [i + 1 for i in range(25) if mask & (1 << i)]


# ─── acertos ───────────────────────────────────────────────────────────────────

def acertos(jogo_mask: int, sorteio_mask: int) -> int:
    """Quantas dezenas o jogo acertou no sorteio (ambos bitmasks)."""
    return (jogo_mask & sorteio_mask).bit_count()


# ─── verificador exato da curva de garantia ─────────────────────────────────────

def curva_garantia(jogos: list[int], pool: list[int]) -> dict[int, int]:
    """Curva de garantia exata do conjunto de ``jogos`` (bitmasks) sobre o ``pool``.

    Retorna ``{p: g}`` onde ``g`` é o número de acertos garantido no pior caso
    quando exatamente ``p`` das dezenas do pool são sorteadas.
    """
    curva: dict[int, int] = {}
    for p in range(len(pool) + 1):
        pior: int | None = None
        for combo in itertools.combinations(pool, p):
            alvo = para_bitmask(combo)
            melhor = max((acertos(j, alvo) for j in jogos), default=0)
            pior = melhor if pior is None else min(pior, melhor)
        curva[p] = pior if pior is not None else 0
    return curva


# ─── gerador (covering guloso + busca binária) ──────────────────────────────────

def _subconjuntos_mask(pool: list[int], p: int) -> list[int]:
    return [para_bitmask(c) for c in itertools.combinations(pool, p)]


def _candidatos(pool: list[int], tamanho_jogo: int) -> list[int]:
    return [para_bitmask(c) for c in itertools.combinations(pool, tamanho_jogo)]


def _cobre(candidatos: list[int], subsets: list[int], t: int, limite: int) -> list[int] | None:
    """Covering guloso: cobre todo subset com >=t acertos em <=limite jogos.

    Retorna a lista de jogos (<=limite) se conseguir cobrir tudo; senão None.
    """
    descobertos = set(range(len(subsets)))
    escolhidos: list[int] = []
    while descobertos:
        if len(escolhidos) >= limite:
            return None
        melhor_cand = None
        melhor_cobertura: set[int] = set()
        for cand in candidatos:
            cobre = {i for i in descobertos if acertos(cand, subsets[i]) >= t}
            if len(cobre) > len(melhor_cobertura) or (
                len(cobre) == len(melhor_cobertura)
                and melhor_cand is not None
                and cand < melhor_cand
            ):
                melhor_cand, melhor_cobertura = cand, cobre
        if not melhor_cobertura:
            return None  # nenhum candidato cobre nada → t inalcançável
        escolhidos.append(melhor_cand)  # type: ignore[arg-type]
        descobertos -= melhor_cobertura
    return escolhidos


def _preencher(jogos: list[int], candidatos: list[int], subsets: list[int],
               n_jogos: int) -> list[int]:
    """Preenche até n_jogos escolhendo o candidato que mais eleva a cobertura total."""
    jogos = list(jogos)
    melhor_por_subset = [max((acertos(j, s) for j in jogos), default=0) for s in subsets]
    usados = set(jogos)
    while len(jogos) < n_jogos:
        melhor_cand = None
        melhor_ganho = -1
        for cand in candidatos:
            ganho = sum(
                max(0, acertos(cand, subsets[i]) - melhor_por_subset[i])
                for i in range(len(subsets))
            )
            if ganho > melhor_ganho or (
                ganho == melhor_ganho and melhor_cand is not None and cand < melhor_cand
            ):
                # prefere candidato inédito quando empata em ganho
                if ganho == melhor_ganho and cand in usados and melhor_cand not in usados:
                    continue
                melhor_cand, melhor_ganho = cand, ganho
        if melhor_cand is None:
            break
        jogos.append(melhor_cand)
        usados.add(melhor_cand)
        for i in range(len(subsets)):
            melhor_por_subset[i] = max(melhor_por_subset[i], acertos(melhor_cand, subsets[i]))
    return jogos


def gerar_fechamento(
    pool: list[int],
    n_jogos: int,
    alvo_p: int | None = None,
    tamanho_jogo: int = TAMANHO_JOGO_PADRAO,
) -> list[list[int]]:
    """Gera ``n_jogos`` jogos de ``tamanho_jogo`` dezenas ⊆ ``pool`` maximizando a
    garantia de pior caso para ``alvo_p`` dezenas sorteadas do pool.

    Default ``alvo_p = min(len(pool), 15)`` (melhor caso de quantas do pool saem).
    """
    if n_jogos < 1:
        raise ValueError("n_jogos deve ser >= 1")
    if len(pool) < tamanho_jogo:
        raise ValueError(f"pool ({len(pool)}) menor que o tamanho do jogo ({tamanho_jogo})")
    if len(set(pool)) != len(pool):
        raise ValueError("pool tem dezenas repetidas")

    if alvo_p is None:
        alvo_p = min(len(pool), 15)
    alvo_p = max(0, min(alvo_p, len(pool)))

    candidatos = _candidatos(pool, tamanho_jogo)
    subsets = _subconjuntos_mask(pool, alvo_p)

    melhor_jogos: list[int] = []
    teto_t = min(tamanho_jogo, alvo_p)
    for t in range(teto_t, 0, -1):
        cobertura = _cobre(candidatos, subsets, t, n_jogos)
        if cobertura is not None:
            melhor_jogos = cobertura
            break

    melhor_jogos = _preencher(melhor_jogos, candidatos, subsets, n_jogos)
    return [para_dezenas(m) for m in melhor_jogos]
