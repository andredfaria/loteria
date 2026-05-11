"""Retrain ensemble + predict contest 3680 with ROI-optimized portfolio."""
import json, logging, sys, time
from pathlib import Path
import numpy as np

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S", level=logging.INFO)
logger = logging.getLogger("predict_3680")

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lotofacil_lab.data.feature_flags import FeatureConfig
from lotofacil_lab.data.draws_loader import load_draws_last_n
from lotofacil_lab.models.neural_modular import NeuralModular

MODELS_DIR = SRC / "lotofacil_lab" / "saved_models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

CONFIG = FeatureConfig(
    use_base_history=True, use_temporal=True, use_climate=True,
    use_lunar=True, use_interactions=True, use_strategy_priors=True,
)

# C-small HP (best from grid search: 9.28 mean hits)
HP = {
    "LSTM_UNITS": [128, 128, 64],
    "LSTM_DROPOUT": 0.3,
    "LSTM_DROPOUT_INPUT": 0.1,
    "LSTM_DROPOUT_DENSE": 0.2,
    "LSTM_LR": 0.001,
    "FOCAL_LOSS_GAMMA": 3.0,
    "FOCAL_LOSS_ALPHA": 0.75,
    "LSTM_EPOCHS": 150,
    "LSTM_PATIENCE": 20,
}

ENSEMBLE_SEEDS = [42, 123, 456]
N_DRAWS = 250


def game_quality_score(game: list) -> float:
    s, pairs = sum(game), sum(1 for n in game if n % 2 == 0)
    moldura = {1, 2, 3, 4, 5, 6, 7, 11, 12, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25}
    primos = {2, 3, 5, 7, 11, 13, 17, 19, 23}
    fib = {1, 2, 3, 5, 8, 13, 21}
    score = 7
    if 171 <= s <= 220: score += 1
    if 7 <= pairs <= 8: score += 1
    if 9 <= sum(1 for n in game if n in moldura) <= 10: score += 1
    if 4 <= sum(1 for n in game if n in primos) <= 7: score += 1
    if 3 <= sum(1 for n in game if n in fib) <= 5: score += 1
    return score


def generate_roi_games(proba: np.ndarray, n_games: int = 2) -> list:
    """Generate games maximizing both probability and coverage for ROI."""
    ranked = np.argsort(proba)[::-1] + 1
    core = list(ranked[:11])
    candidates = list(ranked[11:17])

    from itertools import combinations

    # Score game by probability + quality + diversity
    def score(game, used_nums):
        hit_prob = proba[[n - 1 for n in game]].sum()
        quality = game_quality_score(game) * 0.05
        diversity = len(set(game) - used_nums) * 0.01
        return hit_prob + quality + diversity

    games = []
    used_nums = set()
    for _ in range(n_games):
        best, best_score = None, -999
        for combo in combinations(candidates, 4):
            game = sorted(core + list(combo))
            s = score(game, used_nums)
            if s > best_score:
                best, best_score = game, s
        if best:
            games.append(best)
            used_nums.update(best)
    return games


def main():
    t0 = time.time()
    draws = load_draws_last_n(N_DRAWS)
    logger.info("Loaded %d draws (concurso %d–%d)", len(draws), draws[0].concurso, draws[-1].concurso)

    trained = []
    for i, seed in enumerate(ENSEMBLE_SEEDS):
        hp = {**HP, "RANDOM_SEED": seed, "tag": f"seed-{seed}"}
        logger.info("[%d/3] seed=%d training on %d draws...", i + 1, seed, len(draws))
        t1 = time.time()
        model = NeuralModular(CONFIG, hp_overrides=hp)
        model.fit(draws)
        path = MODELS_DIR / f"c3680_seed{seed}_{CONFIG.signature()}.keras"
        model.save(path)
        logger.info("        → %.1fs saved", time.time() - t1)

        proba = model.predict_proba(draws)
        trained.append({"seed": seed, "model": model, "proba": proba})

    # Ensemble
    ensemble_proba = np.mean([t["proba"] for t in trained], axis=0)

    core_11 = sorted((np.argsort(ensemble_proba)[::-1][:11] + 1).tolist())
    games = generate_roi_games(ensemble_proba, n_games=2)

    logger.info("")
    logger.info("=" * 60)
    logger.info("  CONCURSO 3680 — 08/05/2026 (Sexta, 21h)")
    logger.info("=" * 60)
    logger.info("  Clima SP: 23.5°C, 0% chuva, wcode=3")
    logger.info("  Modelo: C-small ensemble (3 seeds)")
    logger.info("  Core 11: %s", core_11)
    logger.info("")
    logger.info("  Jogos otimizados para ROI positivo:")
    logger.info("")

    result = {"concurso": 3680, "core_11": core_11,
              "ensemble_proba": ensemble_proba.tolist(), "games": []}

    for i, game in enumerate(games):
        prob_sum = ensemble_proba[[n - 1 for n in game]].sum()
        prob_mean = ensemble_proba[[n - 1 for n in game]].mean()
        q = game_quality_score(game)
        pairs = sum(1 for n in game if n % 2 == 0)
        imp = 15 - pairs
        s = sum(game)

        logger.info("  Jogo %02d: %s", i + 1,
                     " ".join(f"{n:02d}" for n in game))
        logger.info("          sum=%d | %dP/%dI | quality=%d/7 | P(media)=%.4f",
                     s, pairs, imp, q, prob_mean)

        result["games"].append({
            "numbers": game, "sum": s, "pairs": pairs,
            "prob_mean": prob_mean, "quality": q,
        })

    # Coverage
    all_nums = set()
    for g in games:
        all_nums.update(g)
    logger.info("")
    logger.info("  Cobertura: %d numeros unicos (%s)", len(all_nums),
                " ".join(f"{n:02d}" for n in sorted(all_nums)))
    logger.info("  Custo: R$%.2f (2 jogos × R$3.50)", 2 * 3.50)

    # ROI analysis
    logger.info("")
    logger.info("  Analise de ROI:")
    logger.info("    11 acertos → R$ 7.00 (break-even)")
    logger.info("    12 acertos → R$ 14.00 (ROI +100%%)")
    logger.info("    13 acertos → R$ 35.00 (ROI +400%%)")

    path = MODELS_DIR / "portfolio_3680.json"
    path.write_text(json.dumps(result, indent=2))
    logger.info("")
    logger.info("  Portfolio salvo: %s", path)
    logger.info("  Tempo total: %.1f min", (time.time() - t0) / 60)


if __name__ == "__main__":
    main()
