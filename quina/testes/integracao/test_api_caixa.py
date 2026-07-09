import json

import responses

from quina.infra.config import API_QUINA
from quina.infra.dados.api_caixa import QuinaFetcher, _parse_record
from quina.infra.dados.banco import DatabaseManager

RAW_7059 = {"concurso": 7059, "data": "07/07/2026", "dezenas": ["27", "47", "57", "70", "78"]}
RAW_7058 = {"concurso": 7058, "data": "06/07/2026", "dezenas": ["08", "26", "27", "66", "79"]}


class TestParseRecord:
    def test_valid(self):
        rec = _parse_record(RAW_7059)
        assert rec["concurso"] == 7059
        assert rec["dezenas"] == [27, 47, 57, 70, 78]

    def test_invalid_count(self):
        bad = {"concurso": 1, "data": "01/01/2026", "dezenas": ["1", "2", "3"]}
        assert _parse_record(bad) is None

    def test_invalid_range(self):
        bad = {"concurso": 1, "data": "01/01/2026", "dezenas": ["1", "2", "3", "4", "81"]}
        assert _parse_record(bad) is None

    def test_missing_field(self):
        assert _parse_record({"concurso": 1}) is None


class TestQuinaFetcher:
    @responses.activate
    def test_fetch_latest(self, tmp_path):
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)
        db = DatabaseManager(db_path=tmp_path / "test.db")
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        result = fetcher.fetch_latest()

        assert result["concurso"] == 7059
        assert result["dezenas"] == [27, 47, 57, 70, 78]
        assert db.count_concursos() == 1
        assert (tmp_path / "concurso_7059.json").exists()

    @responses.activate
    def test_fetch_by_concurso_from_api(self, tmp_path):
        responses.add(responses.GET, f"{API_QUINA}/7059", json=RAW_7059, status=200)
        db = DatabaseManager(db_path=tmp_path / "test.db")
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        result = fetcher.fetch_by_concurso(7059)

        assert result["concurso"] == 7059
        assert db.count_concursos() == 1

    @responses.activate
    def test_fetch_by_concurso_from_db_skips_api(self, tmp_path):
        db = DatabaseManager(db_path=tmp_path / "test.db")
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        result = fetcher.fetch_by_concurso(7059)

        assert result["concurso"] == 7059
        assert len(responses.calls) == 0

    @responses.activate
    def test_sync_new_draws_bootstraps_empty_db_from_local_files(self, tmp_path):
        (tmp_path / "concurso_7058.json").write_text(json.dumps(RAW_7058))
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7058, status=200)
        db = DatabaseManager(db_path=tmp_path / "test.db")
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        new_count = fetcher.sync_new_draws()

        assert db.count_concursos() == 1
        assert new_count == 0

    @responses.activate
    def test_sync_new_draws_fetches_gap(self, tmp_path):
        db = DatabaseManager(db_path=tmp_path / "test.db")
        db.upsert_concurso(7058, "06/07/2026", [8, 26, 27, 66, 79])
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)
        responses.add(responses.GET, f"{API_QUINA}/7059", json=RAW_7059, status=200)
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        new_count = fetcher.sync_new_draws()

        assert new_count == 1
        assert db.count_concursos() == 2
        assert db.get_latest_concurso()["concurso"] == 7059

    @responses.activate
    def test_sync_new_draws_no_op_when_up_to_date(self, tmp_path):
        db = DatabaseManager(db_path=tmp_path / "test.db")
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        new_count = fetcher.sync_new_draws()

        assert new_count == 0
        assert db.count_concursos() == 1


class TestSyncValidaJogosGerados:
    @responses.activate
    def test_sync_atualiza_acertos_de_jogos_pendentes(self, tmp_path):
        db = DatabaseManager(db_path=tmp_path / "test.db")
        db.upsert_concurso(7058, "06/07/2026", [8, 26, 27, 66, 79])
        db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[27, 47, 57, 70, 78],
            score=0.8, custo=3.0, concurso_alvo_validacao=7059,
        )
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)
        responses.add(responses.GET, f"{API_QUINA}/7059", json=RAW_7059, status=200)
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        fetcher.sync_new_draws()

        jogos = db.listar_jogos_gerados()
        assert jogos[0]["acertos"] == 5  # dezenas do jogo batem 100% com o sorteio 7059

    @responses.activate
    def test_sync_nao_toca_jogos_de_outro_concurso_alvo(self, tmp_path):
        db = DatabaseManager(db_path=tmp_path / "test.db")
        db.upsert_concurso(7058, "06/07/2026", [8, 26, 27, 66, 79])
        db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[1, 2, 3, 4, 5],
            score=0.5, custo=3.0, concurso_alvo_validacao=9999,
        )
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)
        responses.add(responses.GET, f"{API_QUINA}/7059", json=RAW_7059, status=200)
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        fetcher.sync_new_draws()

        jogos = db.listar_jogos_gerados()
        assert jogos[0]["acertos"] is None
