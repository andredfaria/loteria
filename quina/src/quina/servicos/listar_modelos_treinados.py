from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from quina.infra.config import MODELOS_DIR


@dataclass(frozen=True)
class ResultadoListaModelos:
    modelos: list[dict]
    total: int


def listar_modelos_treinados(
    modelos_dir: Optional[Path] = None,
) -> ResultadoListaModelos:
    modelos_dir = modelos_dir or MODELOS_DIR
    modelos = []

    if (modelos_dir / "frequency_model.json").exists():
        modelos.append({"nome": "frequencia", "arquivo": "frequency_model.json"})
    if (modelos_dir / "frequency_ensemble.json").exists():
        modelos.append({"nome": "frequencia_ensemble", "arquivo": "frequency_ensemble.json"})
    if (modelos_dir / "probabilistic_model.json").exists():
        modelos.append({"nome": "probabilistico", "arquivo": "probabilistic_model.json"})
    if (modelos_dir / "ml_model.joblib").exists():
        modelos.append({"nome": "ml", "arquivo": "ml_model.joblib"})

    return ResultadoListaModelos(
        modelos=modelos,
        total=len(modelos),
    )