"""Testes do núcleo combinatório de fechamento (covering design)."""
from __future__ import annotations

import itertools

import pytest

from lotofacil.infra.geracao.wheel import (
    acertos,
    curva_garantia,
    gerar_fechamento,
    para_bitmask,
    para_dezenas,
)


# ─── conversão bitmask ─────────────────────────────────────────────────────────

def test_bitmask_roundtrip():
    dezenas = [1, 7, 13, 25]
    mask = para_bitmask(dezenas)
    assert para_dezenas(mask) == sorted(dezenas)


def test_dezena_1_e_bit_0():
    assert para_bitmask([1]) == 0b1
    assert para_bitmask([25]) == 1 << 24


# ─── acertos ───────────────────────────────────────────────────────────────────

def test_acertos_conta_intersecao():
    jogo = para_bitmask([1, 2, 3, 10])
    sorteio = para_bitmask([2, 3, 4, 10, 11])
    assert acertos(jogo, sorteio) == 3  # {2,3,10}


# ─── curva de garantia (verificador exato) ──────────────────────────────────────

def test_curva_garantia_caso_calculado_a_mao():
    # pool {1,2,3,4}; jogos {1,2} e {3,4}. Curva calculada à mão no spec.
    pool = [1, 2, 3, 4]
    jogos = [para_bitmask([1, 2]), para_bitmask([3, 4])]
    assert curva_garantia(jogos, pool) == {0: 0, 1: 1, 2: 1, 3: 2, 4: 2}


def _curva_forca_bruta(jogos: list[int], pool: list[int]) -> dict[int, int]:
    """Definição ingênua independente, para conferência cruzada."""
    out = {}
    for p in range(len(pool) + 1):
        pior = None
        for combo in itertools.combinations(pool, p):
            alvo = para_bitmask(combo)
            melhor = max(acertos(j, alvo) for j in jogos)
            pior = melhor if pior is None else min(pior, melhor)
        out[p] = pior if pior is not None else 0
    return out


def test_curva_garantia_concorda_com_forca_bruta():
    pool = [3, 6, 9, 12, 15, 18]  # N=6
    jogos = [
        para_bitmask([3, 6, 9]),
        para_bitmask([12, 15, 18]),
        para_bitmask([3, 12, 15]),
    ]
    assert curva_garantia(jogos, pool) == _curva_forca_bruta(jogos, pool)


# ─── gerar_fechamento ────────────────────────────────────────────────────────────

def test_jogo_unico_cobre_pool_de_15():
    pool = list(range(1, 16))  # exatamente 15
    jogos = gerar_fechamento(pool, n_jogos=1)
    assert len(jogos) == 1
    assert sorted(jogos[0]) == pool
    masks = [para_bitmask(j) for j in jogos]
    assert curva_garantia(masks, pool)[15] == 15


def test_respeita_orcamento_e_pool():
    pool = list(range(1, 19))  # N=18
    jogos = gerar_fechamento(pool, n_jogos=8)
    assert len(jogos) == 8
    for j in jogos:
        assert len(j) == 15
        assert len(set(j)) == 15
        assert set(j) <= set(pool)


def test_monotonicidade_mais_jogos_nao_piora():
    pool = [1, 2, 3, 4, 5, 6]
    poucos = [para_bitmask(j) for j in gerar_fechamento(pool, n_jogos=2, tamanho_jogo=3)]
    muitos = [para_bitmask(j) for j in gerar_fechamento(pool, n_jogos=6, tamanho_jogo=3)]
    c_poucos = curva_garantia(poucos, pool)
    c_muitos = curva_garantia(muitos, pool)
    for p in c_poucos:
        assert c_muitos[p] >= c_poucos[p]


def test_garantia_atinge_alvo_quando_orcamento_suficiente():
    # pool 6, jogos de 3, alvo_p=3: cobrir todo 3-subconjunto com >=2 acertos
    # é possível; com orçamento folgado a curva em p=3 deve ser >= ... verificável.
    pool = [1, 2, 3, 4, 5, 6]
    jogos = [para_bitmask(j) for j in gerar_fechamento(pool, n_jogos=20, tamanho_jogo=3, alvo_p=3)]
    # com cobertura total de todos os 3-subconjuntos, g(3) == 3
    assert curva_garantia(jogos, pool)[3] == 3


def test_entrada_invalida():
    with pytest.raises(ValueError):
        gerar_fechamento([1, 2, 3], n_jogos=0)
    with pytest.raises(ValueError):
        gerar_fechamento(list(range(1, 19)), n_jogos=-1)
