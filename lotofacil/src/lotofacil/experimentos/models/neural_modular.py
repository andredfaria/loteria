"""Modular neural model: LSTM + MultiHeadAttention + Focal Loss.

Architecture adapts to any FeatureConfig, so n_features is determined
at build time. Reuses the focal loss and attention pattern from
src/strategies/eleven_numbers/approaches/neural.py.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import numpy as np

from lotofacil.experimentos.config import (
    TOTAL_NUMBERS, RANDOM_SEED,
    LSTM_UNITS, ATTENTION_HEADS, ATTENTION_DIM,
    LSTM_DROPOUT, LSTM_DROPOUT_INPUT, LSTM_DROPOUT_DENSE,
    LSTM_LR, LSTM_LR_MIN, LSTM_LR_FACTOR, LSTM_LR_PATIENCE,
    LSTM_EPOCHS, LSTM_BATCH_SIZE, LSTM_PATIENCE,
    FOCAL_LOSS_GAMMA, FOCAL_LOSS_ALPHA, NEURAL_VAL_SPLIT,
    MODELS_DIR,
)
from lotofacil.experimentos.data.feature_flags import FeatureConfig
from lotofacil.experimentos.features.builder import ModularFeatureBuilder
from lotofacil.experimentos.models.base import BaseLabModel

logger = logging.getLogger(__name__)


def focal_loss(gamma: float = FOCAL_LOSS_GAMMA, alpha: float = FOCAL_LOSS_ALPHA):
    """Focal loss for multi-label binary classification."""
    def loss(y_true, y_pred):
        import tensorflow.keras.backend as K
        y_true = K.cast(y_true, dtype="float32")
        y_pred = K.clip(y_pred, K.epsilon(), 1.0 - K.epsilon())
        ce = -(y_true * K.log(y_pred) + (1 - y_true) * K.log(1 - y_pred))
        pt = K.pow(1 - y_pred, gamma) * y_true * alpha + \
             K.pow(y_pred, gamma) * (1 - y_true) * (1 - alpha)
        return K.mean(ce * pt, axis=-1)
    return loss


class NeuralModular(BaseLabModel):
    """LSTM + Attention neural model parameterised by FeatureConfig.

    The model shape (LSTM units, attention heads, n_features) is determined
    by the config at fit() time and stays frozen until the model is reset.

    Args:
        config: FeatureConfig controlling which feature blocks are active.
        hp_overrides: Optional dict of hyperparameter overrides.
            Keys match config.py constant names (e.g. 'LSTM_UNITS', 'LSTM_LR').
    """

    def __init__(self, config: FeatureConfig, hp_overrides: dict | None = None, fast: bool = False):
        self.config = config
        self._hp = hp_overrides or {}
        if fast:
            # Smaller model for faster CPU training
            self._hp.setdefault("LSTM_UNITS", [64, 32, 16])
            self._hp.setdefault("LSTM_DROPOUT", 0.2)
            self._hp.setdefault("LSTM_DROPOUT_DENSE", 0.15)
            self._hp.setdefault("ATTENTION_HEADS", 2)
            self._hp.setdefault("ATTENTION_DIM", 16)
            self._hp.setdefault("LSTM_BATCH_SIZE", 64)
        self._model = None
        self._history: dict = {}
        self._fitted = False

    def _hp_val(self, name: str):
        """Return hyperparameter value: override > config > None."""
        if name in self._hp:
            return self._hp[name]
        return globals().get(name)

    _HP_NAMES = (
        "LSTM_UNITS", "ATTENTION_HEADS", "ATTENTION_DIM",
        "LSTM_DROPOUT", "LSTM_DROPOUT_INPUT", "LSTM_DROPOUT_DENSE",
        "LSTM_LR", "LSTM_LR_MIN", "LSTM_LR_FACTOR", "LSTM_LR_PATIENCE",
        "LSTM_EPOCHS", "LSTM_BATCH_SIZE", "LSTM_PATIENCE",
        "FOCAL_LOSS_GAMMA", "FOCAL_LOSS_ALPHA", "NEURAL_VAL_SPLIT",
        "RANDOM_SEED",
    )

    def hiperparametros_efetivos(self) -> dict:
        """Valores efetivos (override > config) de todos os hiperparâmetros."""
        return {name: self._hp_val(name) for name in self._HP_NAMES}

    def fit(self, draws: list) -> None:
        """Train on historical draws using the active feature config."""
        try:
            import tensorflow as tf
            tf.random.set_seed(self._hp_val("RANDOM_SEED"))
        except ImportError:
            raise RuntimeError("TensorFlow required. pip install tensorflow>=2.16")

        builder = ModularFeatureBuilder(draws, self.config)
        X, y, meta = builder.build_sequences()

        if meta["n_samples"] < 20:
            raise ValueError(f"Too few sequences: {meta['n_samples']} < 20")

        n_val = max(1, int(meta["n_samples"] * self._hp_val("NEURAL_VAL_SPLIT")))
        n_train = meta["n_samples"] - n_val
        X_train, X_val = X[:n_train], X[n_train:]
        y_train, y_val = y[:n_train], y[n_train:]

        n_features = meta["n_features"]
        model = self._build_model(n_features, self.config.window_size)

        model.compile(
            optimizer=tf.keras.optimizers.Adam(
                learning_rate=self._hp_val("LSTM_LR")
            ),
            loss=focal_loss(
                gamma=self._hp_val("FOCAL_LOSS_GAMMA"),
                alpha=self._hp_val("FOCAL_LOSS_ALPHA"),
            ),
            metrics=["binary_accuracy"],
        )

        class _EpochProgressCallback(tf.keras.callbacks.Callback):
            """Emits parseable epoch progress to stdout for the dashboard modal."""
            def __init__(self, total_epochs: int) -> None:
                super().__init__()
                self._total = total_epochs

            def on_epoch_end(self, epoch, logs=None) -> None:
                logs = logs or {}
                e = epoch + 1
                loss = logs.get("loss", 0.0)
                val_loss = logs.get("val_loss", 0.0)
                print(
                    f"EPOCH_PROGRESS: {e}/{self._total} "
                    f"loss={loss:.4f} val_loss={val_loss:.4f}",
                    flush=True,
                )

        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=self._hp_val("LSTM_PATIENCE"),
                restore_best_weights=True, min_delta=1e-5,
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss", factor=self._hp_val("LSTM_LR_FACTOR"),
                patience=self._hp_val("LSTM_LR_PATIENCE"),
                min_lr=self._hp_val("LSTM_LR_MIN"), verbose=0,
            ),
            _EpochProgressCallback(self._hp_val("LSTM_EPOCHS")),
        ]

        try:
            history = model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val),
                epochs=self._hp_val("LSTM_EPOCHS"),
                batch_size=self._hp_val("LSTM_BATCH_SIZE"),
                callbacks=callbacks,
                verbose=0,
            )
        except MemoryError:
            raise RuntimeError(
                "Memória insuficiente para treinar o modelo. "
                "Tente reduzir 'concursos' (ex: 500), 'janela' (ex: 30) "
                "ou use o modo rápido."
            )
        self._model = model
        self._history = {k: [float(v) for v in vs] for k, vs in history.history.items()}
        self._meta = meta
        self._fitted = True

        best = int(np.argmin(history.history["val_loss"]))
        logger.info(
            "Trained [%s]: %d samples, %d features, best_epoch=%d val_loss=%.4f",
            self.config.signature(), meta["n_samples"], n_features,
            best + 1, history.history["val_loss"][best],
        )

    def predict(self, draws: list) -> List[int]:
        """Return top target_numbers dezenas by predicted probability."""
        if not self._fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        builder = ModularFeatureBuilder(draws, self.config)
        x_latest = builder.build_for_prediction()  # (1, window, n_features)
        proba = self._model.predict(x_latest, verbose=0)[0]  # (25,)

        top = np.argsort(proba)[::-1][:self.config.target_numbers]
        return sorted(int(i + 1) for i in top)

    def predict_proba(self, draws: list) -> np.ndarray:
        """Return raw probability array of shape (25,)."""
        if not self._fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        builder = ModularFeatureBuilder(draws, self.config)
        x_latest = builder.build_for_prediction()
        return self._model.predict(x_latest, verbose=0)[0]

    def _build_model(self, n_features: int, window_size: int):
        """Build LSTM + MultiHeadAttention + Dense model."""
        import tensorflow as tf
        from tensorflow.keras import layers, models, Input

        lstm_units = self._hp_val("LSTM_UNITS")
        attn_heads = self._hp_val("ATTENTION_HEADS")
        attn_dim = self._hp_val("ATTENTION_DIM")
        dp_input = self._hp_val("LSTM_DROPOUT_INPUT")
        dp = self._hp_val("LSTM_DROPOUT")
        dp_dense = self._hp_val("LSTM_DROPOUT_DENSE")

        inputs = Input(shape=(window_size, n_features))
        x = layers.Dropout(dp_input)(inputs)

        x = layers.LSTM(lstm_units[0], return_sequences=True)(x)
        x = layers.MultiHeadAttention(
            num_heads=attn_heads, key_dim=attn_dim, dropout=0.1
        )(x, x)
        x = layers.LayerNormalization()(x)

        x = layers.LSTM(lstm_units[1], return_sequences=True)(x)
        x = layers.MultiHeadAttention(
            num_heads=max(1, attn_heads // 2), key_dim=attn_dim // 2, dropout=0.1
        )(x, x)
        x = layers.LayerNormalization()(x)

        x = layers.LSTM(lstm_units[2], return_sequences=False)(x)
        x = layers.Dropout(dp)(x)

        x = layers.Dense(64, activation="relu")(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(dp_dense)(x)

        outputs = layers.Dense(TOTAL_NUMBERS, activation="sigmoid")(x)
        model = models.Model(inputs=inputs, outputs=outputs)
        logger.debug("Model params: %d", model.count_params())
        return model

    def save(self, path: Path | None = None) -> None:
        if not self._fitted:
            raise RuntimeError("Nothing to save — model not fitted.")
        if path is None:
            path = MODELS_DIR / f"neural_{self.config.signature()}.keras"
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._model.save(str(path))
        meta = {
            "history": self._history,
            "config": self.config.to_dict(),
            "hp_overrides": self._hp,
            "hp_efetivos": self.hiperparametros_efetivos(),
        }
        path.with_suffix(".meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        logger.info("Saved model to %s", path)

    def load(self, path: Path | None = None) -> None:
        from tensorflow.keras.models import load_model
        from lotofacil.experimentos.data.feature_flags import FeatureConfig
        if path is None:
            path = MODELS_DIR / f"neural_{self.config.signature()}.keras"
        self._model = load_model(str(path), custom_objects={"loss": focal_loss()})
        meta_path = Path(path).with_suffix(".meta.json")
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            self._history = meta.get("history", {})
            saved_cfg = meta.get("config")
            if saved_cfg:
                # Restore exact config used at training time (preserves window_size etc.)
                self.config = FeatureConfig.from_dict(saved_cfg)
        self._fitted = True

    @property
    def name(self) -> str:
        return f"neural_{self.config.signature()}"

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def get_history(self) -> dict:
        return self._history
