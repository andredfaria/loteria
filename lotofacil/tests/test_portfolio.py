"""Tests for cli/portfolio.py"""
import json
import sys
import tempfile
from pathlib import Path

_LOTOFACIL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_LOTOFACIL / "src"))

import cli.portfolio as m


def test_cost_per_game_is_3_50_core():
    from core.config import COST_PER_GAME
    assert COST_PER_GAME == 3.50


def test_cost_per_game_is_3_50_ml():
    from lotofacil_ml.config import COST_PER_GAME
    assert COST_PER_GAME == 3.50


def test_distribute_games_five():
    c, e, a = m.distribute_games(5)
    assert c + e + a == 5
    assert c >= e >= a >= 1


def test_distribute_games_eight():
    c, e, a = m.distribute_games(8)
    assert c + e + a == 8
    assert c >= e >= a >= 1


def test_distribute_games_one():
    c, e, a = m.distribute_games(1)
    assert c + e + a == 1


def test_game_quality_score_bounds():
    score = m.game_quality_score(
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    )
    assert 0.0 <= score <= 1.0


def test_game_quality_score_good_game():
    game = [1, 3, 4, 5, 6, 7, 9, 10, 12, 13, 15, 16, 17, 18, 21]
    last = [2, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 17, 20, 22]
    score = m.game_quality_score(game, last)
    assert 0.0 <= score <= 1.0


def test_load_draws_from_files_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = m.load_draws_from_files(Path(tmpdir), max_concurso=9999)
    assert result == []


def test_load_draws_from_files_respects_max_concurso():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        for n, dezenas in [(100, list(range(1, 16))), (200, list(range(2, 17)))]:
            (d / f"concurso_{n}.json").write_text(
                json.dumps({
                    "concurso": n,
                    "data": "01/01/2020",
                    "dezenas": [str(x).zfill(2) for x in dezenas],
                })
            )
        draws = m.load_draws_from_files(d, max_concurso=200)
    assert len(draws) == 1
    assert draws[0].concurso == 100


def test_load_draws_sorted_by_concurso():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        for n, dezenas in [(300, list(range(3, 18))), (100, list(range(1, 16)))]:
            (d / f"concurso_{n}.json").write_text(
                json.dumps({
                    "concurso": n,
                    "data": "01/01/2020",
                    "dezenas": [str(x).zfill(2) for x in dezenas],
                })
            )
        draws = m.load_draws_from_files(d, max_concurso=9999)
    assert draws[0].concurso == 100
    assert draws[1].concurso == 300


def test_get_probabilities_shape_and_sum():
    draws = m.load_draws_from_files(
        _LOTOFACIL / "dados" / "sample",
        max_concurso=9999,
    )
    assert len(draws) >= 10
    probas = m.get_probabilities(draws)
    assert probas.shape == (25,)
    assert abs(probas.sum() - 1.0) < 1e-4
    assert all(probas >= 0)


def test_get_probabilities_top11_unique():
    import numpy as np
    draws = m.load_draws_from_files(
        _LOTOFACIL / "dados" / "sample",
        max_concurso=9999,
    )
    probas = m.get_probabilities(draws)
    top11 = list(np.argsort(probas)[::-1][:11] + 1)
    assert len(set(top11)) == 11
    assert all(1 <= n <= 25 for n in top11)


def test_generate_games_for_tier_count():
    core = list(range(1, 12))
    fill_pool = list(range(12, 18))
    last_draw = list(range(1, 16))
    games = m.generate_games_for_tier(core, fill_pool, n_games=3, last_draw=last_draw)
    assert len(games) == 3


def test_generate_games_for_tier_each_game_has_15():
    core = list(range(1, 12))
    fill_pool = list(range(12, 20))
    last_draw = list(range(1, 16))
    games = m.generate_games_for_tier(core, fill_pool, n_games=2, last_draw=last_draw)
    for game in games:
        assert len(game) == 15
        assert len(set(game)) == 15
        assert all(1 <= n <= 25 for n in game)


def test_generate_games_for_tier_contains_core():
    core = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21]
    fill_pool = [2, 4, 6, 8, 10, 12, 14, 16]
    last_draw = list(range(1, 16))
    games = m.generate_games_for_tier(core, fill_pool, n_games=2, last_draw=last_draw)
    for game in games:
        assert all(n in game for n in core)


def test_build_portfolio_structure():
    core = list(range(1, 12))
    ranked = list(range(1, 26))
    last_draw = list(range(1, 16))
    portfolio = m.build_portfolio(core, ranked, n_games=5, last_draw=last_draw)
    assert "conservador" in portfolio
    assert "equilibrado" in portfolio
    assert "agressivo" in portfolio
    total = sum(len(v) for v in portfolio.values())
    assert total == 5


def test_print_portfolio_runs_without_error():
    portfolio = {
        "conservador": [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]],
        "equilibrado": [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16]],
        "agressivo": [],
    }
    # Rich Console writes to stdout; just verify no exception is raised
    m.print_portfolio(portfolio, n_jogos=2, target_concurso=3675)
