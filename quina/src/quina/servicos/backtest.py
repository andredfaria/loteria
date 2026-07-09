"""Backtest walk-forward de estratégias contra o histórico real da Quina."""
from __future__ import annotations

import random
import time
from typing import Optional

from quina.dominio.regras import FAIXAS_ACERTOS, NUMEROS_POR_SORTEIO, TOTAL_NUMEROS
from quina.infra.dados.banco import DatabaseManager
from quina.servicos.estrategias import scoring
from quina.servicos.estrategias.frequencia_atraso import gerar_candidato_frequencia_atraso

ESTRATEGIAS_DISPONIVEIS = ("filtros", "frequencia_atraso")

_CANDIDATOS_POR_RODADA = 100


def _gerar_candidato(estrategia: str, historico: list[dict]) -> list[int]:
    if estrategia == "filtros":
        candidatos = scoring.gerar_candidatos(
            quantidade=_CANDIDATOS_POR_RODADA, tamanho_aposta=NUMEROS_POR_SORTEIO, draws=historico
        )
        return candidatos[0]["dezenas"]
    return gerar_candidato_frequencia_atraso(historico, NUMEROS_POR_SORTEIO)["dezenas"]


def rodar_backtest(
    estrategia: str,
    janela: int = 300,
    draws: Optional[list[dict]] = None,
    db: Optional[DatabaseManager] = None,
) -> dict:
    if estrategia not in ESTRATEGIAS_DISPONIVEIS:
        raise ValueError(f"estratégia desconhecida: {estrategia}")

    todos = draws if draws is not None else (db or DatabaseManager()).get_all_concursos()
    if len(todos) < 2:
        raise ValueError("dados insuficientes para backtest (mínimo 2 concursos)")

    janela_efetiva = min(janela, len(todos) - 1)
    inicio = len(todos) - janela_efetiva

    contagem_estrategia = {f: 0 for f in FAIXAS_ACERTOS}
    contagem_baseline = {f: 0 for f in FAIXAS_ACERTOS}

    inicio_tempo = time.monotonic()
    for i in range(inicio, len(todos)):
        historico = todos[:i]
        resultado_real = set(todos[i]["dezenas"])

        candidato_estrategia = set(_gerar_candidato(estrategia, historico))
        candidato_baseline = set(random.sample(range(1, TOTAL_NUMEROS + 1), NUMEROS_POR_SORTEIO))

        acertos_estrategia = len(candidato_estrategia & resultado_real)
        acertos_baseline = len(candidato_baseline & resultado_real)
        if acertos_estrategia in contagem_estrategia:
            contagem_estrategia[acertos_estrategia] += 1
        if acertos_baseline in contagem_baseline:
            contagem_baseline[acertos_baseline] += 1
    tempo_execucao = round(time.monotonic() - inicio_tempo, 3)

    total_rodadas = len(todos) - inicio
    return {
        "janela": janela_efetiva,
        "total_rodadas": total_rodadas,
        "taxa_estrategia": {str(f): contagem_estrategia[f] / total_rodadas for f in FAIXAS_ACERTOS},
        "taxa_baseline": {str(f): contagem_baseline[f] / total_rodadas for f in FAIXAS_ACERTOS},
        "tempo_execucao_segundos": tempo_execucao,
    }
