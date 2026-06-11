"""Central configuration for lotofacil_lab experimental pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────────────
_LAB_DIR = Path(__file__).resolve().parent        # src/lotofacil/experimentos/
SRC_DIR = _LAB_DIR.parent.parent                  # src/
PROJECT_ROOT = SRC_DIR.parent                     # lotofacil/

# Ensure src/ is importable (core.models, data.*, strategies.*, lotofacil_ml.*)
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

DATA_DIR = PROJECT_ROOT / "dados"
CLIMATE_DIR = DATA_DIR / "clima"
LUA_DIR = DATA_DIR / "lua"
OUTPUT_DIR = _LAB_DIR / "output"
MODELS_DIR = _LAB_DIR / "saved_models"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ── Lottery constants ───────────────────────────────────────────────────────────
TOTAL_NUMBERS = 25
NUMBERS_PER_DRAW = 15
HORA_SORTEIO = 21          # 21h BRT (São Paulo)
LATITUDE_SP = (-23, 33, 0)
LONGITUDE_SP = (-46, 37, 0)

# ── Draw location for climate API ───────────────────────────────────────────────
LATITUDE = -23.55
LONGITUDE = -46.63
TIMEZONE = "America/Sao_Paulo"

# ── Lunar normalization constants ────────────────────────────────────────────────
LUNAR_PERIGEE_KM = 356_500.0
LUNAR_APOGEE_KM = 406_700.0
LUNAR_CYCLE_DAYS = 29.53

# Phase thresholds for is_new / is_full flags (±1.5 days ≈ 1.5/29.53 fraction)
LUNAR_NEW_THRESHOLD = 1.5 / LUNAR_CYCLE_DAYS
LUNAR_FULL_THRESHOLD = 1.5 / LUNAR_CYCLE_DAYS

# ── Random seed ─────────────────────────────────────────────────────────────────
RANDOM_SEED = 42

# ── Neural model hyperparameters ─────────────────────────────────────────────────
LSTM_UNITS = [256, 128, 64]
ATTENTION_HEADS = 4
ATTENTION_DIM = 32
LSTM_DROPOUT = 0.3
LSTM_DROPOUT_INPUT = 0.1
LSTM_DROPOUT_DENSE = 0.2
LSTM_LR = 0.001
LSTM_LR_MIN = 1e-5
LSTM_LR_FACTOR = 0.5
LSTM_LR_PATIENCE = 5
LSTM_EPOCHS = 100
LSTM_BATCH_SIZE = 32
LSTM_PATIENCE = 10
FOCAL_LOSS_GAMMA = 2.0
FOCAL_LOSS_ALPHA = 0.75
NEURAL_VAL_SPLIT = 0.15

# ── Presets de treino (CLI `lotofacil lab train --preset`) ──────────────────────
# Chaves = nomes das constantes de hiperparâmetros acima. Flags explícitas da
# CLI sobrescrevem o preset. "completo" é vazio de propósito: usa os defaults
# deste módulo (LSTM [256,128,64], epochs 100, patience 10).
PRESETS_TREINO: dict[str, dict] = {
    "rapido": {
        "LSTM_UNITS": [64, 32, 16],
        "LSTM_BATCH_SIZE": 64,
        "LSTM_DROPOUT": 0.2,
        "LSTM_DROPOUT_DENSE": 0.15,
        "ATTENTION_HEADS": 2,
        "ATTENTION_DIM": 16,
        "LSTM_EPOCHS": 40,
        "LSTM_PATIENCE": 5,
    },
    "equilibrado": {
        "LSTM_UNITS": [128, 64, 32],
        "LSTM_EPOCHS": 60,
        "LSTM_PATIENCE": 8,
        "LSTM_BATCH_SIZE": 32,
    },
    "completo": {},
}

# ── Walk-forward defaults ────────────────────────────────────────────────────────
BACKTEST_MIN_TRAIN = 300
BACKTEST_RETRAIN_EVERY = 50

# ── Tuning por busca aleatória (CLI `lotofacil lab tune`) ────────────────────────
# Espaço de busca de hiperparâmetros. Chaves = nomes das constantes deste
# módulo; cada valor descreve como amostrar:
#   - "log_uniforme": 10 ** uniform(log10(min), log10(max))
#   - "uniforme":     uniform(min, max)
#   - "escolha":      escolha uniforme dentro de "valores"
TUNING_ESPACO: dict[str, dict] = {
    "LSTM_LR": {"tipo": "log_uniforme", "min": 1e-4, "max": 1e-2},
    "LSTM_DROPOUT": {"tipo": "uniforme", "min": 0.1, "max": 0.5},
    "LSTM_BATCH_SIZE": {"tipo": "escolha", "valores": [16, 32, 64]},
    "LSTM_UNITS": {"tipo": "escolha",
                   "valores": [[64, 32, 16], [128, 64, 32], [256, 128, 64]]},
}

# Relatórios de tuning (JSON + markdown). Diretório criado no uso.
TUNING_DIR = PROJECT_ROOT / "saida" / "experimentos"

# ── Financial simulation ─────────────────────────────────────────────────────────
try:
    from lotofacil_ml.config import COST_PER_GAME, PRIZE_TABLE  # reuse from ml
except ImportError:
    COST_PER_GAME = 3.50
    PRIZE_TABLE = {11: 7.00, 12: 14.00, 13: 35.00, 14: 2_000.00, 15: 1_500_000.00}

# ── Archive API (backfill histórico) ─────────────────────────────────────────────
ARCHIVE_API_URL = "https://archive-api.open-meteo.com/v1/archive"
ARCHIVE_BATCH_DAYS = 30          # concursos por chamada de API
ARCHIVE_DELAY_SECONDS = 1.0      # segundos entre chamadas

# ── Strategy hierarchy weights (Nível 1 > 2 > 3) ────────────────────────────────
STRATEGY_WEIGHTS = {
    "soma": 10.0,
    "repetidos": 8.0,
    "parimpar": 5.0,
    "moldura": 5.0,
    "primos": 3.0,
    "fibonacci": 3.0,
    "consecutivos": 3.0,
    "ciclo": 2.0,
}

# ── Similarity search defaults ──────────────────────────────────────────────────
SIMILARITY_TOP_N = 10
SIMILARITY_MOON_WEIGHT = 0.5
SIMILARITY_CLIMATE_WEIGHT = 0.5
SIMILARITY_MIN_DRAWS = 3

# ── Combined scoring weights ─────────────────────────────────────────────────────
SCORE_SIMILAR_WEIGHT = 0.5
SCORE_PADROES21_WEIGHT = 0.5
PADROES21_JANELA = 21

# Faixas-alvo para 15-numbers (baseadas em docs/Hierarquia de Estratégias)
STRATEGY_RANGES = {
    "soma": (171, 220),
    "repetidos": (8, 10),
    "pares": (7, 8),
    "moldura": (9, 10),
    "primos": (4, 7),
    "fibonacci": (3, 5),
    "consecutivos": (2, 999),   # mínimo 2
}

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
FIBONACCI = {1, 2, 3, 5, 8, 13, 21}
MOLDURA = {1, 2, 3, 4, 5, 6, 7, 11, 12, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25}

# Window for strategy prior conformity check
STRATEGY_PRIOR_WINDOW = 10
