"""Similarity search engine: find historical draws with moon+climate similar to target."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Dict, List, Tuple

import numpy as np

from lotofacil.experimentos.config import (
    SIMILARITY_TOP_N, SIMILARITY_MOON_WEIGHT, SIMILARITY_CLIMATE_WEIGHT,
    SIMILARITY_MIN_DRAWS, SRC_DIR,
)
from lotofacil.experimentos.data.lunar_loader import (
    compute_lunar_features, _parse_iso, LUNAR_FEATURE_NAMES,
)
from lotofacil.experimentos.data.climate_loader import CLIMATE_FEATURE_NAMES

logger = logging.getLogger(__name__)

N_LUNAR = len(LUNAR_FEATURE_NAMES)
N_CLIMATE = len(CLIMATE_FEATURE_NAMES)
N_TOTAL = N_LUNAR + N_CLIMATE

_climate_cache: Dict[str, np.ndarray] = {}


def _normalize(arr: np.ndarray) -> np.ndarray:
    lo = arr.min(axis=0)
    hi = arr.max(axis=0)
    denom = hi - lo
    denom[denom == 0] = 1.0
    return (arr - lo) / denom


def get_target_moon(date_iso: str) -> np.ndarray:
    return compute_lunar_features(date_iso)


def get_target_climate(date_iso: str) -> np.ndarray:
    if date_iso in _climate_cache:
        return _climate_cache[date_iso]
    from lotofacil.experimentos.data.climate_loader import fetch_climate_from_api, normalize_climate
    resumo = fetch_climate_from_api(date_iso)
    if resumo:
        arr = np.array(normalize_climate(resumo), dtype=np.float32)
    else:
        logger.warning("Climate API failed for %s, using zeros", date_iso)
        arr = np.zeros(N_CLIMATE, dtype=np.float32)
    _climate_cache[date_iso] = arr
    return arr


def build_historical_matrices(draws) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List]:
    lunar_list = []
    climate_list = []
    mask = []
    valid_draws = []

    from lotofacil.experimentos.data.climate_loader import load_all_climate, normalize_climate
    climate_map = load_all_climate()

    for d in draws:
        iso = _parse_iso(d.data)
        if not iso:
            mask.append(False)
            continue
        moon = compute_lunar_features(iso)

        resumo = climate_map.get(d.concurso)
        if resumo is None:
            mask.append(False)
            continue

        clim = np.array(normalize_climate(resumo), dtype=np.float32)
        lunar_list.append(moon)
        climate_list.append(clim)
        mask.append(True)
        valid_draws.append(d)

    if not lunar_list:
        logger.warning("No draws with both lunar and climate data found.")
        return (
            np.zeros((0, N_LUNAR), dtype=np.float32),
            np.zeros((0, N_CLIMATE), dtype=np.float32),
            np.array(mask, dtype=bool),
            [],
        )

    return (
        np.array(lunar_list, dtype=np.float32),
        np.array(climate_list, dtype=np.float32),
        np.array(mask, dtype=bool),
        valid_draws,
    )


def find_similar(
    draws,
    target_date_iso: str = "",
    top_n: int = SIMILARITY_TOP_N,
    moon_weight: float = SIMILARITY_MOON_WEIGHT,
    climate_weight: float = SIMILARITY_CLIMATE_WEIGHT,
) -> List[Dict]:
    if not target_date_iso:
        target_date_iso = date.today().isoformat()

    target_moon = get_target_moon(target_date_iso)
    target_climate = get_target_climate(target_date_iso)

    lunar_mat, climate_mat, mask, valid_draws = build_historical_matrices(draws)
    n_valid = len(valid_draws)

    if n_valid == 0:
        logger.warning("No valid draws for similarity search.")
        return []

    logger.info(
        "Target moon+climate: lunar=[%s] climate=[%s]",
        ", ".join(f"{v:.3f}" for v in target_moon),
        ", ".join(f"{v:.3f}" for v in target_climate),
    )

    moon_stack = np.vstack([target_moon, lunar_mat])
    clim_stack = np.vstack([target_climate, climate_mat])

    moon_norm = _normalize(moon_stack)
    clim_norm = _normalize(clim_stack)

    target_m_norm = moon_norm[0]
    target_c_norm = clim_norm[0]
    hist_m_norm = moon_norm[1:]
    hist_c_norm = clim_norm[1:]

    moon_dist = np.linalg.norm(hist_m_norm - target_m_norm, axis=1)
    clim_dist = np.linalg.norm(hist_c_norm - target_c_norm, axis=1)

    weights_sum = moon_weight + climate_weight
    if weights_sum == 0:
        weights_sum = 1.0

    combined = (
        (moon_weight / weights_sum) * moon_dist
        + (climate_weight / weights_sum) * clim_dist
    )

    sorted_idx = np.argsort(combined)
    n_select = min(top_n, n_valid)
    selected = sorted_idx[:n_select]

    results = []
    for rank, idx in enumerate(selected, 1):
        d = valid_draws[idx]
        sim_score = float(1.0 / (1.0 + combined[idx]))
        results.append({
            "rank": rank,
            "concurso": d.concurso,
            "data": d.data,
            "dezenas": d.dezenas,
            "distancia_lua": float(moon_dist[idx]),
            "distancia_clima": float(clim_dist[idx]),
            "distancia_total": float(combined[idx]),
            "similaridade": round(sim_score, 4),
        })

    logger.info(
        "Top-%d similar draws to %s: %s",
        n_select, target_date_iso,
        [r["concurso"] for r in results],
    )
    return results


def compute_similarity_weighted_freq(
    similar_results: List[Dict], n_numbers: int = 25
) -> np.ndarray:
    if not similar_results:
        return np.ones(n_numbers, dtype=np.float32) * 0.5

    scores = np.zeros(n_numbers, dtype=np.float64)
    total_weight = 0.0

    for r in similar_results:
        sim = r["similaridade"]
        for num in r["dezenas"]:
            scores[num - 1] += sim
        total_weight += sim

    if total_weight > 0:
        scores /= total_weight

    lo, hi = scores.min(), scores.max()
    if hi > lo:
        scores = (scores - lo) / (hi - lo)
    else:
        scores[:] = 0.5

    return scores.astype(np.float32)
