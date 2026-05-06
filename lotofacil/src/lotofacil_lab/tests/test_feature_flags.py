"""Tests for FeatureConfig."""

import pytest
from lotofacil_lab.data.feature_flags import (
    FeatureConfig, MINIMAL, BASE, WITH_CLIMATE, WITH_LUNAR, FULL,
    FeatureConfig,
)


def test_defaults():
    cfg = FeatureConfig()
    assert cfg.use_base_history is True
    assert cfg.use_temporal is True
    assert cfg.use_strategy_priors is True
    assert cfg.use_climate is False
    assert cfg.use_lunar is False
    assert cfg.use_interactions is False
    assert cfg.window_size == 50
    assert cfg.target_numbers == 15


def test_signature_base():
    assert BASE.signature() == "base+temp+priors"


def test_signature_full():
    sig = FULL.signature()
    for part in ("base", "temp", "priors", "clima", "lua", "inter"):
        assert part in sig


def test_signature_minimal():
    assert MINIMAL.signature() == "base"


def test_from_signature_roundtrip():
    cfg = FeatureConfig(use_base_history=True, use_climate=True, use_lunar=True)
    sig = cfg.signature()
    restored = FeatureConfig.from_signature(sig)
    assert restored.use_base_history == cfg.use_base_history
    assert restored.use_climate == cfg.use_climate
    assert restored.use_lunar == cfg.use_lunar


def test_to_dict_serializable():
    import json
    d = BASE.to_dict()
    json.dumps(d)  # must not raise


def test_from_dict_roundtrip():
    d = FULL.to_dict()
    restored = FeatureConfig.from_dict(d)
    assert restored == FULL


def test_frozen():
    cfg = FeatureConfig()
    with pytest.raises((TypeError, AttributeError)):
        cfg.use_climate = True  # frozen dataclass


def test_predefined_configs_differ():
    assert BASE != FULL
    assert MINIMAL != BASE
