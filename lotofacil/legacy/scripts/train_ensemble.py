"""Grid search + ensemble training for Lotofácil 3679.

Usage:
    PYTHONPATH=src python train_ensemble.py

Phases:
    1. Grid search (6 HP configs, 500 draws) — find best
    2. Train 3 ensemble models with best config on ALL data
    3. Ensemble predict for concurso 3679
    4. Generate portfolio and compare with existing two games
"""

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("train_ensemble")

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lotofacil_lab.data.feature_flags import FeatureConfig
from lotofacil_lab.data.draws_loader import load_draws_last_n, load_draws
from lotofacil_lab.models.neural_modular import NeuralModular
from lotofacil_lab.features.builder import ModularFeatureBuilder

# ── Best known games (user's existing portfolio) ─────────────────────────
EXISTING_GAMES = [
    [2, 3, 4, 5, 7, 9, 10, 11, 12, 13, 14, 15, 20, 22, 25],
    [2, 3, 4, 5, 7, 9, 10, 11, 12, 13, 14, 19, 20, 22, 25],
]

EXISTING_CORE_11 = [3, 4, 5, 10, 11, 12, 13, 14, 20, 22, 25]

# ── Feature config (richest) ─────────────────────────────────────────────
FULL_CONFIG = FeatureConfig(
    use_base_history=True,
    use_temporal=True,
    use_climate=True,
    use_lunar=True,
    use_interactions=True,
    use_strategy_priors=True,
)

# ── Hyperparameter grid (6 combos) ───────────────────────────────────────
HP_GRID = [
    {   # A — baseline lab
        "tag": "A-lab",
        "LSTM_UNITS": [256, 128, 64],
        "LSTM_DROPOUT": 0.3,
        "LSTM_DROPOUT_INPUT": 0.1,
        "LSTM_DROPOUT_DENSE": 0.2,
        "LSTM_LR": 0.001,
        "FOCAL_LOSS_GAMMA": 2.0,
        "FOCAL_LOSS_ALPHA": 0.75,
        "LSTM_EPOCHS": 150,
        "LSTM_PATIENCE": 15,
        "RANDOM_SEED": 42,
    },
    {   # B — more regularization, lower LR
        "tag": "B-regularized",
        "LSTM_UNITS": [256, 128, 64],
        "LSTM_DROPOUT": 0.4,
        "LSTM_DROPOUT_INPUT": 0.2,
        "LSTM_DROPOUT_DENSE": 0.3,
        "LSTM_LR": 0.0005,
        "FOCAL_LOSS_GAMMA": 2.0,
        "FOCAL_LOSS_ALPHA": 0.85,
        "LSTM_EPOCHS": 150,
        "LSTM_PATIENCE": 15,
        "RANDOM_SEED": 42,
    },
    {   # C — smaller network
        "tag": "C-small",
        "LSTM_UNITS": [128, 128, 64],
        "LSTM_DROPOUT": 0.3,
        "LSTM_DROPOUT_INPUT": 0.1,
        "LSTM_DROPOUT_DENSE": 0.2,
        "LSTM_LR": 0.001,
        "FOCAL_LOSS_GAMMA": 3.0,
        "FOCAL_LOSS_ALPHA": 0.75,
        "LSTM_EPOCHS": 150,
        "LSTM_PATIENCE": 15,
        "RANDOM_SEED": 42,
    },
    {   # D — larger network
        "tag": "D-large",
        "LSTM_UNITS": [256, 256, 128],
        "LSTM_DROPOUT": 0.4,
        "LSTM_DROPOUT_INPUT": 0.15,
        "LSTM_DROPOUT_DENSE": 0.3,
        "LSTM_LR": 0.0005,
        "FOCAL_LOSS_GAMMA": 2.0,
        "FOCAL_LOSS_ALPHA": 0.85,
        "LSTM_EPOCHS": 150,
        "LSTM_PATIENCE": 20,
        "RANDOM_SEED": 42,
    },
    {   # E — low gamma, high alpha
        "tag": "E-focal",
        "LSTM_UNITS": [256, 128, 64],
        "LSTM_DROPOUT": 0.3,
        "LSTM_DROPOUT_INPUT": 0.1,
        "LSTM_DROPOUT_DENSE": 0.2,
        "LSTM_LR": 0.001,
        "FOCAL_LOSS_GAMMA": 1.0,
        "FOCAL_LOSS_ALPHA": 0.90,
        "LSTM_EPOCHS": 150,
        "LSTM_PATIENCE": 15,
        "RANDOM_SEED": 42,
    },
    {   # F — very low LR, long training
        "tag": "F-slow",
        "LSTM_UNITS": [256, 128, 64],
        "LSTM_DROPOUT": 0.2,
        "LSTM_DROPOUT_INPUT": 0.1,
        "LSTM_DROPOUT_DENSE": 0.2,
        "LSTM_LR": 0.0001,
        "FOCAL_LOSS_GAMMA": 3.0,
        "FOCAL_LOSS_ALPHA": 0.80,
        "LSTM_EPOCHS": 200,
        "LSTM_PATIENCE": 25,
        "RANDOM_SEED": 42,
    },
]

