import json
from pathlib import Path
from lotofacil_ml.data.loader import Draw, load_draws


def _make_json(tmp_path: Path, concurso: int, dezenas: list[int]) -> None:
    data = {
        "concurso": concurso,
        "data": "01/01/2020",
        "dezenas": [f"{d:02d}" for d in dezenas],
    }
    (tmp_path / f"concurso_{concurso}.json").write_text(json.dumps(data))


def test_load_draws_returns_sorted_draws(tmp_path):
    _make_json(tmp_path, 3, list(range(1, 16)))
    _make_json(tmp_path, 1, list(range(1, 16)))
    _make_json(tmp_path, 2, list(range(1, 16)))

    draws = load_draws(tmp_path)
    assert len(draws) == 3
    assert [d.concurso for d in draws] == [1, 2, 3]


def test_load_draws_dezenas_are_sorted_ints(tmp_path):
    _make_json(tmp_path, 1, [15, 3, 22, 7, 11, 1, 25, 8, 14, 19, 6, 13, 20, 4, 17])
    draws = load_draws(tmp_path)
    assert draws[0].dezenas == sorted([15, 3, 22, 7, 11, 1, 25, 8, 14, 19, 6, 13, 20, 4, 17])
    assert all(isinstance(n, int) for n in draws[0].dezenas)


def test_load_draws_skips_corrupt_json(tmp_path):
    _make_json(tmp_path, 1, list(range(1, 16)))
    (tmp_path / "concurso_99.json").write_text("NOT JSON {{{")
    draws = load_draws(tmp_path)
    assert len(draws) == 1


def test_load_draws_validates_15_numbers(tmp_path):
    # concurso with only 3 dezenas — must be skipped
    data = {"concurso": 2, "data": "01/01/2020", "dezenas": ["01", "02", "03"]}
    (tmp_path / "concurso_2.json").write_text(json.dumps(data))
    _make_json(tmp_path, 1, list(range(1, 16)))
    draws = load_draws(tmp_path)
    assert len(draws) == 1
    assert draws[0].concurso == 1


def test_draw_dataclass_fields():
    d = Draw(concurso=100, data="01/01/2020", dezenas=list(range(1, 16)))
    assert d.concurso == 100
    assert len(d.dezenas) == 15


def test_load_draws_skips_out_of_range_dezenas(tmp_path):
    # dezena 26 is out of range (1-25)
    data = {
        "concurso": 3,
        "data": "01/01/2020",
        "dezenas": ["01", "02", "03", "04", "05", "06", "07", "08",
                    "09", "10", "11", "12", "13", "14", "26"]
    }
    (tmp_path / "concurso_3.json").write_text(json.dumps(data))
    _make_json(tmp_path, 1, list(range(1, 16)))
    draws = load_draws(tmp_path)
    assert len(draws) == 1
    assert draws[0].concurso == 1


def test_load_draws_skips_duplicate_dezenas(tmp_path):
    # 15 values but with a duplicate — should be skipped
    data = {
        "concurso": 4,
        "data": "01/01/2020",
        "dezenas": ["01", "01", "02", "03", "04", "05", "06", "07",
                    "08", "09", "10", "11", "12", "13", "14"]
    }
    (tmp_path / "concurso_4.json").write_text(json.dumps(data))
    _make_json(tmp_path, 1, list(range(1, 16)))
    draws = load_draws(tmp_path)
    assert len(draws) == 1
    assert draws[0].concurso == 1
