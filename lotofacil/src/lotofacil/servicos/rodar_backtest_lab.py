"""Backtest walk-forward de modelos neurais do lab, sem vazamento de dados.

Camada fina sobre ExperimentRunner: valida entradas vindas do dashboard,
traduz o intervalo de concursos escolhido pelo usuário para os parâmetros
que ExperimentRunner já entende (period_start/period_end/n_test) e devolve
o relatório pronto para exibição (comparação entre modelos + baselines).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from lotofacil.experimentos.config import BACKTEST_MIN_TRAIN, BACKTEST_RETRAIN_EVERY
from lotofacil.experimentos.data.draws_loader import load_draws
from lotofacil.experimentos.data.feature_flags import FeatureConfig
from lotofacil.experimentos.experiments.runner import ExperimentRunner

CONFIGS_CONHECIDAS = (
    "base+temp+priors",
    "base+temp+priors+lua",
    "base+temp+priors+clima",
    "base+temp+priors+lua+clima",
)


@dataclass(frozen=True)
class ResultadoBacktestLab:
    report: dict
    warnings: list[str] = field(default_factory=list)


def rodar_backtest_lab(
    configs: list[str],
    start_concurso: int,
    end_concurso: int,
    retrain_every: int = BACKTEST_RETRAIN_EVERY,
) -> ResultadoBacktestLab:
    """Roda walk-forward (treina em N, prevê N+1) para as configs dadas.

    Levanta ValueError para qualquer entrada inválida — nenhum treino é
    iniciado nesses casos.
    """
    if not configs:
        raise ValueError("Selecione ao menos uma config para o backtest.")

    invalidas = [c for c in configs if c not in CONFIGS_CONHECIDAS]
    if invalidas:
        raise ValueError(f"Configs inválidas: {', '.join(invalidas)}")

    if start_concurso >= end_concurso:
        raise ValueError(
            f"start_concurso ({start_concurso}) deve ser menor que end_concurso ({end_concurso})."
        )

    draws = load_draws()
    if not draws:
        raise ValueError("Nenhum dado histórico encontrado.")

    concursos = [d.concurso for d in draws]
    if end_concurso > concursos[-1]:
        raise ValueError(
            f"end_concurso ({end_concurso}) além do último concurso disponível ({concursos[-1]})."
        )

    start_idx = next((i for i, c in enumerate(concursos) if c >= start_concurso), len(concursos))
    if start_idx >= len(concursos):
        raise ValueError(f"start_concurso ({start_concurso}) além do intervalo de dados disponível.")

    warnings: list[str] = []
    effective_start = start_concurso
    if start_idx < BACKTEST_MIN_TRAIN:
        if BACKTEST_MIN_TRAIN >= len(concursos):
            raise ValueError(
                "Histórico insuficiente para qualquer backtest (mínimo: "
                f"{BACKTEST_MIN_TRAIN} concursos de treino)."
            )
        effective_start = concursos[BACKTEST_MIN_TRAIN]
        if effective_start > end_concurso:
            raise ValueError(
                f"Intervalo [{start_concurso}, {end_concurso}] não deixa "
                f"{BACKTEST_MIN_TRAIN} concursos de histórico antes do início."
            )
        warnings.append(
            f"Início ajustado de {start_concurso} para {effective_start} "
            f"(mínimo de {BACKTEST_MIN_TRAIN} concursos de treino)."
        )

    n_test = sum(1 for c in concursos if effective_start <= c <= end_concurso)
    feature_configs = [FeatureConfig.from_signature(sig) for sig in configs]

    runner = ExperimentRunner(draws)
    report = runner.run(
        n_test=n_test,
        retrain_every=retrain_every,
        configs=feature_configs,
        run_neural=True,
        period_end=end_concurso,
    )
    return ResultadoBacktestLab(report=report, warnings=warnings)
