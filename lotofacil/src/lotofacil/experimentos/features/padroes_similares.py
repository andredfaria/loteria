"""Score combinado: similaridade lua+clima + padroes_21 + geracao do jogo."""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from lotofacil.experimentos.config import (
    SIMILARITY_TOP_N, PROJECT_ROOT, PADROES21_JANELA,
    SCORE_SIMILAR_WEIGHT, SCORE_PADROES21_WEIGHT,
    STRATEGY_RANGES,
)
from lotofacil.experimentos.features.similarity import (
    find_similar, compute_similarity_weighted_freq,
    get_target_moon, get_target_climate,
)

logger = logging.getLogger(__name__)


def calcular_score_padroes21(
    draws, janela: int = PADROES21_JANELA
) -> np.ndarray:
    """Reimplementação de ml/padroes_21.py para objetos Draw.

    Score de 5 padrões para cada número 1-25, normalizado [0,1].
    """
    if not draws:
        return np.ones(25, dtype=np.float32) * 0.5

    if len(draws) > janela:
        ultimos = draws[-janela:]
    else:
        ultimos = draws

    n_draws = len(ultimos)
    ultimo_set = set(ultimos[-1].dezenas)
    recentes3: set = set()
    for d in ultimos[-3:]:
        recentes3.update(d.dezenas)

    scores = []
    for num in range(1, 26):
        freq = sum(1 for d in ultimos if num in d.dezenas) / n_draws
        repeticao = 1.0 if num in ultimo_set else 0.0

        atraso_raw = n_draws
        for i, d in enumerate(reversed(ultimos)):
            if num in d.dezenas:
                atraso_raw = i
                break
        atraso = 1.0 - min(atraso_raw / n_draws, 1.0)

        ciclo = 1.0 if num not in recentes3 else 0.0

        consecutivo = 0.0
        for viz in [num - 1, num + 1]:
            if 1 <= viz <= 25:
                freq_viz = sum(1 for d in ultimos if viz in d.dezenas) / n_draws
                if freq_viz >= 0.6:
                    consecutivo = 1.0
                    break

        score = (
            0.30 * freq
            + 0.25 * repeticao
            + 0.20 * atraso
            + 0.15 * ciclo
            + 0.10 * consecutivo
        )
        scores.append(score)

    arr = np.array(scores, dtype=np.float32)
    lo, hi = arr.min(), arr.max()
    if hi > lo:
        return (arr - lo) / (hi - lo)
    return np.full(25, 0.5, dtype=np.float32)


def _contar_pares(jogo: List[int]) -> int:
    return sum(1 for n in jogo if n % 2 == 0)


def _contar_moldura(jogo: List[int]) -> int:
    return sum(1 for n in jogo if n <= 5 or n >= 21)


def _contar_primos(jogo: List[int]) -> int:
    PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
    return sum(1 for n in jogo if n in PRIMOS)


def _contar_fibonacci(jogo: List[int]) -> int:
    FIB = {1, 2, 3, 5, 8, 13, 21}
    return sum(1 for n in jogo if n in FIB)


def _tem_consecutivo(jogo: List[int]) -> bool:
    nums = sorted(jogo)
    return any(nums[i + 1] == nums[i] + 1 for i in range(len(nums) - 1))


def _aplicar_filtro_soma(jogo: List[int]) -> List[int]:
    dentro = list(jogo)
    fora = sorted(set(range(1, 26)) - set(dentro))
    soma = sum(dentro)
    tentativas = 0

    while soma < 171 and fora and tentativas < 50:
        maiores = [n for n in fora if n > min(dentro)]
        if not maiores:
            break
        sai = min(dentro)
        entra = min(maiores)
        dentro.remove(sai)
        fora.remove(entra)
        fora.append(sai)
        dentro.append(entra)
        soma = sum(dentro)
        tentativas += 1

    tentativas = 0
    while soma > 220 and fora and tentativas < 50:
        menores = [n for n in fora if n < max(dentro)]
        if not menores:
            break
        sai = max(dentro)
        entra = max(menores)
        dentro.remove(sai)
        fora.remove(entra)
        fora.append(sai)
        dentro.append(entra)
        soma = sum(dentro)
        tentativas += 1

    return sorted(dentro)


