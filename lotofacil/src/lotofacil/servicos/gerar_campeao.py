"""Champion game generation — combines all strategies to generate, score, and rank 10,000 candidates."""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

import numpy as np

from lotofacil.dominio.entidades import Sorteio
from lotofacil.infra.config import DADOS_DIR, JOGOS_DIR, MODELOS_DIR, TOTAL_NUMEROS
from lotofacil.infra.dados.leitor import load_draws

_PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
_FIBONACCI = {1, 2, 3, 5, 8, 13, 21}
_MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
N_CANDIDATES = 10000
TARGET_COUNT = 15

FILTERS = {
    "soma": {"min": 171, "max": 220, "weight": 10.0},
    "repetidos": {"min": 8, "max": 10, "weight": 8.0},
    "pares": {"min": 7, "max": 8, "weight": 5.0},
    "moldura": {"min": 9, "max": 10, "weight": 5.0},
    "primos": {"min": 4, "max": 7, "weight": 3.0},
    "fibonacci": {"min": 3, "max": 5, "weight": 3.0},
    "consecutivos": {"min": 2, "max": 6, "weight": 3.0},
}
TOTAL_FILTER_WEIGHT = sum(f["weight"] for f in FILTERS.values())


@dataclass(frozen=True)
class ResultadoCampeao:
    concurso_alvo: int
    top_3: List[dict]
    total_candidatos: int = N_CANDIDATES
    estrategias_ativas: List[str] = field(default_factory=list)
    ultimo_concurso: int = 0


def _game_quality_score(game: List[int], last_draw: List[int]) -> float:
    """Score 0.0–1.0 based on 7 statistical filter criteria."""
    passed = 0
    pares = sum(1 for n in game if n % 2 == 0)
    if (pares, TARGET_COUNT - pares) in {(7, 8), (8, 7), (6, 9), (9, 6)}:
        passed += 1
    soma = sum(game)
    if FILTERS["soma"]["min"] <= soma <= FILTERS["soma"]["max"]:
        passed += 1
    if FILTERS["moldura"]["min"] <= sum(1 for n in game if n in _MOLDURA) <= FILTERS["moldura"]["max"]:
        passed += 1
    if FILTERS["primos"]["min"] <= sum(1 for n in game if n in _PRIMOS) <= FILTERS["primos"]["max"]:
        passed += 1
    if FILTERS["fibonacci"]["min"] <= sum(1 for n in game if n in _FIBONACCI) <= FILTERS["fibonacci"]["max"]:
        passed += 1
    s = sorted(game)
    if any(s[i + 1] == s[i] + 1 for i in range(len(s) - 1)):
        passed += 1
    if FILTERS["repetidos"]["min"] <= sum(1 for n in game if n in set(last_draw)) <= FILTERS["repetidos"]["max"]:
        passed += 1
    return passed / 7


