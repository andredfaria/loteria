"""Tests for ModularFeatureBuilder."""

import numpy as np
import pytest

from lotofacil.experimentos.data.feature_flags import FeatureConfig, MINIMAL, BASE, WITH_LUNAR
from lotofacil.experimentos.features.builder import ModularFeatureBuilder


_W = 10  # window_size for all builder tests (sample_draws has 50 draws)


def _cfg(**kw):
    """Helper: build FeatureConfig with window_size=10 and explicit flags."""
    defaults = dict(use_base_history=True, use_temporal=False,
                    use_strategy_priors=False, use_climate=False,
                    use_lunar=False, use_interactions=False, window_size=_W)
    defaults.update(kw)
    return FeatureConfig(**defaults)


def test_base_only_shape(sample_draws):
    cfg = _cfg()
    builder = ModularFeatureBuilder(sample_draws, cfg)
    X, y, meta = builder.build_sequences()
    assert X.shape[0] == len(sample_draws) - _W
    assert X.shape[1] == _W
    assert X.shape[2] == meta["n_features"]
    assert y.shape == (X.shape[0], 25)


def test_base_plus_temporal_larger(sample_draws):
    base_cfg = _cfg()
    full_cfg = _cfg(use_temporal=True)
    _, _, meta_base = ModularFeatureBuilder(sample_draws, base_cfg).build_sequences()
    _, _, meta_full = ModularFeatureBuilder(sample_draws, full_cfg).build_sequences()
    assert meta_full["n_features"] > meta_base["n_features"]


def test_lunar_block_adds_features(sample_draws):
    base_cfg = _cfg()
    lunar_cfg = _cfg(use_lunar=True)
    _, _, meta_base = ModularFeatureBuilder(sample_draws, base_cfg).build_sequences()
    _, _, meta_lunar = ModularFeatureBuilder(sample_draws, lunar_cfg).build_sequences()
    assert meta_lunar["n_features"] == meta_base["n_features"] + 7  # N_LUNAR_FEATURES=7


def test_block_slices_coverage(sample_draws):
    cfg = _cfg(use_temporal=True, use_strategy_priors=True)
    builder = ModularFeatureBuilder(sample_draws, cfg)
    X, _, meta = builder.build_sequences()
    slices = meta["block_slices"]
    covered = set()
    for sl in slices.values():
        covered.update(range(sl.start, sl.stop))
    assert covered == set(range(meta["n_features"]))


def test_y_is_binary(sample_draws):
    builder = ModularFeatureBuilder(sample_draws, _cfg())
    _, y, _ = builder.build_sequences()
    assert np.all((y == 0) | (y == 1))


def test_y_has_15_per_row(sample_draws):
    builder = ModularFeatureBuilder(sample_draws, _cfg())
    _, y, _ = builder.build_sequences()
    assert np.all(y.sum(axis=1) == 15)


def test_signature_in_meta(sample_draws):
    cfg = _cfg(use_temporal=True, use_strategy_priors=True)
    builder = ModularFeatureBuilder(sample_draws, cfg)
    _, _, meta = builder.build_sequences()
    assert meta["signature"] == cfg.signature()


def test_too_few_draws_raises(minimal_draws):
    """Window larger than draw count should raise ValueError."""
    cfg = FeatureConfig(window_size=100)
    with pytest.raises(ValueError, match="Not enough draws"):
        ModularFeatureBuilder(minimal_draws, cfg).build_sequences()


def test_build_for_prediction_shape(sample_draws):
    cfg = _cfg()
    builder = ModularFeatureBuilder(sample_draws, cfg)
    x = builder.build_for_prediction()
    assert x.shape[0] == 1
    assert x.shape[1] == _W
