"""LSTM neural model — gracefully falls back if TensorFlow is unavailable."""

import logging
from pathlib import Path

import numpy as np

from lotofacil.infra.config import (
    LSTM_BATCH_SIZE,
    LSTM_DROPOUT,
    LSTM_EPOCHS,
    LSTM_LR,
    LSTM_PATIENCE,
    LSTM_UNITS_1,
    LSTM_UNITS_2,
    LSTM_WINDOW_SIZE,
    RANDOM_SEED,
    TOTAL_NUMBERS,
)
from lotofacil.infra.modelos.base_model import BaseModel

logger = logging.getLogger(__name__)

try:
    import tensorflow as tf
    tf.random.set_seed(RANDOM_SEED)
    _TF_AVAILABLE = True
    logger.debug("TensorFlow %s available", tf.__version__)
except ImportError:
    _TF_AVAILABLE = False
    logger.warning("TensorFlow not installed — LSTMModel will return uniform probabilities")


def _build_lstm_model() -> "tf.keras.Model":
    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(LSTM_UNITS_1, return_sequences=True,
                             input_shape=(LSTM_WINDOW_SIZE, TOTAL_NUMBERS)),
        tf.keras.layers.Dropout(LSTM_DROPOUT),
        tf.keras.layers.LSTM(LSTM_UNITS_2),
        tf.keras.layers.Dropout(LSTM_DROPOUT),
        tf.keras.layers.Dense(TOTAL_NUMBERS, activation="sigmoid"),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=LSTM_LR),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


class LSTMModel(BaseModel):
    """Sequence model trained on sliding windows of draw binary matrices."""

    def __init__(self):
        self._model = None
        self._trained = False

    @property
    def name(self) -> str:
        return "lstm"

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        """
        Args:
            X_train: shape (n, window_size, 25)
            y_train: shape (n, 25)
        """
        if not _TF_AVAILABLE:
            logger.warning("Skipping LSTM training — TensorFlow unavailable")
            return

        logger.info("Training LSTMModel on X=%s y=%s", X_train.shape, y_train.shape)
        self._model = _build_lstm_model()
        callbacks = [
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss", factor=0.5, patience=5, min_lr=1e-6
            ),
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=LSTM_PATIENCE, restore_best_weights=True
            ),
        ]
        self._model.fit(
            X_train,
            y_train,
            epochs=LSTM_EPOCHS,
            batch_size=LSTM_BATCH_SIZE,
            validation_split=0.1,
            callbacks=callbacks,
            verbose=0,
        )
        self._trained = True
        logger.info("LSTMModel training complete")

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Args:
            X: shape (1, window_size, 25)
        Returns:
            probabilities: shape (25,)
        """
        if not _TF_AVAILABLE or not self._trained or self._model is None:
            logger.debug("LSTM returning uniform probabilities")
            return np.full(TOTAL_NUMBERS, 1.0 / TOTAL_NUMBERS, dtype=np.float32)
        preds = self._model.predict(X, verbose=0)
        return preds[0].astype(np.float32)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        if _TF_AVAILABLE and self._model is not None:
            self._model.save(str(path / "lstm_model.keras"))
            logger.debug("LSTMModel saved to %s", path)
        else:
            logger.debug("LSTMModel: nothing to save (not trained or TF unavailable)")

    def load(self, path: Path) -> None:
        if not _TF_AVAILABLE:
            logger.warning("Cannot load LSTM model — TensorFlow unavailable")
            return
        model_path = Path(path) / "lstm_model.keras"
        if model_path.exists():
            self._model = tf.keras.models.load_model(str(model_path))
            self._trained = True
            logger.debug("LSTMModel loaded from %s", model_path)
        else:
            logger.warning("LSTM model file not found at %s", model_path)
