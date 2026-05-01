"""Tests for the LotofacilFetcher."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import responses as resp_lib

from lotofacil_ml.data.database import DatabaseManager
from lotofacil_ml.data.fetcher import LotofacilFetcher, _parse_record


# ── Fixtures ───────────────────────────────────────────────────────────────────

VALID_RAW = {
    "concurso": 3500,
    "data": "01/01/2024",
    "dezenas": [f"{i:02d}" for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]],
}


@pytest.fixture
def tmp_db(tmp_path):
    return DatabaseManager(db_path=tmp_path / "test.db")


@pytest.fixture
def tmp_dados(tmp_path):
    dados = tmp_path / "dados"
    dados.mkdir()
    for i in range(1, 4):
        record = {
            "concurso": i,
            "data": f"0{i}/01/2003",
            "dezenas": [f"{j:02d}" for j in range(i, i + 15)],
        }
        (dados / f"concurso_{i}.json").write_text(json.dumps(record))
    return dados


# ── parse_record ───────────────────────────────────────────────────────────────

def test_parse_record_valid():
    rec = _parse_record(VALID_RAW)
    assert rec is not None
    assert rec["concurso"] == 3500
    assert len(rec["dezenas"]) == 15
    assert all(1 <= d <= 25 for d in rec["dezenas"])


def test_parse_record_wrong_count():
    bad = {**VALID_RAW, "dezenas": ["01", "02"]}
    assert _parse_record(bad) is None


def test_parse_record_out_of_range():
    bad = {**VALID_RAW, "dezenas": [f"{i:02d}" for i in range(1, 15)] + ["26"]}
    assert _parse_record(bad) is None


def test_parse_record_missing_field():
    bad = {"concurso": 1}
    assert _parse_record(bad) is None


# ── fetch_all_results (local files) ───────────────────────────────────────────

def test_fetch_all_results_local(tmp_db, tmp_dados):
    fetcher = LotofacilFetcher(db=tmp_db, data_dir=tmp_dados)
    results = fetcher.fetch_all_results()
    assert len(results) == 3
    assert results[0]["concurso"] == 1


def test_fetch_all_results_invalid_skipped(tmp_db, tmp_path):
    dados = tmp_path / "dados"
    dados.mkdir()
    # One valid, one invalid
    (dados / "concurso_1.json").write_text(json.dumps(VALID_RAW))
    (dados / "concurso_bad.json").write_text("not json{")
    fetcher = LotofacilFetcher(db=tmp_db, data_dir=dados)
    results = fetcher.fetch_all_results()
    assert len(results) == 1


# ── fetch_latest (API) ────────────────────────────────────────────────────────

@resp_lib.activate
def test_fetch_latest_api_success(tmp_db, tmp_dados):
    from lotofacil_ml.config import API_LOTOFACIL
    resp_lib.add(
        resp_lib.GET,
        f"{API_LOTOFACIL}/latest",
        json=VALID_RAW,
        status=200,
    )
    fetcher = LotofacilFetcher(db=tmp_db, data_dir=tmp_dados)
    result = fetcher.fetch_latest()
    assert result is not None
    assert result["concurso"] == 3500


@resp_lib.activate
def test_fetch_latest_api_failure_falls_back(tmp_db, tmp_dados):
    from lotofacil_ml.config import API_LOTOFACIL
    # Seed the DB first
    tmp_db.upsert_concurso(1, "01/01/2003", list(range(1, 16)))
    # All API attempts fail
    for _ in range(6):
        resp_lib.add(
            resp_lib.GET,
            f"{API_LOTOFACIL}/latest",
            status=500,
        )
    fetcher = LotofacilFetcher(db=tmp_db, data_dir=tmp_dados)
    result = fetcher.fetch_latest()
    # Should fall back to DB value
    assert result is not None
    assert result["concurso"] == 1


# ── fetch_by_concurso ─────────────────────────────────────────────────────────

def test_fetch_by_concurso_from_db(tmp_db, tmp_dados):
    tmp_db.upsert_concurso(3500, "01/01/2024", list(range(1, 16)))
    fetcher = LotofacilFetcher(db=tmp_db, data_dir=tmp_dados)
    result = fetcher.fetch_by_concurso(3500)
    assert result is not None
    assert result["concurso"] == 3500


# ── Payload validation ────────────────────────────────────────────────────────

def test_payload_validation_persists_only_valid(tmp_db, tmp_path):
    dados = tmp_path / "dados"
    dados.mkdir()
    valid = {**VALID_RAW, "concurso": 10}
    invalid = {**VALID_RAW, "concurso": 11, "dezenas": ["01"] * 15}  # duplicates but right length
    # Actually make dezenas invalid count
    invalid["dezenas"] = ["01", "02"]  # only 2
    (dados / "concurso_10.json").write_text(json.dumps(valid))
    (dados / "concurso_11.json").write_text(json.dumps(invalid))
    fetcher = LotofacilFetcher(db=tmp_db, data_dir=dados)
    results = fetcher.fetch_all_results()
    assert len(results) == 1
    assert results[0]["concurso"] == 10