ENSEMBLE_SEEDS = [42, 123, 456]
SAVED_MODELS_DIR = SRC / "lotofacil_lab" / "saved_models"
SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════
#  PHASE 1: Grid search — train each HP config, evaluate on val set
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_config(hp: dict, train_draws: list, val_draws: list) -> dict:
    """Train a model with given HP, return val-set metrics."""
    tag = hp.pop("tag", "unknown")
    try:
        model = NeuralModular(FULL_CONFIG, hp_overrides=hp)
        model.fit(train_draws)

        # Predict each val draw and count hits
        val_hits = []
        for i, draw in enumerate(val_draws):
            # Need > window_size draws total for build_sequences to work
            n_train_ctx = min(FULL_CONFIG.window_size, len(train_draws))
            ctx = train_draws[-n_train_ctx:] + val_draws[:i + 1]
            proba = _get_proba(model, ctx)
            predicted = set(np.argsort(proba)[::-1][:15] + 1)
            actual = set(draw.dezenas)
            val_hits.append(len(predicted & actual))

        mean_hits = float(np.mean(val_hits))
        logger.info("  %s → mean_hits=%.2f  hits=%s", tag, mean_hits, val_hits)

        return {"tag": tag, "mean_hits": mean_hits, "hits": val_hits, "hp": hp}
    except Exception as e:
        logger.error("  %s → FAILED: %s", tag, e)
        return {"tag": tag, "mean_hits": 0, "hits": [], "hp": hp, "error": str(e)}
    finally:
        hp["tag"] = tag


def _get_proba(model: NeuralModular, context_draws: list) -> np.ndarray:
    """Get probability prediction, building features only once if needed."""
    try:
        return model.predict_proba(context_draws)
    except RuntimeError:
        return np.ones(25) / 25


def run_grid_search() -> list:
    """Run grid search and return ranked results."""
    logger.info("═" * 60)
    logger.info("PHASE 1: Grid Search — 6 HP configs on 500 draws")
    logger.info("═" * 60)

    all_draws = load_draws_last_n(250)
    train_draws = all_draws[:-50]
    val_draws = all_draws[-50:]

    logger.info("Train: %d draws | Val: %d draws", len(train_draws), len(val_draws))

    results = []
    for i, hp in enumerate(HP_GRID):
        logger.info("[%d/6] %s — training...", i + 1, hp["tag"])
        t0 = time.time()
        result = evaluate_config(dict(hp), train_draws, val_draws)
        elapsed = time.time() - t0
        logger.info("        → %.1fs | mean_hits=%.2f", elapsed, result.get("mean_hits", 0))
        results.append(result)

    results.sort(key=lambda r: r.get("mean_hits", 0), reverse=True)
    logger.info("")
    logger.info("Grid Search Results (ranked):")
    for i, r in enumerate(results):
        err = f" ERROR: {r.get('error', '')}" if "error" in r else ""
        logger.info("  %d. %s — mean_hits=%.2f%s", i + 1, r["tag"], r["mean_hits"], err)

    return results


# ═══════════════════════════════════════════════════════════════════════════
#  PHASE 2: Train ensemble (3 models) with best HP on ALL data
# ═══════════════════════════════════════════════════════════════════════════

def compute_core_11(probas: np.ndarray) -> list:
    """Return core 11 numbers from probability array."""
    return sorted((np.argsort(probas)[::-1][:11] + 1).tolist())


