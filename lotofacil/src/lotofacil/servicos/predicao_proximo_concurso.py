"""Predição consolidada do próximo concurso da Lotofácil.

Reúne em um único resultado: qual é o próximo concurso, quando ele deve
ocorrer, e quais dezenas o sistema recomenda — sempre acompanhado do
baseline aleatório para honestidade estatística.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np

from lotofacil.infra.config import DADOS_DIR, NUMEROS_POR_SORTEIO
from lotofacil.infra.dados.leitor import load_draws
from lotofacil.infra.estrategias.onze_dezenas.predictor import ElevenNumbersStrategy

logger = logging.getLogger(__name__)

# Acertos esperados de 15 dezenas escolhidas ao acaso (hipergeométrico: 15*15/25)
BASELINE_ACERTOS_ESPERADO = 9.0

_ABORDAGEM_PARA_APPROACH = {
    "ensemble": "all",
    "todas": "all",
    "all": "all",
    "statistical": "statistical",
    "estatistica": "statistical",
    "ml": "ml",
    "neural": "neural",
}


@dataclass(frozen=True)
class PredicaoProximoConcurso:
    concurso_alvo: int
    data_prevista: str
    dezenas: list[int]
    confianca_por_dezena: dict[int, float]
    confianca_media: float
    modelo: str
    abordagem: str
    baseline_esperado: float
    gerado_em: str


def _proxima_data_sorteio(ultima_data: str) -> str:
    """Lotofácil sorteia de segunda a sábado; calcula a próxima data útil."""
    try:
        dt = datetime.strptime(ultima_data, "%d/%m/%Y")
    except ValueError:
        dt = datetime.now()
    proxima = dt + timedelta(days=1)
    while proxima.weekday() == 6:  # domingo: sem sorteio
        proxima += timedelta(days=1)
    return proxima.strftime("%d/%m/%Y")


def gerar_predicao_proximo_concurso(
    dados_dir: Optional[Path] = None,
    n_dezenas: int = NUMEROS_POR_SORTEIO,
    abordagem: str = "ensemble",
    modelo_nome: Optional[str] = None,
) -> PredicaoProximoConcurso:
    """Gera a predição para o próximo concurso ainda não sorteado.

    `draws` contém apenas concursos já realizados — o concurso alvo
    (`draws[-1].concurso + 1`) nunca é usado como entrada (sem vazamento).
    """
    dados_dir = dados_dir or DADOS_DIR
    draws = load_draws(dados_dir)
    if not draws:
        raise ValueError("Sem sorteios carregados — execute 'lotofacil dados atualizar'")

    ultimo = draws[-1]
    concurso_alvo = ultimo.concurso + 1
    data_prevista = _proxima_data_sorteio(ultimo.data)

    approach = _ABORDAGEM_PARA_APPROACH.get(abordagem, "all")
    strategy = ElevenNumbersStrategy()
    pred = strategy.predict(draws, approach=approach)

    probas = np.array(pred.probabilidades, dtype=np.float64)
    indices = np.argsort(probas)[::-1][:n_dezenas]
    dezenas = sorted((indices + 1).tolist())
    confianca_por_dezena = {int(d): round(float(probas[d - 1]), 4) for d in dezenas}
    confianca_media = float(np.mean([probas[d - 1] for d in dezenas])) if dezenas else 0.0

    return PredicaoProximoConcurso(
        concurso_alvo=concurso_alvo,
        data_prevista=data_prevista,
        dezenas=dezenas,
        confianca_por_dezena=confianca_por_dezena,
        confianca_media=round(confianca_media, 4),
        modelo=modelo_nome or pred.abordagem,
        abordagem=pred.abordagem,
        baseline_esperado=BASELINE_ACERTOS_ESPERADO,
        gerado_em=datetime.now().isoformat(),
    )
