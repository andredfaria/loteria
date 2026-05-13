"""Predictor for the 15-numbers strategy (target: 11+ hits)."""

from __future__ import annotations

from typing import List

from lotofacil.dominio.entidades import Draw


class QuinzePredictor:
    """Orchestrator for 15-number predictions."""

    def __init__(self, use_ensemble: bool = True):
        self._neural = None
        self._ensemble = None
        self._use_ensemble = use_ensemble

    def _get_ensemble(self):
        if self._ensemble is None:
            from lotofacil.infra.estrategias.quinze_dezenas.approaches.ensemble import EnsembleApproach
            self._ensemble = EnsembleApproach()
        return self._ensemble

    def _get_neural(self):
        if self._neural is None:
            from lotofacil.infra.estrategias.quinze_dezenas.approaches.neural import NeuralApproach
            self._neural = NeuralApproach()
        return self._neural

    def predict(self, draws: List[Draw], use_filters: bool = True) -> List[int]:
        """Predict 15 numbers for the next draw."""
        if self._use_ensemble:
            ensemble = self._get_ensemble()
            ensemble.fit(draws)
            if use_filters:
                return ensemble.predict_with_filters(draws)
            else:
                import numpy as np
                probas = ensemble.predict_proba()
                return sorted(np.argsort(probas)[::-1][:15] + 1)
        else:
            neural = self._get_neural()
            neural.fit(draws)
            if use_filters:
                return neural.predict_with_filters(draws)
            else:
                import numpy as np
                probas = neural.predict_proba()
                return sorted(np.argsort(probas)[::-1][:15] + 1)

    def predict_loaded(self, draws: List[Draw], use_filters: bool = True,
                        use_ensemble: bool | None = None) -> List[int]:
        """Predict using pre-trained model (no retraining)."""
        if use_ensemble is None:
            use_ensemble = self._use_ensemble

        if use_ensemble:
            ensemble = self._get_ensemble()
            ensemble.load()
            if use_filters:
                return ensemble.predict_with_filters(draws)
            else:
                import numpy as np
                probas = ensemble.predict_proba()
                return sorted(np.argsort(probas)[::-1][:15] + 1)
        else:
            neural = self._get_neural()
            neural.load()
            if use_filters:
                return neural.predict_with_filters(draws)
            else:
                import numpy as np
                probas = neural.predict_proba(draws)
                return sorted(np.argsort(probas)[::-1][:15] + 1)
