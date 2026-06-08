"""Testes do serviço de fechamento garantido."""
from __future__ import annotations

import json

from lotofacil.infra.dados.leitor import Draw
from lotofacil.infra.geracao.wheel import curva_garantia, para_bitmask
from lotofacil.servicos.gerar_fechamento import (
    ResultadoFechamento,
    gerar_fechamento_service,
)

COST_PER_GAME = 3.50


def _draws():
    base = [
        list(range(1, 16)),
        list(range(2, 17)),
        list(range(3, 18)),
        [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 2, 4],
    ]
    return [Draw(concurso=100 + i, data="2026-01-01", dezenas=sorted(d)) for i, d in enumerate(base)]


def test_resultado_basico():
    r = gerar_fechamento_service(pool_size=18, n_jogos=8, draws=_draws())
    assert isinstance(r, ResultadoFechamento)
    assert r.n_jogos == 8
    assert len(r.jogos) == 8
    assert len(r.pool) == 18
    assert r.concurso_alvo == 104  # último (103) + 1
    assert r.custo_total == 8 * COST_PER_GAME


def test_override_respeitado():
    r = gerar_fechamento_service(
        pool_size=18, n_jogos=6, fixar=[20, 22], excluir=[1, 2], draws=_draws()
    )
    assert {20, 22} <= set(r.pool)
    assert not ({1, 2} & set(r.pool))


def test_curva_bate_com_verificador():
    r = gerar_fechamento_service(pool_size=17, n_jogos=10, draws=_draws())
    masks = [para_bitmask(j) for j in r.jogos]
    assert r.curva_garantia == curva_garantia(masks, r.pool)
    # monotonicidade da curva
    valores = [r.curva_garantia[p] for p in sorted(r.curva_garantia)]
    assert valores == sorted(valores)


def test_nota_ev_honesta():
    r = gerar_fechamento_service(pool_size=16, n_jogos=4, draws=_draws())
    assert r.nota_ev
    assert "esperado" in r.nota_ev.lower()


def test_salva_json_quando_pedido(tmp_path):
    r = gerar_fechamento_service(
        pool_size=16, n_jogos=4, draws=_draws(), salvar=True, saida_dir=tmp_path
    )
    arq = tmp_path / f"fechamento_{r.concurso_alvo}.json"
    assert arq.exists()
    dados = json.loads(arq.read_text())
    assert dados["n_jogos"] == 4
    assert len(dados["jogos"]) == 4
