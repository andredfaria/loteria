"""Predefined FeatureConfig grid for systematic ablation studies."""

from lotofacil_lab.data.feature_flags import FeatureConfig

# Ordered from simplest → richest so the runner can build on each layer
ABLATION_GRID = [
    FeatureConfig(
        use_base_history=True,
        use_temporal=False,
        use_climate=False,
        use_lunar=False,
        use_interactions=False,
        use_strategy_priors=False,
    ),
    FeatureConfig(
        use_base_history=True,
        use_temporal=True,
        use_climate=False,
        use_lunar=False,
        use_interactions=False,
        use_strategy_priors=False,
    ),
    FeatureConfig(
        use_base_history=True,
        use_temporal=True,
        use_climate=False,
        use_lunar=False,
        use_interactions=False,
        use_strategy_priors=True,
    ),
    FeatureConfig(
        use_base_history=True,
        use_temporal=True,
        use_climate=True,
        use_lunar=False,
        use_interactions=False,
        use_strategy_priors=True,
    ),
    FeatureConfig(
        use_base_history=True,
        use_temporal=True,
        use_climate=False,
        use_lunar=True,
        use_interactions=False,
        use_strategy_priors=True,
    ),
    FeatureConfig(
        use_base_history=True,
        use_temporal=True,
        use_climate=True,
        use_lunar=True,
        use_interactions=False,
        use_strategy_priors=True,
    ),
    FeatureConfig(
        use_base_history=True,
        use_temporal=True,
        use_climate=True,
        use_lunar=True,
        use_interactions=True,
        use_strategy_priors=True,
    ),
]