def _filter_weighted_score(game: List[int], last_draw: List[int]) -> float:
    """Weighted filter score (soft penalty, same as quinze_dezenas post_processor)."""
    score = 0.0
    s = sum(game)
    lo, hi = FILTERS["soma"]["min"], FILTERS["soma"]["max"]
    if lo <= s <= hi:
        score += FILTERS["soma"]["weight"]
    else:
        dist = min(abs(s - lo), abs(s - hi))
        score += max(-FILTERS["soma"]["weight"], -FILTERS["soma"]["weight"] * dist / 20.0)

    pares = sum(1 for n in game if n % 2 == 0)
    lo, hi = FILTERS["pares"]["min"], FILTERS["pares"]["max"]
    if lo <= pares <= hi:
        score += FILTERS["pares"]["weight"]
    elif 6 <= pares <= 9:
        score += FILTERS["pares"]["weight"] * 0.5
    else:
        score += -FILTERS["pares"]["weight"] * 0.5

    mold = sum(1 for n in game if n in _MOLDURA)
    lo, hi = FILTERS["moldura"]["min"], FILTERS["moldura"]["max"]
    if lo <= mold <= hi:
        score += FILTERS["moldura"]["weight"]
    elif 8 <= mold <= 11:
        score += FILTERS["moldura"]["weight"] * 0.5
    else:
        score += -FILTERS["moldura"]["weight"] * 0.5

    prim = sum(1 for n in game if n in _PRIMOS)
    if FILTERS["primos"]["min"] <= prim <= FILTERS["primos"]["max"]:
        score += FILTERS["primos"]["weight"]
    else:
        score += -FILTERS["primos"]["weight"] * 0.3

    fib = sum(1 for n in game if n in _FIBONACCI)
    if FILTERS["fibonacci"]["min"] <= fib <= FILTERS["fibonacci"]["max"]:
        score += FILTERS["fibonacci"]["weight"]
    else:
        score += -FILTERS["fibonacci"]["weight"] * 0.3

    s = sorted(game)
    cons = sum(1 for i in range(len(s) - 1) if s[i + 1] == s[i] + 1)
    if cons >= FILTERS["consecutivos"]["min"]:
        score += FILTERS["consecutivos"]["weight"]
    else:
        score += -FILTERS["consecutivos"]["weight"] * 0.5

    reps = len(set(game) & set(last_draw))
    lo, hi = FILTERS["repetidos"]["min"], FILTERS["repetidos"]["max"]
    if lo <= reps <= hi:
        score += FILTERS["repetidos"]["weight"]
    else:
        dist = min(abs(reps - lo), abs(reps - hi))
        score += max(-FILTERS["repetidos"]["weight"], -FILTERS["repetidos"]["weight"] * dist / 3.0)

    return score


# ── Probability collection (load pretrained first, fallback to fit) ────────────

def _get_ensemble_predictor_probas(draws: List[Sorteio]) -> Optional[np.ndarray]:
    try:
        from lotofacil.infra.modelos.ensemble import EnsemblePredictor
        predictor = EnsemblePredictor()
        try:
            predictor.load()
            if not predictor._fitted:
                raise RuntimeError("not fitted")
        except Exception:
            predictor.fit(draws)
        probas = predictor.predict_proba()
        if probas.sum() > 0:
            probas /= probas.sum()
        return probas
    except Exception as e:
        print(f"    [yellow]EnsemblePredictor falhou: {e}[/yellow]")
        return None


def _get_eleven_strategy_probas(draws: List[Sorteio]) -> Optional[np.ndarray]:
    try:
        from lotofacil.infra.estrategias.onze_dezenas.approaches.statistical import StatisticalApproach
        from lotofacil.infra.estrategias.onze_dezenas.approaches.ml import MLApproach
        from lotofacil.infra.estrategias.onze_dezenas.config import APPROACH_WEIGHTS
        from lotofacil.infra.config import TOTAL_NUMEROS as TOTAL

        probas = np.zeros(TOTAL, dtype=np.float64)
        total_w = 0.0

        stat = StatisticalApproach()
        stat.fit(draws)
        p = stat.predict_proba()
        w = APPROACH_WEIGHTS.get("statistical", 0.3)
        probas += w * p
        total_w += w

        ml = MLApproach()
        ml.fit(draws)
        p = ml.predict_proba(draws)
        w = APPROACH_WEIGHTS.get("ml", 0.45)
        probas += w * p
        total_w += w

        try:
            from lotofacil.infra.estrategias.onze_dezenas.approaches.neural import NeuralApproach
            neural = NeuralApproach()
            try:
                neural.load()
            except Exception:
                neural.fit(draws)
            p = neural.predict_proba()
            w = APPROACH_WEIGHTS.get("neural", 0.25)
            probas += w * p
            total_w += w
        except Exception as e:
            print(f"    [dim]Neural (11) indisponivel: {e}[/dim]")

        if total_w > 0:
            probas /= total_w
        if probas.sum() > 0:
            probas /= probas.sum()
        return probas
    except Exception as e:
        print(f"    [yellow]ElevenNumbersStrategy falhou: {e}[/yellow]")
        return None


