"""Transformer sequence model for Lotofácil prediction."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import numpy as np

from lotofacil_ml.config import (
    LSTM_WINDOW_SIZE,
    RANDOM_SEED,
    TOTAL_NUMBERS,
    TRANSFORMER_BATCH_SIZE,
    TRANSFORMER_BLOCKS,
    TRANSFORMER_DROPOUT,
    TRANSFORMER_EPOCHS,
    TRANSFORMER_HEADS,
    TRANSFORMER_KEY_DIM,
    TRANSFORMER_MODEL_DIM,
    TRANSFORMER_PATIENCE,
)
from lotofacil_ml.data.loader import Draw
from lotofacil_ml.models.base_model import BaseModel

logger = logging.getLogger(__name__)

try:
    import tensorflow as tf
    tf.random.set_seed(RANDOM_SEED)
    _TF_AVAILABLE = True
    logger.debug("TensorFlow %s available", tf.__version__)
except ImportError:
    _TF_AVAILABLE = False
    logger.warning("TensorFlow not installed — TransformerModel will return uniform probabilities")


def _draws_to_binary(draws: List[Draw]) -> np.ndarray:
    """Convert draws to binary matrix of shape (N, 25)."""
    mat = np.zeros((len(draws), TOTAL_NUMBERS), dtype=np.float32)
    for i, d in enumerate(draws):
        for n in d.dezenas:
            mat[i, n - 1] = 1.0
    return mat


def _build_transformer(window_size: int) -> "tf.keras.Model":
    inputs = tf.keras.Input(shape=(window_size, TOTAL_NUMBERS))
    x = tf.keras.layers.Dense(TRANSFORMER_MODEL_DIM)(inputs)
    pos_emb = tf.keras.layers.Embedding(
        input_dim=window_size, output_dim=TRANSFORMER_MODEL_DIM
    )(tf.range(start=0, limit=window_size, delta=1))
    x = x + pos_emb
    for _ in range(TRANSFORMER_BLOCKS):
        attn_out = tf.keras.layers.MultiHeadAttention(
            num_heads=TRANSFORMER_HEADS,
            key_dim=TRANSFORMER_KEY_DIM,
            dropout=TRANSFORMER_DROPOUT,
        )(x, x)
        x = tf.keras.layers.LayerNormalization()(x + attn_out)
        ff = tf.keras.layers.Dense(TRANSFORMER_MODEL_DIM * 2, activation="relu")(x)
        ff = tf.keras.layers.Dense(TRANSFORMER_MODEL_DIM)(ff)
        ff = tf.keras.layers.Dropout(TRANSFORMER_DROPOUT)(ff)
        x = tf.keras.layers.LayerNormalization()(x + ff)
    x = tf.keras.layers.GlobalAveragePooling1D()(x)
    x = tf.keras.layers.Dense(64, activation="relu")(x)
    x = tf.keras.layers.Dropout(TRANSFORMER_DROPOUT)(x)
    outputs = tf.keras.layers.Dense(TOTAL_NUMBERS, activation="sigmoid")(x)
    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="binary_crossentropy",
    )
    return model


class TransformerModel(BaseModel):
    """Transformer attention model on sliding windows of binary draw sequences."""

    def __init__(self, window_size: int = LSTM_WINDOW_SIZE):
        self._window_size = window_size
        self._model = None
        self._latest_proba: np.ndarray = np.full(
            TOTAL_NUMBERS, 1.0 / TOTAL_NUMBERS, dtype=np.float32
        )

    @property
    def name(self) -> str:
        return "transformer"

    def fit(self, draws: List[Draw]) -> None:
        if not _TF_AVAILABLE:
            logger.warning("Skipping TransformerModel training — TensorFlow unavailable")
            return
        if len(draws) <= self._window_size:
            logger.warning(
                "TransformerModel: not enough draws (%d) for window_size=%d",
                len(draws), self._window_size,
            )
            return

        binary = _draws_to_binary(draws)
        X = np.array([binary[i - self._window_size:i] for i in range(self._window_size, len(binary))])
        y = binary[self._window_size:]

        logger.info("Training TransformerModel X=%s y=%s", X.shape, y.shape)
        self._model = _build_transformer(self._window_size)
        self._model.fit(
            X, y,
            epochs=TRANSFORMER_EPOCHS,
            batch_size=TRANSFORMER_BATCH_SIZE,
            validation_split=0.1,
            callbacks=[
                tf.keras.callbacks.EarlyStopping(
                    monitor="val_loss", patience=TRANSFORMER_PATIENCE, restore_best_weights=True
                )
            ],
            verbose=0,
        )
        last_window = binary[-self._window_size:][np.newaxis]  # (1, window, 25)
        self._latest_proba = self._model.predict(last_window, verbose=0)[0].astype(np.float32)
        logger.info("TransformerModel training complete")

    def predict_proba(self) -> np.ndarray:
        return self._latest_proba

    def save(self, path: Path) -> None:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        if _TF_AVAILABLE and self._model is not None:
            self._model.save(str(p / "transformer_model.keras"))
            logger.debug("TransformerModel saved to %s", p)
        else:
            logger.debug("TransformerModel: nothing to save (not trained or TF unavailable)")

    def load(self, path: Path) -> None:
        if not _TF_AVAILABLE:
            logger.warning("Cannot load Transformer model — TensorFlow unavailable")
            return
        mp = Path(path) / "transformer_model.keras"
        if mp.exists():
            self._model = tf.keras.models.load_model(str(mp))
            logger.debug("TransformerModel loaded from %s", mp)
        else:
            logger.warning("Transformer model file not found at %s", mp)
