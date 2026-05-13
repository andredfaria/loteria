from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from lotofacil.infra.config import MODELOS_DIR, DADOS_DIR
from lotofacil.infra.dados.leitor import load_draws
from lotofacil.infra.modelos.frequency_model import FrequencyModel
from lotofacil.infra.modelos.frequency_ensemble import FrequencyEnsembleModel
from lotofacil.infra.modelos.probabilistic import ProbabilisticModel
from lotofacil.infra.modelos.ml_model import MLEnsembleModel
from lotofacil.infra.modelos.ensemble import EnsemblePredictor


@dataclass(frozen=True)
class ResultadoTreinamento:
    modelos_treinados: list[str]
    status: str
    total_concursos: int = 0
    detalhes: Optional[dict] = None


def treinar_modelos(
    dados_dir: Optional[Path] = None,
    modelos_dir: Optional[Path] = None,
) -> ResultadoTreinamento:
    dados_dir = dados_dir or DADOS_DIR
    modelos_dir = modelos_dir or MODELOS_DIR

    draws = load_draws(dados_dir)

    modelos_treinados: list[str] = []

    freq = FrequencyModel()
    freq.fit(draws)
    freq.save(modelos_dir)
    modelos_treinados.append(freq.name)

    freq_ens = FrequencyEnsembleModel()
    freq_ens.fit(draws)
    freq_ens.save(modelos_dir)
    modelos_treinados.append(freq_ens.name)

    prob = ProbabilisticModel()
    prob.fit(draws)
    prob.save(modelos_dir)
    modelos_treinados.append(prob.name)

    ml = MLEnsembleModel()
    ml.fit(draws)
    ml.save(modelos_dir)
    modelos_treinados.append(ml.name)

    ensemble = EnsemblePredictor(models_dir=modelos_dir)
    ensemble.fit(draws)
    ensemble.save()
    modelos_treinados.append(ensemble.name)

    return ResultadoTreinamento(
        modelos_treinados=modelos_treinados,
        status="sucesso",
        total_concursos=len(draws),
    )