def _get_quinze_ensemble_probas(draws: List[Sorteio]) -> Optional[np.ndarray]:
    try:
        from lotofacil.infra.estrategias.quinze_dezenas.approaches.ensemble import EnsembleApproach
        approach = EnsembleApproach()
        try:
            approach.load()
        except Exception:
            approach.fit(draws)
        probas = approach.predict_proba(draws)
        if probas.sum() > 0:
            probas /= probas.sum()
        return probas
    except Exception as e:
        print(f"    [yellow]QuinzeEnsemble falhou: {e}[/yellow]")
        return None


def _get_probabilistic_probas(draws: List[Sorteio]) -> Optional[np.ndarray]:
    try:
        from lotofacil.infra.modelos.probabilistic import ProbabilisticModel
        model = ProbabilisticModel()
        try:
            model.load(MODELOS_DIR)
            if model._probas is None:
                raise RuntimeError("not loaded")
        except Exception:
            model.fit(draws)
        probas = model.predict_proba()
        if probas.sum() > 0:
            probas /= probas.sum()
        return probas
    except Exception as e:
        print(f"    [yellow]ProbabilisticModel falhou: {e}[/yellow]")
        return None


def _get_frequency_ensemble_probas(draws: List[Sorteio]) -> Optional[np.ndarray]:
    try:
        from lotofacil.infra.modelos.frequency_ensemble import FrequencyEnsembleModel
        model = FrequencyEnsembleModel()
        try:
            model.load(MODELOS_DIR)
            if model._probas is None:
                raise RuntimeError("not loaded")
        except Exception:
            model.fit(draws)
        probas = model.predict_proba()
        if probas.sum() > 0:
            probas /= probas.sum()
        return probas
    except Exception as e:
        print(f"    [yellow]FrequencyEnsembleModel falhou: {e}[/yellow]")
        return None


def _get_ml_ensemble_probas(draws: List[Sorteio]) -> Optional[np.ndarray]:
    try:
        from lotofacil.infra.modelos.ml_model import MLEnsembleModel
        model = MLEnsembleModel()
        try:
            model.load(MODELOS_DIR)
            if model._model is None:
                raise RuntimeError("not loaded")
        except Exception:
            model.fit(draws)
        probas = model.predict_proba()
        if probas.sum() > 0:
            probas /= probas.sum()
        return probas
    except Exception as e:
        print(f"    [yellow]MLEnsembleModel falhou: {e}[/yellow]")
        return None


def collect_all_probabilities(draws: List[Sorteio]) -> tuple:
    """Collect probability arrays from all available strategies and models."""
    strategies = {}

    strategies["EnsemblePredictor"] = _get_ensemble_predictor_probas(draws)
    strategies["ElevenNumbersStrategy"] = _get_eleven_strategy_probas(draws)
    strategies["QuinzeEnsemble"] = _get_quinze_ensemble_probas(draws)
    strategies["ProbabilisticModel"] = _get_probabilistic_probas(draws)
    strategies["FrequencyEnsembleModel"] = _get_frequency_ensemble_probas(draws)
    strategies["MLEnsembleModel"] = _get_ml_ensemble_probas(draws)

    active = {k: v for k, v in strategies.items() if v is not None}
    if not active:
        raise RuntimeError("Nenhuma estratégia conseguiu gerar probabilidades.")

    weights = {
        "EnsemblePredictor": 0.25,
        "ElevenNumbersStrategy": 0.25,
        "QuinzeEnsemble": 0.20,
        "ProbabilisticModel": 0.10,
        "FrequencyEnsembleModel": 0.10,
        "MLEnsembleModel": 0.10,
    }
    combined = np.zeros(TOTAL_NUMEROS, dtype=np.float64)
    total_w = 0.0
    for name, probas in active.items():
        w = weights.get(name, 0.15)
        combined += w * probas
        total_w += w
    combined /= total_w

    consensus = np.zeros(TOTAL_NUMEROS, dtype=np.int32)
    for probas in active.values():
        top15 = set(np.argsort(probas)[::-1][:15] + 1)
        for n in top15:
            consensus[n - 1] += 1

    return combined, active, consensus


# ── Candidate generation strategies ────────────────────────────────────────────

