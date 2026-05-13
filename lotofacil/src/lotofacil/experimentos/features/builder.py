"""ModularFeatureBuilder: assembles feature tensors from active blocks."""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import numpy as np

from lotofacil.experimentos.config import TOTAL_NUMBERS
from lotofacil.experimentos.data.feature_flags import FeatureConfig
from lotofacil.experimentos.features import (
    base as feat_base,
    temporal as feat_temporal,
    climate as feat_climate,
    lunar as feat_lunar,
    interactions as feat_interactions,
    strategy_priors as feat_priors,
)

logger = logging.getLogger(__name__)


class ModularFeatureBuilder:
    """Assembles feature sequences from activated blocks.

    Usage:
        builder = ModularFeatureBuilder(draws, config)
        X, y, meta = builder.build_sequences()
        # X: (n - window, window, n_features_active)
        # y: (n - window, 25) — next draw binary
        # meta: {"block_slices": {...}, "n_features": int, "n_samples": int}
    """

    def __init__(self, draws: list, config: FeatureConfig):
        self.draws = draws
        self.config = config
        self.n = len(draws)

    def build_sequences(self) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Build feature sequences and binary targets.

        Returns:
            X: (samples, window, n_features)
            y: (samples, 25)
            meta: dict with block_slices, n_features, n_samples, signature
        """
        cfg = self.config
        w = cfg.window_size
        draws = self.draws

        if self.n <= w:
            raise ValueError(
                f"Not enough draws: need >{w}, got {self.n}. "
                "Reduce window_size or load more data."
            )

        blocks: List[np.ndarray] = []
        block_slices: Dict[str, slice] = {}
        cursor = 0

        # ── Base history ──────────────────────────────────────────────────────
        if cfg.use_base_history:
            seq = feat_base.build_base_sequences(
                draws, w, freq_windows=cfg.freq_windows[:3]
            )
            # seq shape: (samples, window, 125)
            blocks.append(seq)
            block_slices["base"] = slice(cursor, cursor + feat_base.N_BASE_FEATURES)
            cursor += feat_base.N_BASE_FEATURES
            logger.debug("base: %d features", feat_base.N_BASE_FEATURES)

        # ── Temporal ─────────────────────────────────────────────────────────
        if cfg.use_temporal:
            seq = feat_temporal.build_temporal_sequences(draws, w)
            # seq shape: (samples, window, 4)
            blocks.append(seq)
            block_slices["temporal"] = slice(cursor, cursor + feat_temporal.N_TEMPORAL_FEATURES)
            cursor += feat_temporal.N_TEMPORAL_FEATURES
            logger.debug("temporal: %d features", feat_temporal.N_TEMPORAL_FEATURES)

        # ── Strategy priors ───────────────────────────────────────────────────
        if cfg.use_strategy_priors:
            seq = feat_priors.build_strategy_priors_sequences(draws, w)
            blocks.append(seq)
            block_slices["strategy_priors"] = slice(cursor, cursor + feat_priors.N_STRATEGY_FEATURES)
            cursor += feat_priors.N_STRATEGY_FEATURES
            logger.debug("strategy_priors: %d features", feat_priors.N_STRATEGY_FEATURES)

        # ── Climate ───────────────────────────────────────────────────────────
        climate_seq = None
        if cfg.use_climate:
            climate_seq = feat_climate.build_climate_sequences(draws, w)
            blocks.append(climate_seq)
            block_slices["climate"] = slice(cursor, cursor + feat_climate.N_CLIMATE_FEATURES)
            cursor += feat_climate.N_CLIMATE_FEATURES
            logger.debug("climate: %d features", feat_climate.N_CLIMATE_FEATURES)

        # ── Lunar ─────────────────────────────────────────────────────────────
        lunar_seq = None
        if cfg.use_lunar:
            lunar_seq = feat_lunar.build_lunar_sequences(draws, w)
            blocks.append(lunar_seq)
            block_slices["lunar"] = slice(cursor, cursor + feat_lunar.N_LUNAR_FEATURES)
            cursor += feat_lunar.N_LUNAR_FEATURES
            logger.debug("lunar: %d features", feat_lunar.N_LUNAR_FEATURES)

        # ── Interactions ──────────────────────────────────────────────────────
        if cfg.use_interactions:
            if climate_seq is None or lunar_seq is None:
                logger.warning(
                    "use_interactions=True requires use_climate=True AND use_lunar=True. "
                    "Skipping interactions block."
                )
            else:
                inter_seq = feat_interactions.build_interaction_sequences(climate_seq, lunar_seq)
                blocks.append(inter_seq)
                n_inter = feat_interactions.N_INTERACTION_FEATURES
                block_slices["interactions"] = slice(cursor, cursor + n_inter)
                cursor += n_inter
                logger.debug("interactions: %d features", n_inter)

        if not blocks:
            raise ValueError("No feature blocks selected. Set at least one use_* flag to True.")

        X = np.concatenate(blocks, axis=-1)

        # Build binary targets: next draw's presence
        binary_full = feat_base.binary_matrix(draws)  # (n, 25)
        y = binary_full[w:]  # (samples, 25)

        n_samples = X.shape[0]
        n_features = X.shape[2]
        assert y.shape[0] == n_samples, f"X/y length mismatch: {n_samples} vs {y.shape[0]}"

        meta = {
            "block_slices": block_slices,
            "n_features": n_features,
            "n_samples": n_samples,
            "window_size": w,
            "signature": cfg.signature(),
            "n_draws": self.n,
        }

        logger.info(
            "Built sequences: X=%s y=%s config='%s'",
            X.shape, y.shape, cfg.signature(),
        )
        return X, y, meta

    def build_for_prediction(self) -> np.ndarray:
        """Build a single-sample input tensor for the latest draw.

        Returns shape (1, window, n_features) — suitable for model.predict().
        """
        X, _, _ = self.build_sequences()
        return X[[-1]]
