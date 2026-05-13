from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from lotofacil.infra.config import DADOS_DIR
from lotofacil.infra.dados.leitor import load_draws
from lotofacil.infra.estrategias.onze_dezenas.predictor import ElevenNumbersStrategy


@dataclass(frozen=True)
class ResultadoPredicao:
    concurso_alvo: int
    dezenas: list[int]
    confianca_media: float
    estrategia: str
    abordagem: str


def gerar_predicao(
    dados_dir: Optional[Path] = None,
    abordagem: str = "all",
) -> ResultadoPredicao:
    dados_dir = dados_dir or DADOS_DIR
    draws = load_draws(dados_dir)
    strategy = ElevenNumbersStrategy()
    pred = strategy.predict(draws, approach=abordagem)
    return ResultadoPredicao(
        concurso_alvo=pred.concurso_alvo,
        dezenas=pred.dezenas,
        confianca_media=pred.confianca_media,
        estrategia=pred.strategy,
        abordagem=pred.abordagem,
    )
