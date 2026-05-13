"""ValidationSuite: walk-forward KPI computation for BaseModel instances."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

from lotofacil.infra.avaliacao.backtest import BacktestEngine
from lotofacil.infra.config import BACKTEST_DEFAULT_N, BACKTEST_MIN_TRAIN, BACKTEST_TRAIN_WINDOW
from lotofacil.dominio.entidades import Sorteio as Draw
from lotofacil.infra.avaliacao.confusion import confusion_by_hits, confusion_per_number
from lotofacil.infra.avaliacao.metricas import (
    LotofacilMetrics,
    mae_expected_hits,
    rmse_expected_hits,
    roc_auc_per_number,
)
from lotofacil.infra.modelos.base_model import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class ModelReport:
    model_name: str
    mean_hits: float = 0.0
    rmse: float = 0.0
    mae: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    accuracy: float = 0.0
    roc_auc_mean: float = 0.5
    roc_auc_std: float = 0.0
    confusion_aggregate: dict = field(default_factory=dict)
    hit_distribution: dict = field(default_factory=dict)
    vs_random: dict = field(default_factory=dict)
    n_evaluated: int = 0


class ValidationSuite:
    """
    Compute comprehensive KPIs for a set of BaseModel instances.

    Uses BacktestEngine with capture_probas=True so KPIs have raw probability access.
    Each model is evaluated independently via walk-forward backtest.
    """

    def run(
        self,
        draws: List[Draw],
        models: Dict[str, BaseModel],
        n_backtest: int = BACKTEST_DEFAULT_N,
    ) -> Dict[str, ModelReport]:
        """
        Args:
            draws: full sorted draw history (List[Draw])
            models: {name: model_instance} — each model is trained and evaluated
            n_backtest: number of most recent draws to use as test window

        Returns:
            {model_name: ModelReport}

        Raises:
            ValueError: if there is not enough data for training
        """
        n = len(draws)
        n_test = min(n_backtest, n - BACKTEST_MIN_TRAIN)
        if n_test <= 0:
            raise ValueError(
                f"Not enough draws: {n} total, need at least {BACKTEST_MIN_TRAIN + 1} "
                f"for training (BACKTEST_MIN_TRAIN={BACKTEST_MIN_TRAIN})"
            )

        test_start_idx = n - n_test
        reports: Dict[str, ModelReport] = {}

        for model_name, model in models.items():
            logger.info("ValidationSuite: running backtest for '%s' (%d test draws)", model_name, n_test)
            engine = BacktestEngine(
                model,
                train_window=min(BACKTEST_TRAIN_WINDOW, test_start_idx),
                retrain_every=50,
                min_train=BACKTEST_MIN_TRAIN,
            )
            bt_results = engine.run(draws, start_idx=test_start_idx, capture_probas=True)

            if not bt_results:
                logger.warning("ValidationSuite: no results for model '%s'", model_name)
                continue

            # Convert BacktestResult → dict format expected by KPI functions
            result_dicts = [
                {
                    "predicted": r.jogo,
                    "actual": r.resultado,
                    "hits": r.hits,
                    "probas": r.probas,
                }
                for r in bt_results
            ]

            cm = confusion_per_number(result_dicts)
            hits_cm = confusion_by_hits(result_dicts)
            auc = roc_auc_per_number(result_dicts)

            reports[model_name] = ModelReport(
                model_name=model_name,
                mean_hits=LotofacilMetrics.mean_accuracy(result_dicts),
                rmse=rmse_expected_hits(result_dicts),
                mae=mae_expected_hits(result_dicts),
                precision=cm["precision"],
                recall=cm["recall"],
                f1=cm["f1"],
                accuracy=cm["accuracy"],
                roc_auc_mean=auc["mean"],
                roc_auc_std=auc["std"],
                confusion_aggregate=cm["aggregate"],
                hit_distribution=hits_cm["actual_distribution"],
                vs_random=LotofacilMetrics.vs_random_baseline(result_dicts, n_simulations=200),
                n_evaluated=len(bt_results),
            )

        return reports
