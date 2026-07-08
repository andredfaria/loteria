from pathlib import Path

from quina.infra.dados.leitor import load_draws

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "sample_draws"


class TestLoadDrawsFixtures:
    def test_loads_all_25_fixtures(self):
        draws = load_draws(FIXTURES_DIR)
        assert len(draws) == 25

    def test_sorted_by_concurso(self):
        draws = load_draws(FIXTURES_DIR)
        concursos = [d.concurso for d in draws]
        assert concursos == sorted(concursos)
        assert concursos[0] == 7035
        assert concursos[-1] == 7059

    def test_dezenas_are_sorted_ints(self):
        draws = load_draws(FIXTURES_DIR)
        last = draws[-1]
        assert last.dezenas == [27, 47, 57, 70, 78]


class TestLoadDrawsEdgeCases:
    def test_empty_dir(self, tmp_path):
        assert load_draws(tmp_path) == []

    def test_skips_invalid_count(self, tmp_path):
        (tmp_path / "concurso_1.json").write_text(
            '{"concurso": 1, "data": "01/01/2026", "dezenas": ["1", "2", "3"]}'
        )
        assert load_draws(tmp_path) == []

    def test_skips_duplicates(self, tmp_path):
        (tmp_path / "concurso_1.json").write_text(
            '{"concurso": 1, "data": "01/01/2026", "dezenas": ["1", "1", "2", "3", "4"]}'
        )
        assert load_draws(tmp_path) == []

    def test_skips_out_of_range(self, tmp_path):
        (tmp_path / "concurso_1.json").write_text(
            '{"concurso": 1, "data": "01/01/2026", "dezenas": ["1", "2", "3", "4", "81"]}'
        )
        assert load_draws(tmp_path) == []

    def test_skips_malformed_json(self, tmp_path):
        (tmp_path / "concurso_1.json").write_text("not json")
        assert load_draws(tmp_path) == []

    def test_valid_and_invalid_mixed(self, tmp_path):
        (tmp_path / "concurso_1.json").write_text(
            '{"concurso": 1, "data": "01/01/2026", "dezenas": ["1", "2", "3", "4", "5"]}'
        )
        (tmp_path / "concurso_2.json").write_text(
            '{"concurso": 2, "data": "02/01/2026", "dezenas": ["1", "2", "3"]}'
        )
        draws = load_draws(tmp_path)
        assert len(draws) == 1
        assert draws[0].concurso == 1
