import json
from pathlib import Path
from tempfile import TemporaryDirectory

import responses

from megasena.infra.config import API_MEGASENA
from megasena.infra.dados.api_caixa import MegasenaFetcher
from megasena.infra.dados.banco import DatabaseManager

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sample_draws"


def _load_fixture(concurso: int) -> dict:
    path = FIXTURES / f"megasena_{concurso}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@responses.activate
def test_fetch_latest_api():
    raw = _load_fixture(102)
    responses.get(f"{API_MEGASENA}/latest", json=raw)

    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        fetcher = MegasenaFetcher(db=db, data_dir=Path(tmp))
        rec = fetcher.fetch_latest()
        assert rec is not None
        assert rec["concurso"] == 102
        assert rec["dezenas"] == [19, 20, 37, 42, 44, 56]
        assert db.count_concursos() == 1


@responses.activate
def test_fetch_by_concurso():
    raw = _load_fixture(100)
    responses.get(f"{API_MEGASENA}/100", json=raw)

    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        fetcher = MegasenaFetcher(db=db, data_dir=Path(tmp))
        rec = fetcher.fetch_by_concurso(100)
        assert rec is not None
        assert rec["concurso"] == 100
        assert rec["dezenas"] == [14, 29, 30, 46, 48, 51]


@responses.activate
def test_fetch_by_concurso_not_found():
    responses.get(f"{API_MEGASENA}/99999", status=404)

    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        fetcher = MegasenaFetcher(db=db, data_dir=Path(tmp))
        rec = fetcher.fetch_by_concurso(99999)
        assert rec is None


@responses.activate
def test_fetch_all_results_from_local_files():
    with TemporaryDirectory() as tmp:
        for f in FIXTURES.iterdir():
            (Path(tmp) / f.name).write_text(f.read_text(), encoding="utf-8")

        db = DatabaseManager(Path(tmp) / "test.db")
        fetcher = MegasenaFetcher(db=db, data_dir=Path(tmp))
        records = fetcher.fetch_all_results()
        assert len(records) == 3
        assert db.count_concursos() == 3


@responses.activate
def test_sync_new_draws_bulk_when_db_empty():
    raw_100 = _load_fixture(100)
    raw_101 = _load_fixture(101)
    raw_102 = _load_fixture(102)
    responses.get(API_MEGASENA, json=[raw_100, raw_101, raw_102])

    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        fetcher = MegasenaFetcher(db=db, data_dir=Path(tmp))
        novos = fetcher.sync_new_draws()
        assert novos == 3
        assert db.count_concursos() == 3
        assert db.get_latest_concurso()["concurso"] == 102


@responses.activate
def test_sync_new_draws_incremental():
    raw_103 = _load_fixture(101)
    raw_103["concurso"] = 103
    raw_103["dezenas"] = ["01", "02", "03", "04", "05", "06"]

    responses.get(f"{API_MEGASENA}/latest", json=raw_103)
    responses.get(f"{API_MEGASENA}/103", json=raw_103)

    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        db.upsert_concurso(102, "15/02/1998", [19, 20, 37, 42, 44, 56])
        fetcher = MegasenaFetcher(db=db, data_dir=Path(tmp))
        novos = fetcher.sync_new_draws()
        assert novos == 1
        assert db.count_concursos() == 2
        assert db.get_latest_concurso()["concurso"] == 103


@responses.activate
def test_sync_new_draws_ja_atualizado():
    responses.get(f"{API_MEGASENA}/latest", json=_load_fixture(102))

    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        db.upsert_concurso(102, "15/02/1998", [19, 20, 37, 42, 44, 56])
        fetcher = MegasenaFetcher(db=db, data_dir=Path(tmp))
        novos = fetcher.sync_new_draws()
        assert novos == 0