def _generate_weighted_sampling(
    probas: np.ndarray, n: int, rng: random.Random
) -> List[List[int]]:
    candidates = []
    seen = set()
    p = probas / probas.sum()
    rng_np = np.random.default_rng(42)
    attempts = 0
    while len(candidates) < n and attempts < n * 20:
        cand = tuple(sorted(rng_np.choice(range(1, 26), size=15, replace=False, p=p).tolist()))
        if cand not in seen:
            seen.add(cand)
            candidates.append(list(cand))
        attempts += 1
    return candidates


def _generate_core_fill(
    probas: np.ndarray, last_draw: List[int], n: int, rng: random.Random
) -> List[List[int]]:
    ranked = [int(x) for x in np.argsort(probas)[::-1] + 1]
    core = ranked[:11]
    pool = ranked[11:]
    candidates = []
    seen = set()
    for _ in range(n * 3):
        if len(candidates) >= n:
            break
        fill = [int(x) for x in sorted(rng.sample(pool, 4))]
        game = tuple(sorted(core + fill))
        if game not in seen:
            seen.add(game)
            candidates.append(list(game))
    return candidates[:n]


def _generate_simulated_annealing(
    probas: np.ndarray, last_draw: List[int], n: int, rng: random.Random
) -> List[List[int]]:
    all_numbers = set(range(1, 26))
    candidates = []
    seen = set()

    for i in range(n):
        seed_val = 42 + i * 7
        local_rng = random.Random(seed_val)

        initial = set(int(x) for x in (np.argsort(probas)[::-1][:15] + 1))
        n_swaps = local_rng.randint(1, 2)
        for _ in range(n_swaps):
            remove = local_rng.choice(sorted(initial))
            initial.remove(remove)
            available = [n for n in all_numbers if n not in initial]
            initial.add(local_rng.choice(available))

        current = set(initial)
        current_score = _filter_weighted_score(sorted(current), last_draw)
        best = set(current)
        best_score = current_score

        temp = 3.0
        n_iters = 1500

        for _ in range(n_iters):
            if temp < 0.01:
                break
            curr_list = sorted(current)
            outside = sorted(all_numbers - current)
            remove_num = local_rng.choice(curr_list)
            add_num = local_rng.choice(outside)
            neighbor = set(current)
            neighbor.remove(remove_num)
            neighbor.add(add_num)
            neighbor_score = _filter_weighted_score(sorted(neighbor), last_draw)
            delta = neighbor_score - current_score
            if delta > 0:
                current = neighbor
                current_score = neighbor_score
                if current_score > best_score:
                    best = set(current)
                    best_score = current_score
            else:
                if local_rng.random() < math.exp(delta / temp):
                    current = neighbor
                    current_score = neighbor_score
            temp *= 0.995

        result = tuple(sorted(best))
        if result not in seen:
            seen.add(result)
            candidates.append([int(x) for x in result])

    return candidates


def _generate_filter_guided(
    probas: np.ndarray, last_draw: List[int], n: int, rng: random.Random
) -> List[List[int]]:
    all_numbers = list(range(1, 26))
    candidates = []
    seen = set()

    for _ in range(n):
        base = sorted(rng.sample(all_numbers, TARGET_COUNT))
        cand = set(base)
        n_swaps = rng.randint(1, 5)
        for _ in range(n_swaps):
            current_list = sorted(cand)
            score_before = _filter_weighted_score(current_list, last_draw)

            best_swap = None
            best_delta = -float("inf")
            for _ in range(3):
                remove = rng.choice(current_list)
                add = rng.choice([n for n in all_numbers if n not in cand])
                neighbor = set(cand)
                neighbor.remove(remove)
                neighbor.add(add)
                score_after = _filter_weighted_score(sorted(neighbor), last_draw)
                delta = score_after - score_before
                if delta > best_delta:
                    best_delta = delta
                    best_swap = (remove, add)

            if best_swap and best_delta > 0:
                cand.remove(best_swap[0])
                cand.add(best_swap[1])

        result = tuple(sorted(cand))
        if result not in seen:
            seen.add(result)
            candidates.append(list(result))

    return candidates


