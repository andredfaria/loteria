"""Central configuration for the Lotofácil ML system."""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
_PACKAGE_DIR = Path(__file__).resolve().parent   # src/lotofacil_ml/
SRC_DIR = _PACKAGE_DIR.parent                    # src/
PROJECT_ROOT = SRC_DIR.parent                    # lotofacil/

DATA_DIR = PROJECT_ROOT / "dados"
MODELS_DIR = SRC_DIR / "models_saved"
DB_PATH = SRC_DIR / "lotofacil.db"

MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ── API ────────────────────────────────────────────────────────────────────────
API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api"
API_LOTOFACIL = f"{API_BASE_URL}/lotofacil"
API_TIMEOUT = 30  # seconds
API_RETRIES = 5
API_RETRY_MIN = 1   # seconds
API_RETRY_MAX = 10  # seconds
USER_AGENT = "lotofacil-ml/1.0 (statistical analysis)"

# ── Lottery constants ──────────────────────────────────────────────────────────
TOTAL_NUMBERS = 25
NUMBERS_PER_DRAW = 15
VALID_NUMBERS = set(range(1, TOTAL_NUMBERS + 1))

# ── Random seed ────────────────────────────────────────────────────────────────
RANDOM_SEED = 42

# ── Ensemble weights ───────────────────────────────────────────────────────────
ENSEMBLE_WEIGHTS = {
    "frequency": 0.20,
    "ml": 0.45,
    "lstm": 0.35,
}

# ── Frequency model ────────────────────────────────────────────────────────────
FREQ_WEIGHTS = {
    "freq_30": 0.5,
    "freq_100": 0.3,
    "freq_all": 0.2,
}
FREQ_WINDOWS = [10, 30, 100]

# ── ML ensemble ────────────────────────────────────────────────────────────────
RF_N_ESTIMATORS = 200
RF_MAX_DEPTH = 10
RF_MIN_SAMPLES_LEAF = 5
CV_N_SPLITS = 5

# ── LSTM ───────────────────────────────────────────────────────────────────────
LSTM_WINDOW_SIZE = 50
LSTM_UNITS_1 = 128
LSTM_UNITS_2 = 64
LSTM_DROPOUT = 0.3
LSTM_LR = 0.001
LSTM_EPOCHS = 100
LSTM_BATCH_SIZE = 32
LSTM_PATIENCE = 10

# ── Backtest / walk-forward ────────────────────────────────────────────────────
BACKTEST_DEFAULT_N = 100

# ── Scheduler times (24h) ─────────────────────────────────────────────────────
SCHEDULE_UPDATE_DAYS = ["mon", "wed", "fri"]
SCHEDULE_UPDATE_HOUR = 23
SCHEDULE_RETRAIN_DAY = "mon"
SCHEDULE_RETRAIN_HOUR = 2

# ── Hit thresholds ─────────────────────────────────────────────────────────────
HIT_THRESHOLDS = [11, 12, 13, 14, 15]

# ── Financial simulation ────────────────────────────────────────────────────────
COST_PER_GAME: float = 3.50

# Fixed prizes (11-13 pts) and representative averages (14-15 pts) in BRL.
# Source: Caixa rules. Update periodically for accurate financial simulation.
PRIZE_TABLE: dict[int, float] = {
    11: 7.00,
    12: 14.00,
    13: 35.00,
    14: 2_000.00,
    15: 1_500_000.00,
}

# ── Backtest defaults ──────────────────────────────────────────────────────────
BACKTEST_TRAIN_WINDOW: int = 300   # mínimo de draws para treinar
BACKTEST_RETRAIN_EVERY: int = 50   # retreina a cada N concursos
BACKTEST_MIN_TRAIN: int = 100      # training guard; distinct from BACKTEST_DEFAULT_N (validator draw count)

assert BACKTEST_MIN_TRAIN <= BACKTEST_TRAIN_WINDOW, (
    "BACKTEST_MIN_TRAIN must not exceed BACKTEST_TRAIN_WINDOW"
)
assert BACKTEST_RETRAIN_EVERY <= BACKTEST_TRAIN_WINDOW, (
    "BACKTEST_RETRAIN_EVERY must not exceed BACKTEST_TRAIN_WINDOW"
)

# ── Transformer ────────────────────────────────────────────────────────────────
TRANSFORMER_MODEL_DIM = 64
TRANSFORMER_HEADS = 4
TRANSFORMER_KEY_DIM = 16
TRANSFORMER_BLOCKS = 2
TRANSFORMER_DROPOUT = 0.3
TRANSFORMER_EPOCHS = 100
TRANSFORMER_BATCH_SIZE = 32
TRANSFORMER_PATIENCE = 10

# ── Autoencoder ────────────────────────────────────────────────────────────────
AE_ENCODER_DIMS = [64, 32, 16]
AE_BOTTLENECK_DIM = 8
AE_DROPOUT = 0.2
AE_EPOCHS = 100
AE_BATCH_SIZE = 32
AE_PATIENCE = 10

# ── Validation KPIs ────────────────────────────────────────────────────────────
VALIDATION_N_BACKTEST = 100   # default test window for evaluate command
