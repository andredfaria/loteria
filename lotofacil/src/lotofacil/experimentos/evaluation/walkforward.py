"""Walk-forward temporal validation — model-agnostic, no data leakage."""

from __future__ import annotations

import logging
from typing import Callable, List

from lotofacil.experimentos.config import BACKTEST_MIN_TRAIN, BACKTEST_RETRAIN_EVERY

logger = logging.getLogger(__name__)


def walk_forward(
    draws: list,
    model_factory: Callable,
    n_test: int,
    retrain_every: int = BACKTEST_RETRAIN_EVERY,
    min_train: int = BACKTEST_MIN_TRAIN,
) -> List[dict]:
    """Walk-forward validation: train on past, predict next, never peek forward.

    Args:
        draws: All draws sorted chronologically.
        model_factory: Callable() → fresh BaseLabModel instance.
        n_test: Number of most-recent draws to use as the test window.
        retrain_every: Re-fit the model every N test draws (1 = maximum accuracy).
        min_train: Minimum draws required before first training.

    Returns:
        List of dicts: {concurso, predicted, actual, hits}
    """
    draws = sorted(draws, key=lambda d: d.concurso)
    total = len(draws)

    if total < min_train + n_test:
        n_test = max(1, total - min_train)
        logger.warning("Reduced n_test to %d (insufficient data)", n_test)

    test_draws = draws[-n_test:]
    results = []
    model = None
    last_train_idx = -1

    for step, test_draw in enumerate(test_draws):
        test_concurso = test_draw.concurso
        train_draws = [d for d in draws if d.concurso < test_concurso]

        if len(train_draws) < min_train:
            logger.debug("Skipping concurso %d (train=%d < %d)", test_concurso, len(train_draws), min_train)
            continue

        # Retrain when: first run, or every retrain_every steps
        needs_retrain = (model is None) or (step - last_train_idx >= retrain_every)
        if needs_retrain:
            model = model_factory()
            try:
                model.fit(train_draws)
                last_train_idx = step
                logger.debug("Retrained at step %d (concurso %d, train=%d)",
                             step, test_concurso, len(train_draws))
            except Exception as exc:
                logger.warning("Training failed for concurso %d: %s", test_concurso, exc)
                model = None
                continue

        try:
            predicted = model.predict(train_draws)
        except Exception as exc:
            logger.warning("Prediction failed for concurso %d: %s", test_concurso, exc)
            continue

        actual = test_draw.dezenas
        hits = len(set(predicted) & set(actual))

        results.append({
            "concurso": test_concurso,
            "predicted": predicted,
            "actual": list(actual),
            "hits": hits,
        })

    avg = sum(r["hits"] for r in results) / len(results) if results else 0
    logger.info(
        "Walk-forward done: model='%s' evaluated=%d avg_hits=%.2f",
        model.name if model else "?", len(results), avg,
    )
    return results
