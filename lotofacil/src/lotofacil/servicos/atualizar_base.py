"""Atualização da base de sorteios com etapas automáticas pós-atualização.

Além de sincronizar os concursos com a API da Caixa, quando chegam concursos
novos o serviço valida automaticamente as predições pendentes e registra um
resumo PT-BR no log (ver `executar_pos_atualizacao`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from typing import Literal, Optional

from lotofacil.dominio.entidades import Sorteio
from lotofacil.infra.dados.api_caixa import LotofacilFetcher
from lotofacil.infra.dados.banco import DatabaseManager
from lotofacil.servicos.validar_predicoes import (
    ResultadoValidacaoPredicao,
    resumo_validacoes,
    validar_todas_pendentes,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultadoAtualizacao:
    total_novos: int
    ultimo_concurso: int
    sorteios_adicionados: list[Sorteio]
    validacoes: list[ResultadoValidacaoPredicao] = field(default_factory=list)


def _dict_para_sorteio(d: dict) -> Sorteio:
    return Sorteio(concurso=d["concurso"], data=d["data"], dezenas=d["dezenas"])


def _sincronizar(
    escopo: Literal["todos", "novos", "ultimo"],
    fetcher: LotofacilFetcher,
    db: DatabaseManager,
) -> ResultadoAtualizacao:
    if escopo == "ultimo":
        result = fetcher.fetch_latest()
        if result is None:
            ultimo = db.get_latest_concurso()
            return ResultadoAtualizacao(
                total_novos=0,
                ultimo_concurso=ultimo["concurso"] if ultimo else 0,
                sorteios_adicionados=[],
            )
        sorteio = _dict_para_sorteio(result)
        return ResultadoAtualizacao(
            total_novos=1,
            ultimo_concurso=sorteio.concurso,
            sorteios_adicionados=[sorteio],
        )

    if escopo == "novos":
        latest_before = db.get_latest_concurso()
        fetcher.sync_new_draws()
        all_concursos = db.get_all_concursos()
        if latest_before:
            novos = [c for c in all_concursos if c["concurso"] > latest_before["concurso"]]
        else:
            novos = all_concursos
        ultimo = db.get_latest_concurso()
        return ResultadoAtualizacao(
            total_novos=len(novos),
            ultimo_concurso=ultimo["concurso"] if ultimo else 0,
            sorteios_adicionados=[_dict_para_sorteio(c) for c in novos],
        )

    latest = fetcher.fetch_latest()
    if latest is None:
        return ResultadoAtualizacao(
            total_novos=0,
            ultimo_concurso=0,
            sorteios_adicionados=[],
        )
    api_max = latest["concurso"]
    novos: list[Sorteio] = []
    for num in range(1, api_max + 1):
        rec = fetcher.fetch_by_concurso(num)
        if rec:
            novos.append(_dict_para_sorteio(rec))
    ultimo = db.get_latest_concurso()
    return ResultadoAtualizacao(
        total_novos=len(novos),
        ultimo_concurso=ultimo["concurso"] if ultimo else 0,
        sorteios_adicionados=novos,
    )


def executar_pos_atualizacao(
    db: Optional[DatabaseManager] = None,
) -> list[ResultadoValidacaoPredicao]:
    """Executa as etapas automáticas após a chegada de concursos novos.

    Hoje a etapa é a validação das predições pendentes, com resumo PT-BR
    no log (ex.: "1 predição validada para o concurso 3701: 10 acertos").
    """
    db = db or DatabaseManager()
    validacoes = validar_todas_pendentes(db=db)
    if validacoes:
        logger.info(resumo_validacoes(validacoes))
    else:
        logger.info("Nenhuma predição pendente para validar")
    return validacoes


def atualizar_base(
    escopo: Literal["todos", "novos", "ultimo"] = "novos",
    validar: bool = True,
) -> ResultadoAtualizacao:
    """Sincroniza a base local de sorteios com a API da Caixa.

    Quando chegam concursos novos e `validar=True` (padrão), as predições
    pendentes são validadas automaticamente ao final da atualização — use
    `validar=False` (flag `--sem-validar` na CLI) para pular essa etapa.
    """
    fetcher = LotofacilFetcher()
    db = DatabaseManager()
    resultado = _sincronizar(escopo, fetcher, db)

    if not validar or resultado.total_novos == 0:
        return resultado

    validacoes = executar_pos_atualizacao(db=db)
    return replace(resultado, validacoes=validacoes)
