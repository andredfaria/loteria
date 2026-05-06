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

from lotofacil_lab.config import (
    TOTAL_NUMBERS, RANDOM_SEED,
    LSTM_UNITS, ATTENTION_HEADS, ATTENTION_DIM,
    LSTM_DROPOUT, LSTM_DROPOUT_INPUT, LSTM_DROPOUT_DENSE,
    LSTM_LR, LSTM_LR_MIN, LSTM_LR_FACTOR, LSTM_LR_PATIENCE,
    LSTM_EPOCHS, LSTM_BATCH_SIZE, LSTM_PATIENCE,
    FOCAL_LOSS_GAMMA, FOCAL_LOSS_ALPHA, NEURAL_VAL_SPLIT,
    MODELS_DIR,
)
from lotofacil_lab.data.feature_flags import FeatureConfig
from lotofacil_lab.features.builder import ModularFeatureBuilder
from lotofacil_lab.models.base import BaseLabModel

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
    """

    def __init__(self, config: FeatureConfig):
        self.config = config
        self._model = None
        self._history: dict = {}
        self._fitted = False

    def fit(self, draws: list) -> None:
        """Train on historical draws using the active feature config."""
        try:
            import tensorflow as tf
            tf.random.set_seed(RANDOM_SEED)
        except ImportError:
            raise RuntimeError("TensorFlow required. pip install tensorflow>=2.16")

        builder = ModularFeatureBuilder(draws, self.config)
        X, y, meta = builder.build_sequences()

        if meta["n_samples"] < 20:
            raise ValueError(f"Too few sequences: {meta['n_samples']} < 20")

        n_val = max(1, int(meta["n_samples"] * NEURAL_VAL_SPLIT))
        n_train = meta["n_samples"] - n_val
        X_train, X_val = X[:n_train], X[n_train:]
        y_train, y_val = y[:n_train], y[n_train:]

        n_features = meta["n_features"]
        model = self._build_model(n_features, self.config.window_size)

        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=LSTM_LR),
            loss=focal_loss(),
            metrics=["binary_accuracy"],
        )

        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=LSTM_PATIENCE,
                restore_best_weights=True, min_delta=1e-5,
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss", factor=LSTM_LR_FACTOR,
                patience=LSTM_LR_PATIENCE, min_lr=LSTM_LR_MIN, verbose=0,
            ),
        ]

        history = model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=LSTM_EPOCHS,
            batch_size=LSTM_BATCH_SIZE,
            callbacks=callbacks,
            verbose=0,
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

        inputs = Input(shape=(window_size, n_features))
        x = layers.Dropout(LSTM_DROPOUT_INPUT)(inputs)

        x = layers.LSTM(LSTM_UNITS[0], return_sequences=True)(x)
        x = layers.MultiHeadAttention(
            num_heads=ATTENTION_HEADS, key_dim=ATTENTION_DIM, dropout=0.1
        )(x, x)
        x = layers.LayerNormalization()(x)

        x = layers.LSTM(LSTM_UNITS[1], return_sequences=True)(x)
        x = layers.MultiHeadAttention(
            num_heads=max(1, ATTENTION_HEADS // 2), key_dim=ATTENTION_DIM // 2, dropout=0.1
        )(x, x)
        x = layers.LayerNormalization()(x)

        x = layers.LSTM(LSTM_UNITS[2], return_sequences=False)(x)
        x = layers.Dropout(LSTM_DROPOUT)(x)

        x = layers.Dense(64, activation="relu")(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(LSTM_DROPOUT_DENSE)(x)

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
        meta = {"history": self._history, "config": self.config.to_dict()}
        path.with_suffix(".meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        logger.info("Saved model to %s", path)

    def load(self, path: Path | None = None) -> None:
        from tensorflow.keras.models import load_model
        if path is None:
            path = MODELS_DIR / f"neural_{self.config.signature()}.keras"
        self._model = load_model(str(path), custom_objects={"loss": focal_loss()})
        meta_path = Path(path).with_suffix(".meta.json")
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            self._history = meta.get("history", {})
        self._fitted = True

    @property
    def name(self) -> str:
        return f"neural_{self.config.signature()}"

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def get_history(self) -> dict:
        return self._history
