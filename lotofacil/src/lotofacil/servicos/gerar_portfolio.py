from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import numpy as np

from lotofacil.dominio.entidades import Portfolio, Sorteio
from lotofacil.infra.config import DADOS_DIR, JOGOS_DIR
from lotofacil.infra.dados.leitor import load_draws
from lotofacil.infra.estrategias.onze_dezenas.predictor import ElevenNumbersStrategy

COST_PER_GAME = 3.50

_PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
_FIBONACCI = {1, 2, 3, 5, 8, 13, 21}
_MOLDURA = {1, 2, 3, 4, 5, 21, 22, 23, 24, 25}

_DIST_TABLE = {
    1: (1, 0, 0), 2: (2, 0, 0), 3: (1, 1, 1),
    4: (2, 1, 1), 5: (2, 2, 1), 6: (2, 2, 2),
    7: (3, 2, 2), 8: (3, 3, 2), 9: (3, 3, 3),
    10: (4, 3, 3),
}


@dataclass(frozen=True)
class ResultadoPortfolio:
    concurso_alvo: int
    conservador: List[List[int]]
    equilibrado: List[List[int]]
    agressivo: List[List[int]]
    total_jogos: int = field(init=False)
    custo_total: float = field(init=False)

    def __post_init__(self):
        total = len(self.conservador) + len(self.equilibrado) + len(self.agressivo)
        object.__setattr__(self, "total_jogos", total)
        object.__setattr__(self, "custo_total", total * COST_PER_GAME)

    @property
    def todos_jogos(self) -> List[List[int]]:
        return self.conservador + self.equilibrado + self.agressivo


def _distribute_games(n: int):
    if n in _DIST_TABLE:
        return _DIST_TABLE[n]
    a = max(1, n // 4)
    c = max(1, round(n * 0.4))
    e = n - c - a
    if e < 0:
        e = 0
        c = n - a
    return (c, e, a)


def _game_quality_score(game: List[int], last_draw: List[int]) -> float:
    passed = 0
    pares = sum(1 for n in game if n % 2 == 0)
    if (pares, 15 - pares) in {(7, 8), (8, 7), (6, 9), (9, 6)}:
        passed += 1
    soma = sum(game)
    if 171 <= soma <= 220:
        passed += 1
    if 8 <= sum(1 for n in game if n in _MOLDURA) <= 11:
        passed += 1
    if 4 <= sum(1 for n in game if n in _PRIMOS) <= 7:
        passed += 1
    if 3 <= sum(1 for n in game if n in _FIBONACCI) <= 5:
        passed += 1
    s = sorted(game)
    if any(s[i + 1] == s[i] + 1 for i in range(len(s) - 1)):
        passed += 1
    if 8 <= sum(1 for n in game if n in set(last_draw)) <= 10:
        passed += 1
    return passed / 7


def _generate_games_for_tier(
    core: List[int],
    fill_pool: List[int],
    n_games: int,
    last_draw: List[int],
) -> List[List[int]]:
    if n_games == 0:
        return []
    import itertools

    core_set = set(core)
    effective_pool = [n for n in fill_pool if n not in core_set]
    if len(effective_pool) < 4:
        extras = [n for n in range(1, 26) if n not in core_set and n not in effective_pool]
        effective_pool = effective_pool + extras
    effective_pool = effective_pool[:20]

    candidates = []
    seen = set()
    for fill in itertools.combinations(effective_pool, 4):
        game = sorted(list(core) + list(fill))
        key = tuple(game)
        if key in seen:
            continue
        seen.add(key)
        candidates.append((_game_quality_score(game, last_draw), game))

    candidates.sort(key=lambda x: (-x[0], x[1]))

    chosen = []
    used_fills = []
    for score, game in candidates:
        fills = frozenset(n for n in game if n not in core_set)
        if all(len(fills & prev) < 4 for prev in used_fills):
            chosen.append(game)
            used_fills.append(fills)
        if len(chosen) == n_games:
            break

    for score, game in candidates:
        if len(chosen) >= n_games:
            break
        if game not in chosen:
            chosen.append(game)

    return chosen[:n_games]


def _build_portfolio_dict(
    core: List[int],
    ranked: List[int],
    n_games: int,
    last_draw: List[int],
) -> dict:
    n_c, n_e, n_a = _distribute_games(n_games)
    return {
        "conservador": _generate_games_for_tier(core, ranked[11:17], n_c, last_draw),
        "equilibrado": _generate_games_for_tier(core, ranked[11:22], n_e, last_draw),
        "agressivo": _generate_games_for_tier(core, ranked[11:25], n_a, last_draw),
    }


def _get_probabilities(draws: List[Sorteio]) -> np.ndarray:
    predictor = ElevenNumbersStrategy()
    pred = predictor.predict(draws, approach="all")
    probas = np.array(pred.probabilidades, dtype=np.float64)
    if probas.sum() > 0:
        probas /= probas.sum()
    return probas


def gerar_portfolio(jogos: int = 4, concurso: int | None = None) -> ResultadoPortfolio:
    if concurso is None:
        existing = sorted(
            int(f.stem.split("_")[1])
            for f in DADOS_DIR.glob("concurso_*.json")
            if f.stem.split("_")[1].isdigit()
        )
        concurso = (existing[-1] + 1) if existing else 1

    draws = load_draws(DADOS_DIR)
    draws = [d for d in draws if d.concurso < concurso]
    if not draws:
        raise ValueError(f"Nenhum sorteio anterior ao concurso {concurso} encontrado")

    last_draw = draws[-1].dezenas
    probas = _get_probabilities(draws)
    ranked = [int(x) for x in np.argsort(probas)[::-1] + 1]
    core = ranked[:11]

    portfolio_dict = _build_portfolio_dict(core, ranked, jogos, last_draw)

    resultado = ResultadoPortfolio(
        concurso_alvo=concurso,
        conservador=portfolio_dict["conservador"],
        equilibrado=portfolio_dict["equilibrado"],
        agressivo=portfolio_dict["agressivo"],
    )

    out = JOGOS_DIR / f"portfolio_{concurso}.json"
    out.write_text(
        json.dumps(portfolio_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return resultado
