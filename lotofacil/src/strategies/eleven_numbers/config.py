"""Configuration for the 11-numbers prediction strategy."""

# ── Strategy parameters ────────────────────────────────────────────────────────
TARGET_NUMBERS = 11
MIN_HISTORY = 50

# ── Ensemble weights for combining approaches ──────────────────────────────────
APPROACH_WEIGHTS = {
    "statistical": 0.30,
    "ml": 0.45,
    "neural": 0.25,
}

# ── Statistical approach parameters ────────────────────────────────────────────
STAT_FREQ_WINDOWS = [10, 30, 100]
STAT_FREQ_WEIGHTS = {"freq_10": 0.5, "freq_30": 0.3, "freq_100": 0.2}
STAT_ATRASO_CAP = 20
STAT_TREND_WINDOW = 5

# ── ML approach parameters ─────────────────────────────────────────────────────
ML_RETRAIN_EVERY = 50
ML_MIN_TRAIN_DRAWS = 100

# ── Neural approach parameters ─────────────────────────────────────────────────
NEURAL_WINDOW_SIZE = 50
NEURAL_LSTM_UNITS = [256, 128, 64]
NEURAL_DROPOUT = 0.3
NEURAL_DROPOUT_DENSE = 0.4
NEURAL_EPOCHS = 200
NEURAL_PATIENCE = 15
NEURAL_VAL_SPLIT = 0.2
NEURAL_FOCAL_GAMMA = 2.0

# ── Output ─────────────────────────────────────────────────────────────────────
STRATEGY_NAME = "11-numbers"
STRATEGY_DESCRIPTION = "Predict 11 numbers with highest probability of containing 11+ hits"
