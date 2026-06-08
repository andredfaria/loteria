"""Testes da seleção de pool de dezenas (refino marginal, não previsão)."""
from __future__ import annotations

import pytest

from lotofacil.infra.dados.leitor import Draw
from lotofacil.infra.geracao.pool_selector import selecionar_pool


def _draws():
    # histórico sintético determinístico
    base = [
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16],
        [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17],
        [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 2, 4],
    ]
    return [Draw(concurso=i + 1, data="2026-01-01", dezenas=sorted(d)) for i, d in enumerate(base)]


def test_tamanho_e_dominio():
    pool = selecionar_pool(_draws(), n=18)
    assert len(pool) == 18
    assert len(set(pool)) == 18
    assert all(1 <= d <= 25 for d in pool)
    assert pool == sorted(pool)


def test_fixar_sempre_presente():
    pool = selecionar_pool(_draws(), n=18, fixar=[20, 22, 24])
    assert {20, 22, 24} <= set(pool)


def test_excluir_nunca_presente():
    pool = selecionar_pool(_draws(), n=18, excluir=[1, 2, 3])
    assert not ({1, 2, 3} & set(pool))


def test_deterministico():
    a = selecionar_pool(_draws(), n=17)
    b = selecionar_pool(_draws(), n=17)
    assert a == b


def test_fixar_e_excluir_juntos():
    pool = selecionar_pool(_draws(), n=16, fixar=[25], excluir=[1])
    assert 25 in pool and 1 not in pool and len(pool) == 16


def test_validacao():
    with pytest.raises(ValueError):
        selecionar_pool(_draws(), n=14)            # < 15
    with pytest.raises(ValueError):
        selecionar_pool(_draws(), n=26)            # > 25
    with pytest.raises(ValueError):
        selecionar_pool(_draws(), n=18, fixar=[5], excluir=[5])  # interseção
    with pytest.raises(ValueError):
        selecionar_pool(_draws(), n=16, fixar=list(range(1, 18)))  # fixar > n
