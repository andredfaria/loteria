"""Walk-forward validation for the ensemble predictor."""

import logging
from typing import List

from lotofacil_ml.config import BACKTEST_DEFAULT_N, LSTM_WINDOW_SIZE
from lotofacil_ml.models.ensemble import EnsemblePredictor

logger = logging.getLogger(__name__)


class WalkForwardValidator:
    """
    For each of the last n draws: train on all prior draws, predict, compare.
    This is proper out-of-sample evaluation with no data leakage.
    """

    def __init__(self, draws: List[dict]):
        self.draws = sorted(draws, key=lambda d: d["concurso"])

    def walk_forward_validation(self, n_last: int = BACKTEST_DEFAULT_N) -> List[dict]:
        """
        Args:
            n_last: number of most recent draws to use as test set
        Returns:
            list of {concurso, predicted, actual, hits}
        """
        total = len(self.draws)
        min_train = LSTM_WINDOW_SIZE + 50  # minimum draws needed to train

        if total < min_train + n_last:
            n_last = max(1, total - min_train)
            logger.warning("Reduced n_last to %d (insufficient data)", n_last)

        results = []
        test_draws = self.draws[-(n_last):]

        for idx, test_draw in enumerate(test_draws):
            test_concurso = test_draw["concurso"]
            train_draws = [d for d in self.draws if d["concurso"] < test_concurso]

            if len(train_draws) < min_train:
                logger.debug("Skipping concurso %d (too little training data)", test_concurso)
                continue

            logger.debug(
                "Walk-forward %d/%d: training on %d draws, predicting concurso %d",
                idx + 1, n_last, len(train_draws), test_concurso,
            )

            predictor = EnsemblePredictor()
            try:
                predictor.train(train_draws)
                pred = predictor.predict_next_concurso(train_draws)
                predicted = pred["dezenas_sugeridas"]
            except Exception as exc:
                logger.warning("Prediction failed for concurso %d: %s", test_concurso, exc)
                continue

            actual = test_draw["dezenas"]
            hits = len(set(predicted) & set(actual))

            results.append({
                "concurso": test_concurso,
                "predicted": predicted,
                "actual": actual,
                "hits": hits,
            })

        logger.info(
            "Walk-forward complete: %d evaluated, avg hits=%.2f",
            len(results),
            sum(r["hits"] for r in results) / len(results) if results else 0,
        )
        return results