def _aplicar_filtro_consecutivo(jogo: List[int]) -> List[int]:
    if _tem_consecutivo(jogo):
        return jogo
    fora = sorted(set(range(1, 26)) - set(jogo))
    for n in sorted(jogo):
        for viz in [n - 1, n + 1]:
            if 1 <= viz <= 25 and viz in fora:
                dentro = list(jogo)
                dentro.remove(n)
                dentro.append(viz)
                return sorted(dentro)
    return jogo


def gerar_jogo(
    score_final: np.ndarray,
    target_numbers: int = 15,
) -> List[int]:
    top = np.argsort(score_final)[::-1][:target_numbers]
    jogo = sorted(int(i + 1) for i in top)

    jogo = _aplicar_filtro_soma(jogo)
    jogo = _aplicar_filtro_consecutivo(jogo)

    return jogo


def gerar_jogo_com_similares(
    draws,
    target_date_iso: str = "",
    top_n: int = SIMILARITY_TOP_N,
    peso_similar: float = SCORE_SIMILAR_WEIGHT,
    peso_padroes21: float = SCORE_PADROES21_WEIGHT,
    target_concurso: int = 0,
) -> Dict:
    if not target_date_iso:
        target_date_iso = date.today().isoformat()

    similar_results = find_similar(
        draws,
        target_date_iso=target_date_iso,
        top_n=top_n,
    )

    score_padroes21 = calcular_score_padroes21(draws)

    if similar_results:
        score_similar = compute_similarity_weighted_freq(similar_results)
        logger.info(
            "Top similares: %s | Peso similar=%.1f / padroes21=%.1f",
            [r["concurso"] for r in similar_results],
            peso_similar, peso_padroes21,
        )
    else:
        score_similar = np.ones(25, dtype=np.float32) * 0.5
        logger.warning("Nenhum similar encontrado, usando score neutro.")

    total_weight = peso_similar + peso_padroes21
    if total_weight == 0:
        total_weight = 1.0

    score_final = (
        (peso_similar / total_weight) * score_similar
        + (peso_padroes21 / total_weight) * score_padroes21
    )

    jogo = gerar_jogo(score_final)

    result = {
        "metodo": "similaridade_lua_clima",
        "data_alvo": target_date_iso,
        "target_concurso": target_concurso,
        "lua_hoje": {
            k: round(float(v), 4)
            for k, v in zip(
                ["phase", "phase_sin", "phase_cos", "illumination",
                 "age_norm", "is_new", "is_full"],
                get_target_moon(target_date_iso).tolist(),
            )
        },
        "clima_hoje": {
            k: round(float(v), 4)
            for k, v in zip(
                ["temp_min", "temp_max", "temp_media", "temp_sorteio",
                 "precip_media", "precip_sorteio", "wcode_sorteio", "wcode_dominant"],
                get_target_climate(target_date_iso).tolist(),
            )
        },
        "top_similares": [
            {
                "rank": r["rank"],
                "concurso": r["concurso"],
                "data": r["data"],
                "similaridade": r["similaridade"],
                "distancia_total": round(r["distancia_total"], 4),
            }
            for r in (similar_results or [])
        ],
        "pesos": {
            "similaridade": peso_similar,
            "padroes21": peso_padroes21,
        },
        "dezenas": jogo,
        "soma": sum(jogo),
        "pares": _contar_pares(jogo),
        "moldura": _contar_moldura(jogo),
        "primos": _contar_primos(jogo),
        "fibonacci": _contar_fibonacci(jogo),
        "consecutivo": _tem_consecutivo(jogo),
    }

    return result


def salvar_jogo(result: Dict) -> Path:
    concurso = result.get("target_concurso", 0)
    saida = PROJECT_ROOT / "saida" / "jogos"
    saida.mkdir(parents=True, exist_ok=True)

    path = saida / f"similar_{concurso}.json" if concurso else saida / "similar_hoje.json"
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Jogo salvo em %s", path)
    return path