def _generate_random_filtered(
    probas: np.ndarray, last_draw: List[int], n: int, rng: random.Random
) -> List[List[int]]:
    candidates = []
    seen = set()
    attempts = 0
    while len(candidates) < n and attempts < n * 50:
        cand = sorted(rng.sample(range(1, 26), TARGET_COUNT))
        score = _game_quality_score(cand, last_draw)
        if score >= 4.0 / 7.0:
            key = tuple(cand)
            if key not in seen:
                seen.add(key)
                candidates.append(cand)
        attempts += 1
    return candidates


def generate_candidates(
    probas: np.ndarray, last_draw: List[int], rng: random.Random
) -> tuple:
    """Generate 10,000 candidates using diverse strategies."""
    n_total = N_CANDIDATES
    strategies_generation = {}

    n1 = int(n_total * 0.55)
    c1 = _generate_weighted_sampling(probas, n1, rng)
    strategies_generation["weighted_sampling"] = len(c1)
    all_candidates = c1

    n2 = int(n_total * 0.25)
    c2 = _generate_core_fill(probas, last_draw, n2, rng)
    strategies_generation["core_fill"] = len(c2)
    all_candidates.extend(c2)

    n3 = int(n_total * 0.08)
    c3 = _generate_simulated_annealing(probas, last_draw, n3, rng)
    strategies_generation["simulated_annealing"] = len(c3)
    all_candidates.extend(c3)

    n4 = int(n_total * 0.07)
    c4 = _generate_filter_guided(probas, last_draw, n4, rng)
    strategies_generation["filter_guided"] = len(c4)
    all_candidates.extend(c4)

    n5 = n_total - len(all_candidates)
    if n5 > 0:
        c5 = _generate_random_filtered(probas, last_draw, n5, rng)
        strategies_generation["random_filtered"] = len(c5)
        all_candidates.extend(c5)

    return all_candidates[:n_total], strategies_generation


# ── Scoring and ranking ────────────────────────────────────────────────────────

def score_and_rank(
    candidates: List[List[int]],
    probas: np.ndarray,
    consensus: np.ndarray,
    last_draw: List[int],
    active_strategies: dict,
) -> List[dict]:
    """Score all candidates and return top-3 with diversity constraint."""
    max_proba = np.max(probas) if np.max(probas) > 0 else 1
    max_consensus = len(active_strategies)

    scored = []
    for game in candidates:
        proba_sum = sum(probas[n - 1] for n in game)
        proba_score_norm = proba_sum / (TARGET_COUNT * max_proba)

        filter_score_raw = _filter_weighted_score(game, last_draw)
        filter_score_norm = filter_score_raw / TOTAL_FILTER_WEIGHT

        consensus_sum = sum(consensus[n - 1] for n in game)
        consensus_norm = consensus_sum / (TARGET_COUNT * max_consensus)

        quality_score = _game_quality_score(game, last_draw)

        combined = (
            proba_score_norm * 0.35
            + filter_score_norm * 0.25
            + consensus_norm * 0.25
            + quality_score * 0.15
        )

        scored.append({
            "game": game,
            "combined_score": round(combined, 4),
            "proba_score": round(proba_score_norm, 4),
            "filter_score": round(filter_score_norm, 4),
            "consensus_score": round(consensus_norm, 4),
            "quality_score": round(quality_score, 4),
            "filter_raw": round(filter_score_raw, 2),
        })

    scored.sort(key=lambda x: (-x["combined_score"], -x["proba_score"]))

    top = [scored[0]]
    for entry in scored[1:]:
        if len(top) >= 3:
            break
        n_shared = max(len(set(entry["game"]) & set(t["game"])) for t in top)
        if n_shared < 12:
            top.append(entry)

    return top


# ── Main service ───────────────────────────────────────────────────────────────

