"""Serviço de fechamento garantido (covering design por orçamento fixo).

Dado um pool de N dezenas (auto-sugerido + override manual) e um orçamento de B jogos
de 15, gera B jogos que maximizam a garantia de pior caso e reporta a curva de garantia
verificada exatamente.

Premissa honesta: o fechamento controla a *distribuição* de prêmios de uma aposta fixa,
não o valor esperado (que segue negativo). A garantia é condicional às dezenas do pool
serem sorteadas.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from lotofacil.infra.config import COST_PER_GAME, DADOS_DIR, JOGOS_DIR
from lotofacil.infra.dados.leitor import load_draws
from lotofacil.infra.geracao.pool_selector import selecionar_pool
from lotofacil.infra.geracao.wheel import curva_garantia, gerar_fechamento, para_bitmask

_NOTA_EV = (
    "O fechamento controla a DISTRIBUIÇÃO de prêmios de uma aposta fixa, não o valor "
    "esperado (que permanece negativo na Lotofácil). A garantia da curva é condicional: "
    "vale apenas para as dezenas do seu pool que forem efetivamente sorteadas."
)


@dataclass(frozen=True)
class ResultadoFechamento:
    concurso_alvo: int
    pool: list[int]
    jogos: list[list[int]]
    curva_garantia: dict[int, int]
    n_jogos: int
    custo_total: float = field(init=False)
    nota_ev: str = _NOTA_EV

    def __post_init__(self):
        object.__setattr__(self, "custo_total", self.n_jogos * COST_PER_GAME)


def gerar_fechamento_service(
    pool_size: int,
    n_jogos: int,
    fixar: Sequence[int] = (),
    excluir: Sequence[int] = (),
    alvo_p: Optional[int] = None,
    draws: Optional[Sequence] = None,
    dados_dir: Optional[Path] = None,
    salvar: bool = False,
    saida_dir: Optional[Path] = None,
) -> ResultadoFechamento:
    if draws is None:
        draws = load_draws(dados_dir or DADOS_DIR)
    if not draws:
        raise ValueError("Sem sorteios carregados; rode 'lotofacil dados atualizar'.")

    pool = selecionar_pool(draws, n=pool_size, fixar=fixar, excluir=excluir)
    jogos = gerar_fechamento(pool, n_jogos=n_jogos, alvo_p=alvo_p)
    masks = [para_bitmask(j) for j in jogos]
    curva = curva_garantia(masks, pool)
    concurso_alvo = max(d.concurso for d in draws) + 1

    resultado = ResultadoFechamento(
        concurso_alvo=concurso_alvo,
        pool=pool,
        jogos=jogos,
        curva_garantia=curva,
        n_jogos=n_jogos,
    )

    if salvar:
        destino = (saida_dir or JOGOS_DIR)
        destino.mkdir(parents=True, exist_ok=True)
        arq = destino / f"fechamento_{concurso_alvo}.json"
        arq.write_text(
            json.dumps(
                {
                    "concurso_alvo": concurso_alvo,
                    "pool": pool,
                    "jogos": jogos,
                    "curva_garantia": {str(k): v for k, v in curva.items()},
                    "n_jogos": n_jogos,
                    "custo_total": resultado.custo_total,
                    "nota_ev": resultado.nota_ev,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    return resultado