def generate_games_from_probas(probas: np.ndarray, n_games: int = 2) -> list:
    """Generate n_games from probability array, following conservative strategy."""
    ranked = np.argsort(probas)[::-1] + 1  # 1-indexed, highest first
    core = list(ranked[:11])
    candidates = list(ranked[11:17])  # top 6 fillers

    from itertools import combinations

    def score(game: list) -> float:
        s = sum(game)
        pairs = sum(1 for n in game if n % 2 == 0)
        imp = 15 - pairs
        moldura = {1, 2, 3, 4, 5, 6, 7, 11, 12, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25}
        mold = sum(1 for n in game if n in moldura)
        primos = {2, 3, 5, 7, 11, 13, 17, 19, 23}
        prime = sum(1 for n in game if n in primos)
        fib = {1, 2, 3, 5, 8, 13, 21}
        fibc = sum(1 for n in game if n in fib)

        score = 0
        score -= abs(s - 196) * 0.5
        score -= abs(pairs - 7) * 2
        score -= abs(mold - 9) * 2
        score -= max(0, prime - 7) * 3
        score -= max(0, 4 - prime) * 3
        score -= max(0, fibc - 5) * 3
        score -= max(0, 3 - fibc) * 3
        return score

    games = []
    used_fills = set()
    for _ in range(n_games):
        best = None
        best_score = -999
        for fill_combo in combinations(candidates, 4):
            fill_tuple = tuple(sorted(fill_combo))
            if fill_tuple in used_fills:
                continue
            game = sorted(core + list(fill_combo))
            s = score(game)
            if s > best_score:
                best_score = s
                best = game
        if best:
            games.append(best)
            fill = tuple(sorted(set(best) - set(core)))
            used_fills.add(fill)

    return games, core


def train_ensemble(best_hp: dict) -> list:
    """Train 3 models with different seeds, return list of (model, seed)."""
    logger.info("")
    logger.info("═" * 60)
    logger.info("PHASE 2: Ensemble — 3 models on ALL data")
    logger.info("═" * 60)

    all_draws = load_draws_last_n(250)
    logger.info("Total draws: %d", len(all_draws))

    trained = []
    for seed in ENSEMBLE_SEEDS:
        hp = dict(best_hp)
        hp["RANDOM_SEED"] = seed
        hp["tag"] = f"seed-{seed}"
        logger.info("[%d/3] seed=%d — training on %d draws...",
                    len(trained) + 1, seed, len(all_draws))
        t0 = time.time()
        model = NeuralModular(FULL_CONFIG, hp_overrides=hp)
        model.fit(all_draws)
        elapsed = time.time() - t0

        # Save
        path = SAVED_MODELS_DIR / f"ensemble_seed{seed}_{FULL_CONFIG.signature()}.keras"
        model.save(path)
        logger.info("        → %.1fs | saved to %s", elapsed, path.name)

        # Get prediction for 3679
        proba = model.predict_proba(all_draws)
        trained.append({"seed": seed, "model": model, "proba": proba})

    return trained


# ═══════════════════════════════════════════════════════════════════════════
#  PHASE 3: Ensemble prediction + portfolio generation
# ═══════════════════════════════════════════════════════════════════════════

def ensemble_predict(trained: list) -> np.ndarray:
    """Average probabilities from all trained models."""
    probas = np.array([t["proba"] for t in trained])
    ensemble_proba = probas.mean(axis=0)
    logger.info("")
    logger.info("═" * 60)
    logger.info("PHASE 3: Ensemble Prediction")
    logger.info("═" * 60)
    logger.info("Models: %d", len(trained))
    for i, t in enumerate(trained):
        core = compute_core_11(t["proba"])
        logger.info("  Model seed=%d → core 11: %s", t["seed"], core)

    core = compute_core_11(ensemble_proba)
    logger.info("  ENSEMBLE        → core 11: %s", core)
    return ensemble_proba


def print_games(games: list, label: str):
    logger.info("")
    logger.info("  ── %s ──", label)
    for i, g in enumerate(games):
        s = sum(g)
        pairs = sum(1 for n in g if n % 2 == 0)
        imp = 15 - pairs
        logger.info("  Jogo %02d: %s  | soma %d | %dP/%dI | quality=%.1f",
                    i + 1, " ".join(f"{n:02d}" for n in g), s, pairs, imp,
                    game_quality(g))


def game_quality(game: list) -> float:
    s = sum(game)
    pairs = sum(1 for n in game if n % 2 == 0)
    moldura = {1, 2, 3, 4, 5, 6, 7, 11, 12, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25}
    mold = sum(1 for n in game if n in moldura)
    primos = {2, 3, 5, 7, 11, 13, 17, 19, 23}
    prime = sum(1 for n in game if n in primos)
    fib = {1, 2, 3, 5, 8, 13, 21}
    fibc = sum(1 for n in game if n in fib)

    score = 7
    if 171 <= s <= 220:
        score += 1
    if 7 <= pairs <= 8:
        score += 1
    if 9 <= mold <= 10:
        score += 1
    if 4 <= prime <= 7:
        score += 1
    if 3 <= fibc <= 5:
        score += 1
    return score


