import json
from pathlib import Path
from tempfile import TemporaryDirectory

import responses

from supersete.infra.config import API_SUPERSETE
from supersete.infra.dados.api_caixa import SuperseteFetcher
from supersete.infra.dados.banco import DatabaseManager

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sample_draws"


def _load_fixture(concurso: int) -> dict:
    path = FIXTURES / f"concurso_{concurso}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@responses.activate
def test_fetch_latest_api():
    raw = _load_fixture(102)
    responses.get(f"{API_SUPERSETE}/latest", json=raw)

    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        fetcher = SuperseteFetcher(db=db, data_dir=Path(tmp))
        rec = fetcher.fetch_latest()
        assert rec is not None
        assert rec["concurso"] == 102
        assert rec["digitos"] == [5, 5, 5, 5, 5, 5, 5]
        assert db.count_concursos() == 1


@responses.activate
def test_fetch_by_concurso():
    raw = _load_fixture(100)
    responses.get(f"{API_SUPERSETE}/100", json=raw)

    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        fetcher = SuperseteFetcher(db=db, data_dir=Path(tmp))
        rec = fetcher.fetch_by_concurso(100)
        assert rec is not None
        assert rec["concurso"] == 100
        assert rec["digitos"] == [0, 6, 2, 0, 7, 8, 4]


@responses.activate
def test_fetch_by_concurso_not_found():
    responses.get(f"{API_SUPERSETE}/99999", status=404)

    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        fetcher = SuperseteFetcher(db=db, data_dir=Path(tmp))
        rec = fetcher.fetch_by_concurso(99999)
        assert rec is None


@responses.activate
def test_fetch_all_results_from_local_files():
    with TemporaryDirectory() as tmp:
        for f in FIXTURES.iterdir():
            (Path(tmp) / f.name).write_text(f.read_text(), encoding="utf-8")

        db = DatabaseManager(Path(tmp) / "test.db")
        fetcher = SuperseteFetcher(db=db, data_dir=Path(tmp))
        records = fetcher.fetch_all_results()
        assert len(records) == 3
        assert db.count_concursos() == 3


@responses.activate
def test_sync_new_draws_bulk_when_db_empty():
    raw_100 = _load_fixture(100)
    raw_101 = _load_fixture(101)
    raw_102 = _load_fixture(102)
    responses.get(API_SUPERSETE, json=[raw_100, raw_101, raw_102])

    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        fetcher = SuperseteFetcher(db=db, data_dir=Path(tmp))
        novos = fetcher.sync_new_draws()
        assert novos == 3
        assert db.count_concursos() == 3
        assert db.get_latest_concurso()["concurso"] == 102


@responses.activate
def test_sync_new_draws_incremental():
    raw_102 = _load_fixture(102)
    raw_103 = _load_fixture(101)
    raw_103["concurso"] = 103
    raw_103["dezenas"] = ["1", "1", "1", "1", "1", "1", "1"]

    responses.get(f"{API_SUPERSETE}/latest", json=raw_103)
    responses.get(f"{API_SUPERSETE}/103", json=raw_103)

    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        db.upsert_concurso(102, "17/10/2021", [5, 5, 5, 5, 5, 5, 5])
        fetcher = SuperseteFetcher(db=db, data_dir=Path(tmp))
        novos = fetcher.sync_new_draws()
        assert novos == 1
        assert db.count_concursos() == 2
        assert db.get_latest_concurso()["concurso"] == 103


@responses.activate
def test_sync_new_draws_ja_atualizado():
    responses.get(f"{API_SUPERSETE}/latest", json=_load_fixture(102))

    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        db.upsert_concurso(102, "17/10/2021", [5, 5, 5, 5, 5, 5, 5])
        fetcher = SuperseteFetcher(db=db, data_dir=Path(tmp))
        novos = fetcher.sync_new_draws()
        assert novos == 0
