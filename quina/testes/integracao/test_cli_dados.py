from functools import partial

import responses
from typer.testing import CliRunner

from quina.infra.config import API_QUINA
from quina.infra.dados.banco import DatabaseManager
from quina.interface.cli import dados as dados_cli

runner = CliRunner()

RAW_7059 = {"concurso": 7059, "data": "07/07/2026", "dezenas": ["27", "47", "57", "70", "78"]}


def _patch_backends(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(dados_cli, "DatabaseManager", partial(DatabaseManager, db_path=db_path))
    monkeypatch.setattr(
        dados_cli,
        "QuinaFetcher",
        partial(dados_cli.QuinaFetcher, db=DatabaseManager(db_path=db_path), data_dir=tmp_path),
    )
    return db_path


class TestStatusCommand:
    def test_status_empty_db(self, monkeypatch, tmp_path):
        _patch_backends(monkeypatch, tmp_path)
        result = runner.invoke(dados_cli.app, ["status"])
        assert result.exit_code == 0
        assert "Nenhum concurso" in result.stdout

    def test_status_with_data(self, monkeypatch, tmp_path):
        db_path = _patch_backends(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])

        result = runner.invoke(dados_cli.app, ["status"])

        assert result.exit_code == 0
        assert "7059" in result.stdout


class TestAtualizarCommand:
    @responses.activate
    def test_atualizar_fetches_new(self, monkeypatch, tmp_path):
        db_path = _patch_backends(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.upsert_concurso(7058, "06/07/2026", [8, 26, 27, 66, 79])
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)
        responses.add(responses.GET, f"{API_QUINA}/7059", json=RAW_7059, status=200)

        result = runner.invoke(dados_cli.app, ["atualizar"])

        assert result.exit_code == 0
        assert "sincronizado" in result.stdout

    @responses.activate
    def test_atualizar_already_up_to_date(self, monkeypatch, tmp_path):
        db_path = _patch_backends(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)

        result = runner.invoke(dados_cli.app, ["atualizar"])

        assert result.exit_code == 0
        assert "já atualizados" in result.stdout