def compare_with_existing(new_games: list, new_core: list):
    logger.info("")
    logger.info("═" * 60)
    logger.info("COMPARISON: New vs Existing Portfolio")
    logger.info("═" * 60)

    # Core comparison
    existing_set = set(EXISTING_CORE_11)
    new_set = set(new_core)
    common = existing_set & new_set
    only_old = existing_set - new_set
    only_new = new_set - existing_set
    logger.info("Core overlap: %d/11 common", len(common))
    logger.info("  Common: %s", sorted(common))
    logger.info("  Only old core: %s", sorted(only_old))
    logger.info("  Only new core: %s", sorted(only_new))

    # Coverage comparison
    all_old = set()
    for g in EXISTING_GAMES:
        all_old.update(g)
    all_new = set()
    for g in new_games:
        all_new.update(g)
    logger.info("")
    logger.info("Coverage old (unique): %d numbers: %s",
                len(all_old), sorted(all_old))
    logger.info("Coverage new (unique): %d numbers: %s",
                len(all_new), sorted(all_new))

    # Per-game quality
    logger.info("")
    logger.info("Existing portfolio (2 games):")
    for i, g in enumerate(EXISTING_GAMES):
        q = game_quality(g)
        s = sum(g)
        pairs = sum(1 for n in g if n % 2 == 0)
        logger.info("  Game %d: sum=%d pairs=%d quality=%.0f/7 | %s",
                    i + 1, s, pairs, q,
                    " ".join(f"{n:02d}" for n in g))

    logger.info("")
    logger.info("New portfolio (2 games):")
    for i, g in enumerate(new_games):
        q = game_quality(g)
        s = sum(g)
        pairs = sum(1 for n in g if n % 2 == 0)
        logger.info("  Game %d: sum=%d pairs=%d quality=%.0f/7 | %s",
                    i + 1, s, pairs, q,
                    " ".join(f"{n:02d}" for n in g))


def save_portfolio(games: list, core: list, ensemble_proba: np.ndarray):
    """Save portfolio to JSON for reference."""
    portfolio = {
        "concurso": 3679,
        "core_11": core,
        "ensemble_proba": ensemble_proba.tolist(),
        "games": [{"numbers": g, "sum": sum(g)} for g in games],
        "existing_games": [{"numbers": g, "sum": sum(g)} for g in EXISTING_GAMES],
    }
    path = SAVED_MODELS_DIR / f"portfolio_3679_ensemble.json"
    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)
    path.write_text(json.dumps(portfolio, indent=2, cls=NpEncoder))
    logger.info("Portfolio saved to %s", path)


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    total_start = time.time()

    # Phase 1: Grid search
    grid_results = run_grid_search()
    best_hp = dict(grid_results[0]["hp"]) if grid_results else dict(HP_GRID[0])
    best_tag = grid_results[0]["tag"] if grid_results else "unknown"
    logger.info("")
    logger.info("→ Best config: %s (mean_hits=%.2f)", best_tag, grid_results[0]["mean_hits"])

    # Phase 2: Ensemble training
    trained = train_ensemble(best_hp)

    # Phase 3: Ensemble prediction
    ensemble_proba = ensemble_predict(trained)
    new_core = compute_core_11(ensemble_proba)
    new_games, _ = generate_games_from_probas(ensemble_proba, n_games=2)

    # Phase 4: Print & compare
    logger.info("")
    logger.info("═" * 60)
    logger.info("  NEW PORTFOLIO — Concurso 3679")
    logger.info("═" * 60)
    logger.info("  Core 11: %s", new_core)
    print_games(new_games, "New Games")

    logger.info("")
    logger.info("  ── Existing Games ──")
    for i, g in enumerate(EXISTING_GAMES):
        s = sum(g)
        pairs = sum(1 for n in g if n % 2 == 0)
        logger.info("  Jogo %02d: %s  | soma %d | %dP/%dI | quality=%.1f",
                    i + 1, " ".join(f"{n:02d}" for n in g), s, pairs, imp := 15 - pairs,
                    game_quality(g))

    compare_with_existing(new_games, new_core)
    save_portfolio(new_games, new_core, ensemble_proba)

    total_elapsed = time.time() - total_start
    logger.info("")
    logger.info("═" * 60)
    logger.info("Total time: %.1f min", total_elapsed / 60)
    logger.info("═" * 60)

    # Also print the final new games clearly
    logger.info("")
    logger.info("=" * 60)
    logger.info("RESULTADO FINAL — Jogos para Concurso 3679")
    logger.info("=" * 60)
    logger.info("Core 11: %s", new_core)
    for i, g in enumerate(new_games):
        logger.info("Jogo %02d: %s (sum=%d)",
                    i + 1, " ".join(f"{n:02d}" for n in g), sum(g))
    logger.info("")
    logger.info("Comparação com portfolio existente:")
    compare_with_existing(new_games, new_core)


if __name__ == "__main__":
    main()
