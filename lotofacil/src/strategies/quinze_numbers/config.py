"""Configuration for the 15-numbers prediction strategy (target: 11+ hits)."""

# ── Strategy parameters ────────────────────────────────────────────────────────
TARGET_NUMBERS = 15
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
NEURAL_LSTM_UNITS = [128, 128, 64]
NEURAL_DROPOUT = 0.3
NEURAL_DROPOUT_DENSE = 0.4
NEURAL_EPOCHS = 100
NEURAL_PATIENCE = 10
NEURAL_VAL_SPLIT = 0.2
NEURAL_FOCAL_GAMMA = 2.0
NEURAL_FOCAL_ALPHA = 0.75
NEURAL_LR = 0.001
NEURAL_LR_FACTOR = 0.5
NEURAL_LR_PATIENCE = 5
NEURAL_LR_MIN = 0.00001
NEURAL_BATCH_SIZE = 32
NEURAL_DROPOUT_INPUT = 0.2
NEURAL_ATTENTION_DIM = 128
NEURAL_ATTENTION_HEADS = 4

# ── Post-processing parameters ─────────────────────────────────────────────────
POST_N_CANDIDATES = 50000
POST_NEURAL_WEIGHT = 0.60
POST_FILTER_WEIGHT = 0.40

# ── Statistical filter ranges (calibrated for 15 numbers) ─────────────────────
FILTERS = {
    "soma": {"min": 171, "max": 220, "weight": 10.0},
    "repetidos": {"min": 8, "max": 10, "weight": 8.0},
    "pares": {"min": 7, "max": 8, "weight": 5.0},
    "moldura": {"min": 9, "max": 10, "weight": 5.0},
    "primos": {"min": 4, "max": 7, "weight": 3.0},
    "fibonacci": {"min": 3, "max": 5, "weight": 3.0},
    "consecutivos": {"min": 2, "max": 6, "weight": 3.0},
}

# ── Output ─────────────────────────────────────────────────────────────────────
STRATEGY_NAME = "15-numbers-11plus"
STRATEGY_DESCRIPTION = "Predict 15 numbers calibrated to hit 11+ (optimized 11+ rate)"
