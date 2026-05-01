"""Central configuration for the Lotofácil prediction system."""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent  # lotofacil/
SRC_DIR = _PACKAGE_DIR / "src"
DATA_DIR = _PACKAGE_DIR / "data"
OUTPUT_DIR = _PACKAGE_DIR / "output"

DATA_RAW = DATA_DIR / "raw" / "concursos"
DATA_PROCESSED = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "lotofacil.db"

OUTPUT_PREDICTIONS = OUTPUT_DIR / "predictions"
OUTPUT_REPORTS = OUTPUT_DIR / "reports"
OUTPUT_MODELS = OUTPUT_DIR / "models"

for d in [DATA_RAW, DATA_PROCESSED, OUTPUT_PREDICTIONS, OUTPUT_REPORTS, OUTPUT_MODELS]:
    d.mkdir(parents=True, exist_ok=True)

# ── API ────────────────────────────────────────────────────────────────────────
API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api"
API_LOTOFACIL = f"{API_BASE_URL}/lotofacil"
API_TIMEOUT = 30
API_RETRIES = 5
API_RETRY_MIN = 1
API_RETRY_MAX = 10
USER_AGENT = "lotofacil-prediction/2.0"

# ── Lottery constants ─────────────────────────────────────────────────────────
TOTAL_NUMBERS = 25
NUMBERS_PER_DRAW = 15
VALID_NUMBERS = set(range(1, TOTAL_NUMBERS + 1))

# ── Hit thresholds ─────────────────────────────────────────────────────────────
HIT_THRESHOLDS = [11, 12, 13, 14, 15]

# ── Cost / Prize ───────────────────────────────────────────────────────────────
COST_PER_GAME: float = 3.00

PRIZE_TABLE: dict[int, float] = {
    11: 7.00,
    12: 14.00,
    13: 35.00,
    14: 2_000.00,
    15: 1_500_000.00,
}

# ── Feature engineering ────────────────────────────────────────────────────────
FREQ_WINDOWS = [10, 30, 100]
MIN_HISTORY = 20

# ── ML ─────────────────────────────────────────────────────────────────────────
RF_N_ESTIMATORS = 200
RF_MAX_DEPTH = 10
RF_MIN_SAMPLES_LEAF = 5
CV_N_SPLITS = 5

# ── Neural: LSTM + Attention ──────────────────────────────────────────────────
LSTM_WINDOW_SIZE = 50
LSTM_UNITS_1 = 128
LSTM_UNITS_2 = 128
LSTM_UNITS_3 = 64
LSTM_DROPOUT = 0.3
LSTM_DROPOUT_INPUT = 0.2
LSTM_DROPOUT_DENSE = 0.4
LSTM_LR = 0.001
LSTM_LR_MIN = 0.00001
LSTM_LR_FACTOR = 0.5
LSTM_LR_PATIENCE = 5
LSTM_EPOCHS = 100
LSTM_BATCH_SIZE = 32
LSTM_PATIENCE = 10

FOCAL_LOSS_GAMMA = 2.0
FOCAL_LOSS_ALPHA = 0.75

NEURAL_VAL_SPLIT = 0.2

ATTENTION_DIM = 128
ATTENTION_HEADS = 4

TRANSFORMER_MODEL_DIM = 64
TRANSFORMER_HEADS = 4
TRANSFORMER_KEY_DIM = 16
TRANSFORMER_BLOCKS = 2
TRANSFORMER_DROPOUT = 0.3
TRANSFORMER_EPOCHS = 100
TRANSFORMER_BATCH_SIZE = 32
TRANSFORMER_PATIENCE = 10

AE_ENCODER_DIMS = [64, 32, 16]
AE_BOTTLENECK_DIM = 8
AE_DROPOUT = 0.2
AE_EPOCHS = 100
AE_BATCH_SIZE = 32
AE_PATIENCE = 10

# ── Backtest ───────────────────────────────────────────────────────────────────
BACKTEST_TRAIN_WINDOW: int = 300
BACKTEST_RETRAIN_EVERY: int = 50
BACKTEST_MIN_TRAIN: int = 100
VALIDATION_N_BACKTEST = 100

# ── Random seed ────────────────────────────────────────────────────────────────
RANDOM_SEED = 42

# ── Ensemble weights ───────────────────────────────────────────────────────────
ENSEMBLE_WEIGHTS = {
    "frequency": 0.20,
    "ml": 0.45,
    "lstm": 0.35,
}