def gerar_campeao(concurso: int) -> ResultadoCampeao:
    """Generate champion game for the given concurso using all strategies."""
    from rich.console import Console
    console = Console()

    console.print(f"\n[bold][1/5] Carregando sorteios anteriores ao concurso {concurso}...[/bold]")
    draws = load_draws(DADOS_DIR)
    draws = [d for d in draws if d.concurso < concurso]
    if not draws:
        raise ValueError(f"Nenhum sorteio anterior ao concurso {concurso} encontrado")
    console.print(f"  {len(draws)} concursos ({draws[0].concurso} \u2192 {draws[-1].concurso})")
    last_draw = draws[-1].dezenas
    ultimo_concurso = draws[-1].concurso

    console.print(f"\n[bold][2/5] Coletando probabilidades de todas as estrat\u00e9gias...[/bold]")
    probas_combined, active_strategies, consensus = collect_all_probabilities(draws)
    active_names = list(active_strategies.keys())
    console.print(f"  Estrat\u00e9gias ativas: {', '.join(active_names)}")
    ranked = [int(x) for x in np.argsort(probas_combined)[::-1] + 1]
    console.print(f"  Top 15 (peso combinado): {sorted(ranked[:15])}")
    top5_consensus = sorted(
        [(i + 1, int(c)) for i, c in enumerate(consensus)],
        key=lambda x: -x[1]
    )[:5]
    console.print(f"  Consenso entre modelos: {top5_consensus}")

    console.print(f"\n[bold][3/5] Gerando {N_CANDIDATES} candidatos...[/bold]")
    rng = random.Random(42)
    candidates, gen_map = generate_candidates(probas_combined, last_draw, rng)
    console.print(f"  Gerados: {len(candidates)} jogos \u00fanicos")
    for strat, count in gen_map.items():
        console.print(f"    {strat}: {count}")

    console.print(f"\n[bold][4/5] Pontuando e ranqueando...[/bold]")
    top_3 = score_and_rank(candidates, probas_combined, consensus, last_draw, active_strategies)
    console.print(f"  Top 3 selecionados com diversidade (< 12 n\u00fameros compartilhados)")

    console.print(f"\n[bold][5/5] Salvando resultado...[/bold]")
    out_data = {
        "concurso_alvo": concurso,
        "total_candidatos": N_CANDIDATES,
        "estrategias_ativas": active_names,
        "ultimo_concurso": ultimo_concurso,
        "top_3": [
            {
                "posicao": i + 1,
                "dezenas": sorted(e["game"]),
                "combined_score": e["combined_score"],
                "proba_score": e["proba_score"],
                "filter_score": e["filter_score"],
                "consensus_score": e["consensus_score"],
                "quality_score": e["quality_score"],
                "filtros": {
                    "soma": sum(e["game"]),
                    "pares": f"{sum(1 for n in e['game'] if n % 2 == 0)}P/{TARGET_COUNT - sum(1 for n in e['game'] if n % 2 == 0)}I",
                    "repetidos": len(set(e["game"]) & set(last_draw)),
                    "moldura": sum(1 for n in e['game'] if n in _MOLDURA),
                    "primos": sum(1 for n in e['game'] if n in _PRIMOS),
                    "fibonacci": sum(1 for n in e['game'] if n in _FIBONACCI),
                    "consecutivos": sum(
                        1 for i in range(len(sorted(e['game'])) - 1)
                        if sorted(e['game'])[i + 1] == sorted(e['game'])[i] + 1
                    ),
                },
                "qualidade": round(e["quality_score"] * 7),
            }
            for i, e in enumerate(top_3)
        ],
    }

    class _NumpyEncoder(json.JSONEncoder):
        def default(self, obj: Any) -> Any:
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.ndarray,)):
                return obj.tolist()
            return super().default(obj)

    out_path = JOGOS_DIR / f"campeao_{concurso}.json"
    out_path.write_text(
        json.dumps(out_data, ensure_ascii=False, indent=2, cls=_NumpyEncoder),
        encoding="utf-8",
    )
    console.print(f"  [dim]Salvo em {out_path}[/dim]")

    return ResultadoCampeao(
        concurso_alvo=concurso,
        top_3=out_data["top_3"],
        estrategias_ativas=active_names,
        ultimo_concurso=ultimo_concurso,
    )
