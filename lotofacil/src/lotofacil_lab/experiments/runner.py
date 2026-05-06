"""ExperimentRunner: orchestrates ablation study across multiple FeatureConfigs."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, List

from lotofacil_lab.config import BACKTEST_MIN_TRAIN, BACKTEST_RETRAIN_EVERY, RANDOM_SEED
from lotofacil_lab.data.feature_flags import FeatureConfig
from lotofacil_lab.evaluation.metrics import financial_metrics, vs_random_p_value
from lotofacil_lab.evaluation.walkforward import walk_forward
from lotofacil_lab.experiments.ablation_grid import ABLATION_GRID
from lotofacil_lab.models.baseline_frequency import FrequencyBaseline
from lotofacil_lab.models.baseline_random import RandomBaseline
from lotofacil_lab.models.neural_modular import NeuralModular

logger = logging.getLogger(__name__)


class ExperimentRunner:
    """Runs walk-forward evaluation for baselines + multiple FeatureConfigs.

    Usage:
        runner = ExperimentRunner(draws)
        report = runner.run(n_test=100, retrain_every=50)
    """

    def __init__(
        self,
        draws: list,
        min_train: int = BACKTEST_MIN_TRAIN,
        seed: int = RANDOM_SEED,
    ):
        self.draws = sorted(draws, key=lambda d: d.concurso)
        self.min_train = min_train
        self.seed = seed

    def run(
        self,
        n_test: int = 100,
        retrain_every: int = BACKTEST_RETRAIN_EVERY,
        configs: List[FeatureConfig] | None = None,
        run_neural: bool = True,
        period_start: int | None = None,
        period_end: int | None = None,
    ) -> dict:
        """Run the full experiment.

        Args:
            n_test: Number of draws in the test window.
            retrain_every: Retrain every N steps in walk-forward.
            configs: Feature configs to test. Defaults to ABLATION_GRID.
            run_neural: If False, skips neural configs (fast smoke test).
            period_start: First concurso for period filter (optional).
            period_end: Last concurso for period filter (optional).

        Returns:
            Report dict with all config results, sorted by mean_hits desc.
        """
        draws = self._filter_period(period_start, period_end)
        if not draws:
            raise ValueError("No draws in selected period.")

        configs = configs if configs is not None else ABLATION_GRID
        started_at = datetime.now().isoformat()

        report: dict = {
            "started_at": started_at,
            "n_test": n_test,
            "retrain_every": retrain_every,
            "n_draws_total": len(draws),
            "results": [],
        }

        # ── Random baseline ───────────────────────────────────────────────────
        logger.info("Running random baseline...")
        random_results = self._run_random_baseline(draws, n_test)
        random_entry = self._summarise("random", random_results)
        report["results"].append(random_entry)

        # ── Frequency baseline ────────────────────────────────────────────────
        logger.info("Running frequency baseline...")
        freq_results = walk_forward(
            draws,
            model_factory=lambda: FrequencyBaseline(),
            n_test=n_test,
            retrain_every=retrain_every,
            min_train=self.min_train,
        )
        report["results"].append(self._summarise("frequency", freq_results))

        # ── Neural configs ────────────────────────────────────────────────────
        if run_neural:
            for cfg in configs:
                logger.info("Running neural config: %s", cfg.signature())
                try:
                    entry = self._run_neural_config(cfg, draws, n_test, retrain_every)
                    report["results"].append(entry)
                except Exception as exc:
                    logger.error("Config '%s' failed: %s", cfg.signature(), exc)
                    report["results"].append({
                        "name": f"neural_{cfg.signature()}",
                        "error": str(exc),
                    })

        # Sort by mean_hits descending (skip error entries)
        report["results"].sort(
            key=lambda e: e.get("mean_hits", -1), reverse=True
        )
        report["finished_at"] = datetime.now().isoformat()
        return report

    # ── Private helpers ───────────────────────────────────────────────────────

    def _filter_period(self, start: int | None, end: int | None) -> list:
        if start is None and end is None:
            return self.draws
        return [
            d for d in self.draws
            if (start is None or d.concurso >= start)
            and (end is None or d.concurso <= end)
        ]

    def _run_random_baseline(self, draws: list, n_test: int) -> list:
        """Generate one random game per test draw — no training needed."""
        test_draws = draws[-n_test:] if len(draws) >= n_test else draws
        model = RandomBaseline(seed=self.seed)
        results = []
        for test_draw in test_draws:
            predicted = model.predict([])
            actual = test_draw.dezenas
            hits = len(set(predicted) & set(actual))
            results.append({"concurso": test_draw.concurso, "predicted": predicted,
                             "actual": list(actual), "hits": hits})
        return results

    def _run_neural_config(
        self, cfg: FeatureConfig, draws: list, n_test: int, retrain_every: int
    ) -> dict:
        results = walk_forward(
            draws,
            model_factory=lambda: NeuralModular(cfg),
            n_test=n_test,
            retrain_every=retrain_every,
            min_train=self.min_train,
        )
        return self._summarise(f"neural_{cfg.signature()}", results)

    def _summarise(self, name: str, results: list) -> dict:
        if not results:
            return {"name": name, "n_evaluated": 0}
        hits_list = [r["hits"] for r in results]
        fin = financial_metrics(results)
        p_val = vs_random_p_value(hits_list)
        return {
            "name": name,
            "n_evaluated": len(results),
            "mean_hits": fin.get("mean_hits", 0),
            "roi_pct": fin.get("roi_pct", 0),
            "sharpe": fin.get("sharpe", 0),
            "max_drawdown": fin.get("max_drawdown", 0),
            "p_value_vs_random": p_val,
            "rate_ge_11": fin.get("rate_ge_11", 0),
            "rate_ge_13": fin.get("rate_ge_13", 0),
            "hits_distribution": fin.get("hits_distribution", {}),
            "equity_curve": fin.get("equity_curve", []),
            "raw_results": results,
        }
