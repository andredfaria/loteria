from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from quina.infra.config import DADOS_DIR, MODELOS_DIR
from quina.infra.dados.leitor import load_draws
from quina.infra.modelos.ensemble import EnsemblePredictor


@dataclass(frozen=True)
class ResultadoPredicao:
    concurso_alvo: int
    dezenas: list[int]
    confianca_media: float
    probabilidades: list[float]


def gerar_predicao(
    dados_dir: Optional[Path] = None,
    modelos_dir: Optional[Path] = None,
) -> ResultadoPredicao:
    dados_dir = dados_dir or DADOS_DIR
    modelos_dir = modelos_dir or MODELOS_DIR

    draws = load_draws(dados_dir)
    ultimo_concurso = draws[-1].concurso
    concurso_alvo = ultimo_concurso + 1

    predictor = EnsemblePredictor(models_dir=modelos_dir)
    predictor.load()

    probas = predictor.predict_proba()
    dezenas = predictor.select_top_5()
    confianca = float(probas[[d - 1 for d in dezenas]].mean())

    return ResultadoPredicao(
        concurso_alvo=concurso_alvo,
        dezenas=dezenas,
        confianca_media=round(confianca, 4),
        probabilidades=[round(float(probas[n - 1]), 4) for n in sorted(dezenas)],
    )