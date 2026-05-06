"""Neural approach for 15-numbers strategy (target: 11+ hits).

Architecture: LSTM (128→128→64) + Self-Attention + Focal Loss.
Optimized for predicting 15 numbers calibrated to hit 11+.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import numpy as np

from strategies.quinze_numbers.config import (
    NEURAL_WINDOW_SIZE,
    NEURAL_LSTM_UNITS,
    NEURAL_DROPOUT,
    NEURAL_DROPOUT_DENSE,
    NEURAL_LR,
    NEURAL_EPOCHS,
    NEURAL_BATCH_SIZE,
    NEURAL_PATIENCE,
    NEURAL_VAL_SPLIT,
    NEURAL_FOCAL_GAMMA,
    NEURAL_FOCAL_ALPHA,
    NEURAL_ATTENTION_DIM,
    NEURAL_ATTENTION_HEADS,
    NEURAL_LR_FACTOR,
    NEURAL_LR_PATIENCE,
    NEURAL_LR_MIN,
    NEURAL_DROPOUT_INPUT,
)
from core.config import TOTAL_NUMBERS, OUTPUT_MODELS, RANDOM_SEED
from core.models import Draw
from data.preprocessor import LotofacilPreprocessor

logger = logging.getLogger(__name__)

MODEL_NAME = "lstm_attention_15numbers"
MODEL_PATH = OUTPUT_MODELS / f"{MODEL_NAME}.keras"


class AttentionLayer:
    """Self-attention layer for Keras functional API."""

    def __init__(self, units: int, heads: int = 1):
        self.units = units
        self.heads = heads

    def __call__(self, inputs):
        try:
            import tensorflow as tf
            from tensorflow.keras import layers

            x = layers.MultiHeadAttention(
                num_heads=self.heads,
                key_dim=self.units,
                dropout=0.1,
            )(inputs, inputs)
            x = layers.LayerNormalization()(x + inputs)
            return x
        except Exception as e:
            logger.warning("Attention layer failed: %s, using input directly", e)
            return inputs


def focal_loss(gamma: float = NEURAL_FOCAL_GAMMA, alpha: float = NEURAL_FOCAL_ALPHA):
    """Focal loss for binary classification."""
    def loss(y_true, y_pred):
        import tensorflow.keras.backend as K
        y_true = K.cast(y_true, dtype="float32")
        y_pred = K.clip(y_pred, K.epsilon(), 1.0 - K.epsilon())
        ce = -(y_true * K.log(y_pred) + (1 - y_true) * K.log(1 - y_pred))
        focal = ce * K.pow(1 - y_pred, gamma) * y_true * alpha + \
                ce * K.pow(y_pred, gamma) * (1 - y_true) * (1 - alpha)
        return K.mean(focal, axis=-1)
    return loss


class NeuralApproach:
    """LSTM + Attention neural network for 15-number predictions."""

    def __init__(self):
        self._model = None
        self._probas: np.ndarray | None = None
        self._fitted = False
        self._history = {}

    def fit(self, draws: List[Draw]) -> None:
        """Train LSTM + Attention model on historical draws."""
        try:
            import tensorflow as tf
            tf.random.set_seed(RANDOM_SEED)
            from tensorflow.keras import layers, models, callbacks, Input
        except ImportError:
            raise RuntimeError("TensorFlow is required for neural approach")

        preprocessor = LotofacilPreprocessor(draws)
        X_bin, y_bin, X_freq, X_atraso, X_climate = preprocessor.prepare_enriched_sequences(
            window_size=NEURAL_WINDOW_SIZE
        )

        if len(X_bin) < 20:
            raise ValueError(f"Not enough data: got {len(X_bin)} sequences, need >=20")

        combined_input = self._combine_inputs(X_bin, X_freq, X_atraso, X_climate)

        n_samples = len(combined_input)
        n_val = max(1, int(n_samples * NEURAL_VAL_SPLIT))
        n_train = n_samples - n_val

        X_train = combined_input[:n_train]
        y_train = y_bin[:n_train]
        X_val = combined_input[n_train:]
        y_val = y_bin[n_train:]

        logger.info("Data: train=%d, val=%d, features_per_draw=%d",
                     n_train, n_val, combined_input.shape[2])

        model = self._build_model()

        callbacks_list = [
            callbacks.EarlyStopping(
                monitor="val_loss",
                patience=NEURAL_PATIENCE,
                restore_best_weights=True,
                min_delta=1e-5,
            ),
            callbacks.ReduceLROnPlateau(
                monitor="val_loss",
                factor=NEURAL_LR_FACTOR,
                patience=NEURAL_LR_PATIENCE,
                min_lr=NEURAL_LR_MIN,
                verbose=0,
            ),
        ]

        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=NEURAL_LR),
            loss=focal_loss(gamma=NEURAL_FOCAL_GAMMA, alpha=NEURAL_FOCAL_ALPHA),
            metrics=["binary_accuracy"],
        )

        history = model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=NEURAL_EPOCHS,
            batch_size=NEURAL_BATCH_SIZE,
            callbacks=callbacks_list,
            verbose=0,
        )

        self._model = model
        self._history = {k: [float(v) for v in v_list] for k, v_list in history.history.items()}

        best_epoch = np.argmin(history.history["val_loss"])
        logger.info("Training complete. Best epoch: %d, best val_loss: %.4f",
                     best_epoch + 1, history.history["val_loss"][best_epoch])

        probas = self._predict_from_model(preprocessor)
        self._probas = probas
        self._fitted = True

    def _combine_inputs(self, binary: np.ndarray, freq: np.ndarray, atraso: np.ndarray, climate: np.ndarray) -> np.ndarray:
        """Combine binary, frequency, delay and climate features into single input tensor."""
        atraso_expanded = atraso[:, None, :].repeat(binary.shape[1], axis=1)
        combined = np.concatenate([binary, freq, atraso_expanded, climate], axis=-1)
        return combined

    def _build_model(self):
        """Build LSTM + Attention model."""
        try:
            import tensorflow as tf
            from tensorflow.keras import layers, models, Input
        except ImportError:
            raise RuntimeError("TensorFlow is required")

        n_features = TOTAL_NUMBERS * 3 + 8

        inputs = Input(shape=(NEURAL_WINDOW_SIZE, n_features))

        x = layers.Dropout(NEURAL_DROPOUT_INPUT)(inputs)

        x = layers.LSTM(NEURAL_LSTM_UNITS[0], return_sequences=True)(x)
        x = AttentionLayer(NEURAL_ATTENTION_DIM, heads=NEURAL_ATTENTION_HEADS)(x)
        x = layers.LayerNormalization()(x)

        x = layers.LSTM(NEURAL_LSTM_UNITS[1], return_sequences=True)(x)
        x = AttentionLayer(NEURAL_ATTENTION_DIM // 2, heads=1)(x)
        x = layers.LayerNormalization()(x)

        x = layers.LSTM(NEURAL_LSTM_UNITS[2], return_sequences=False)(x)
        x = layers.Dropout(NEURAL_DROPOUT)(x)

        x = layers.Dense(64, activation="relu")(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(NEURAL_DROPOUT_DENSE)(x)

        outputs = layers.Dense(TOTAL_NUMBERS, activation="sigmoid")(x)

        model = models.Model(inputs=inputs, outputs=outputs)
        logger.info("Model built: %s total params", model.count_params())
        return model

    def _predict_from_model(self, preprocessor: LotofacilPreprocessor) -> np.ndarray:
        """Get probability predictions for the next draw."""
        X_bin = preprocessor.prepare_lstm_sequences(window_size=NEURAL_WINDOW_SIZE)
        _, _, X_freq, X_atraso, X_climate = preprocessor.prepare_enriched_sequences(window_size=NEURAL_WINDOW_SIZE)

        last_bin = X_bin[-1:]
        last_freq = X_freq[-1:]
        last_atraso = X_atraso[-1:]
        last_climate = X_climate[-1:]
        combined = self._combine_inputs(last_bin, last_freq, last_atraso, last_climate)

        pred = self._model.predict(combined, verbose=0)[0]
        if pred.sum() > 0:
            pred /= pred.sum()
        return pred

    def predict_proba(self, draws: List[Draw] | None = None) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Approach not fitted. Call fit() first.")

        if self._probas is not None:
            return self._probas

        if draws is None:
            raise RuntimeError("Draws required for inference when model was loaded.")

        from data.preprocessor import LotofacilPreprocessor
        preprocessor = LotofacilPreprocessor(draws)
        probas = self._predict_from_model(preprocessor)
        self._probas = probas
        return probas

    def get_training_history(self) -> dict:
        return self._history

    def save(self, path: Path | None = None) -> None:
        if path is None:
            path = MODEL_PATH
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._model.save(str(path))
        if self._history:
            meta = {"history": self._history, "config": {
                "units": NEURAL_LSTM_UNITS,
                "window": NEURAL_WINDOW_SIZE,
                "epochs": NEURAL_EPOCHS,
                "focal_gamma": NEURAL_FOCAL_GAMMA,
            }}
            with open(path.with_suffix(".meta.json"), "w") as f:
                json.dump(meta, f, indent=2)

    def load(self, path: Path | None = None) -> None:
        try:
            from tensorflow.keras.models import load_model
        except ImportError:
            raise RuntimeError("TensorFlow is required for neural approach")

        if path is None:
            path = MODEL_PATH
        self._model = load_model(str(path), custom_objects={"loss": focal_loss()})
        self._fitted = True

        meta_path = path.with_suffix(".meta.json")
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            self._history = meta.get("history", {})

    @property
    def name(self) -> str:
        return "neural"

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def predict_with_filters(self, draws: List[Draw]) -> List[int]:
        """Predict 15 numbers combining neural probabilities with statistical filters."""
        if not self._fitted:
            raise RuntimeError("Approach not fitted. Call fit() first.")

        from data.preprocessor import LotofacilPreprocessor
        from strategies.quinze_numbers.post_processor import optimize

        preprocessor = LotofacilPreprocessor(draws)
        probas = self._predict_from_model(preprocessor)

        last_draw = draws[-1].dezenas if draws else None
        optimized = optimize(probas, last_draw=last_draw)

        return optimized
