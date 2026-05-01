"""Autoencoder model: draws[t-1] → draws[t] via encoder-decoder bottleneck."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import numpy as np

from lotofacil_ml.config import (
    AE_BATCH_SIZE,
    AE_BOTTLENECK_DIM,
    AE_DROPOUT,
    AE_ENCODER_DIMS,
    AE_EPOCHS,
    AE_PATIENCE,
    RANDOM_SEED,
    TOTAL_NUMBERS,
)
from lotofacil_ml.data.loader import Draw
from lotofacil_ml.models.base_model import BaseModel

logger = logging.getLogger(__name__)

try:
    import tensorflow as tf
    tf.random.set_seed(RANDOM_SEED)
    _TF_AVAILABLE = True
except ImportError:
    _TF_AVAILABLE = False
    logger.warning("TensorFlow not installed — AutoencoderModel will return uniform probabilities")


def _build_autoencoder() -> "tf.keras.Model":
    inputs = tf.keras.Input(shape=(TOTAL_NUMBERS,))
    x = inputs
    for dim in AE_ENCODER_DIMS:
        x = tf.keras.layers.Dense(dim, activation="relu")(x)
        x = tf.keras.layers.Dropout(AE_DROPOUT)(x)
    x = tf.keras.layers.Dense(AE_BOTTLENECK_DIM, activation="relu")(x)
    for dim in reversed(AE_ENCODER_DIMS):
        x = tf.keras.layers.Dense(dim, activation="relu")(x)
        x = tf.keras.layers.Dropout(AE_DROPOUT)(x)
    outputs = tf.keras.layers.Dense(TOTAL_NUMBERS, activation="sigmoid")(x)
    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="binary_crossentropy",
    )
    return model


class AutoencoderModel(BaseModel):
    """Predictive autoencoder: learns draw[t-1] → draw[t] transitions."""

    def __init__(self):
        self._model = None
        self._latest_proba: np.ndarray = np.full(
            TOTAL_NUMBERS, 1.0 / TOTAL_NUMBERS, dtype=np.float32
        )

    @property
    def name(self) -> str:
        return "autoencoder"

    def fit(self, draws: List[Draw]) -> None:
        if not _TF_AVAILABLE:
            logger.warning("Skipping AutoencoderModel training — TensorFlow unavailable")
            return
        if len(draws) < 2:
            logger.warning("AutoencoderModel: need at least 2 draws, got %d", len(draws))
            return

        binary = np.zeros((len(draws), TOTAL_NUMBERS), dtype=np.float32)
        for i, d in enumerate(draws):
            for n in d.dezenas:
                binary[i, n - 1] = 1.0

        X, y = binary[:-1], binary[1:]
        logger.info("Training AutoencoderModel X=%s y=%s", X.shape, y.shape)

        self._model = _build_autoencoder()
        self._model.fit(
            X, y,
            epochs=AE_EPOCHS,
            batch_size=AE_BATCH_SIZE,
            validation_split=0.1,
            callbacks=[
                tf.keras.callbacks.EarlyStopping(
                    monitor="val_loss", patience=AE_PATIENCE, restore_best_weights=True
                )
            ],
            verbose=0,
        )
        last = binary[-1:].astype(np.float32)
        self._latest_proba = self._model.predict(last, verbose=0)[0].astype(np.float32)
        logger.info("AutoencoderModel training complete")

    def predict_proba(self) -> np.ndarray:
        return self._latest_proba

    def save(self, path: Path) -> None:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        if _TF_AVAILABLE and self._model is not None:
            self._model.save(str(p / "autoencoder_model.keras"))

    def load(self, path: Path) -> None:
        if not _TF_AVAILABLE:
            return
        mp = Path(path) / "autoencoder_model.keras"
        if mp.exists():
            self._model = tf.keras.models.load_model(str(mp))
            logger.debug("AutoencoderModel loaded from %s", mp)
