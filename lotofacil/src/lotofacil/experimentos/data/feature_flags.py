"""FeatureConfig: dataclass that controls which feature blocks are active."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json


@dataclass(frozen=True)
class FeatureConfig:
    """Controls which feature blocks are included in the modular pipeline.

    Each block maps to a contiguous slice in the feature tensor's last axis.
    Set a flag to False to exclude the block entirely (ablation study).
    """

    # ── Feature blocks ──────────────────────────────────────────────────────────
    use_base_history: bool = True
    """Binary presence + sliding frequencies + days-since-last (per number)."""

    use_temporal: bool = True
    """Cyclic sin/cos encoding of day-of-week and month."""

    use_climate: bool = False
    """8 normalised climate features at draw time (Open-Meteo)."""

    use_lunar: bool = False
    """7 lunar features at draw time (pylunar offline)."""

    use_interactions: bool = False
    """Cross-products: climate × lunar, climate × base. Requires climate+lunar."""

    use_strategy_priors: bool = True
    """8 scalars: conformity of recent draws to the statistical hierarchy."""

    # ── Hyperparameters ─────────────────────────────────────────────────────────
    window_size: int = 50
    """Number of past draws fed as LSTM time-steps."""

    freq_windows: tuple = (5, 10, 30, 100)
    """Rolling windows used to compute number frequencies."""

    atraso_norm: float = 50.0
    """Divisor for days-since-last normalisation."""

    # ── Target strategy ─────────────────────────────────────────────────────────
    target_numbers: int = 15
    """How many numbers to select (15 = jogo oficial, 11 = portfolio core)."""

    def signature(self) -> str:
        """Short ID for naming runs/files. Example: 'base+temp+priors+clima'."""
        parts = []
        if self.use_base_history:
            parts.append("base")
        if self.use_temporal:
            parts.append("temp")
        if self.use_strategy_priors:
            parts.append("priors")
        if self.use_climate:
            parts.append("clima")
        if self.use_lunar:
            parts.append("lua")
        if self.use_interactions:
            parts.append("inter")
        return "+".join(parts) if parts else "empty"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "FeatureConfig":
        d = {k: tuple(v) if k == "freq_windows" else v for k, v in d.items()}
        return cls(**d)

    @classmethod
    def from_signature(cls, sig: str) -> "FeatureConfig":
        """Create config from signature string (e.g., 'base+temp+clima')."""
        parts = set(sig.split("+"))
        return cls(
            use_base_history="base" in parts,
            use_temporal="temp" in parts,
            use_climate="clima" in parts,
            use_lunar="lua" in parts,
            use_interactions="inter" in parts,
            use_strategy_priors="priors" in parts,
        )


# ── Predefined configs for ablation grid ────────────────────────────────────────

MINIMAL = FeatureConfig(
    use_base_history=True,
    use_temporal=False,
    use_climate=False,
    use_lunar=False,
    use_interactions=False,
    use_strategy_priors=False,
)

BASE = FeatureConfig()  # base + temp + priors (defaults)

BASE_NO_PRIORS = FeatureConfig(use_strategy_priors=False)

WITH_CLIMATE = FeatureConfig(use_climate=True)

WITH_LUNAR = FeatureConfig(use_lunar=True)

WITH_CLIMATE_LUNAR = FeatureConfig(use_climate=True, use_lunar=True)

FULL = FeatureConfig(
    use_base_history=True,
    use_temporal=True,
    use_climate=True,
    use_lunar=True,
    use_interactions=True,
    use_strategy_priors=True,
)
