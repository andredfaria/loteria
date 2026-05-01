"""Tests for predict_portfolio.py"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

# Ensure src/ is on path for core.models etc.
_LOTOFACIL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_LOTOFACIL / "src"))


def _load_portfolio():
    spec = importlib.util.spec_from_file_location(
        "predict_portfolio",
        _LOTOFACIL / "predict_portfolio.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Task 1: cost ───────────────────────────────────────────────────────────────

def test_cost_per_game_is_3_50_core():
    from core.config import COST_PER_GAME
    assert COST_PER_GAME == 3.50


def test_cost_per_game_is_3_50_ml():
    from lotofacil_ml.config import COST_PER_GAME
    assert COST_PER_GAME == 3.50


# ── Task 2: pure helpers ───────────────────────────────────────────────────────

def test_distribute_games_five():
    m = _load_portfolio()
    c, e, a = m.distribute_games(5)
    assert c + e + a == 5
    assert c >= e >= a >= 1


def test_distribute_games_eight():
    m = _load_portfolio()
    c, e, a = m.distribute_games(8)
    assert c + e + a == 8
    assert c >= e >= a >= 1


def test_distribute_games_one():
    m = _load_portfolio()
    c, e, a = m.distribute_games(1)
    assert c + e + a == 1


def test_game_quality_score_bounds():
    m = _load_portfolio()
    score = m.game_quality_score(
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    )
    assert 0.0 <= score <= 1.0


def test_game_quality_score_good_game():
    m = _load_portfolio()
    # concurso 3671: passes most filters
    game = [1, 3, 4, 5, 6, 7, 9, 10, 12, 13, 15, 16, 17, 18, 21]
    last = [2, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 17, 20, 22]
    score = m.game_quality_score(game, last)
    assert 0.0 <= score <= 1.0


# ── Task 3: data loader ────────────────────────────────────────────────────────

def test_load_draws_from_files_empty_dir():
    m = _load_portfolio()
    with tempfile.TemporaryDirectory() as tmpdir:
        result = m.load_draws_from_files(Path(tmpdir), max_concurso=9999)
    assert result == []


def test_load_draws_from_files_respects_max_concurso():
    m = _load_portfolio()
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
    m = _load_portfolio()
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


# ── Task 4: probabilities ──────────────────────────────────────────────────────

def test_get_probabilities_shape_and_sum():
    m = _load_portfolio()
    draws = m.load_draws_from_files(
        _LOTOFACIL / "dados" / "sample",
        max_concurso=9999,
    )
    assert len(draws) >= 10, "Need at least 10 sample draws"
    probas = m.get_probabilities(draws)
    assert probas.shape == (25,)
    assert abs(probas.sum() - 1.0) < 1e-4
    assert all(probas >= 0)


def test_get_probabilities_top11_unique():
    import numpy as np
    m = _load_portfolio()
    draws = m.load_draws_from_files(
        _LOTOFACIL / "dados" / "sample",
        max_concurso=9999,
    )
    probas = m.get_probabilities(draws)
    top11 = list(np.argsort(probas)[::-1][:11] + 1)
    assert len(set(top11)) == 11
    assert all(1 <= n <= 25 for n in top11)


# ── Task 5: game generation ────────────────────────────────────────────────────

def test_generate_games_for_tier_count():
    m = _load_portfolio()
    core = list(range(1, 12))
    fill_pool = list(range(12, 18))
    last_draw = list(range(1, 16))
    games = m.generate_games_for_tier(core, fill_pool, n_games=3, last_draw=last_draw)
    assert len(games) == 3


def test_generate_games_for_tier_each_game_has_15():
    m = _load_portfolio()
    core = list(range(1, 12))
    fill_pool = list(range(12, 20))
    last_draw = list(range(1, 16))
    games = m.generate_games_for_tier(core, fill_pool, n_games=2, last_draw=last_draw)
    for game in games:
        assert len(game) == 15, f"Game has {len(game)} numbers: {game}"
        assert len(set(game)) == 15, "Game has duplicates"
        assert all(1 <= n <= 25 for n in game)


def test_generate_games_for_tier_contains_core():
    m = _load_portfolio()
    core = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21]
    fill_pool = [2, 4, 6, 8, 10, 12, 14, 16]
    last_draw = list(range(1, 16))
    games = m.generate_games_for_tier(core, fill_pool, n_games=2, last_draw=last_draw)
    for game in games:
        assert all(n in game for n in core), f"Core not fully in game {game}"


def test_build_portfolio_structure():
    m = _load_portfolio()
    core = list(range(1, 12))
    ranked = list(range(1, 26))
    last_draw = list(range(1, 16))
    portfolio = m.build_portfolio(core, ranked, n_games=5, last_draw=last_draw)
    assert "conservador" in portfolio
    assert "equilibrado" in portfolio
    assert "agressivo" in portfolio
    total = sum(len(v) for v in portfolio.values())
    assert total == 5


# ── Task 6: display ────────────────────────────────────────────────────────────

def test_print_portfolio_runs_without_error(capsys):
    m = _load_portfolio()
    portfolio = {
        "conservador": [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]],
        "equilibrado": [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16]],
        "agressivo": [],
    }
    m.print_portfolio(portfolio, n_jogos=2, target_concurso=3675)
    captured = capsys.readouterr()
    assert "3675" in captured.out
    assert "R$" in captured.out
