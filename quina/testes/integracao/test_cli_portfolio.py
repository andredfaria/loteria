from functools import partial

from typer.testing import CliRunner

from quina.infra.dados.banco import DatabaseManager
from quina.interface.cli import portfolio as portfolio_cli

runner = CliRunner()


def _patch_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(portfolio_cli, "DatabaseManager", partial(DatabaseManager, db_path=db_path))
    return db_path


def _seed_draws(db):
    for i in range(1, 6):
        db.upsert_concurso(i, f"0{i}/01/2026", [i, i + 10, i + 20, i + 30, i + 40])


class TestGerarCommand:
    def test_dados_insuficientes(self, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        result = runner.invoke(portfolio_cli.app, ["gerar", "--orcamento", "30"])

        assert result.exit_code == 1

    def test_gerar_com_dados(self, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        result = runner.invoke(portfolio_cli.app, ["gerar", "--orcamento", "30", "--perfil", "conservador"])

        assert result.exit_code == 0
        assert "Custo total" in result.stdout

    def test_perfil_desconhecido_da_erro_limpo(self, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        result = runner.invoke(portfolio_cli.app, ["gerar", "--orcamento", "30", "--perfil", "bogus"])

        assert result.exit_code == 1
        assert "perfil desconhecido" in result.stdout
        assert isinstance(result.exception, SystemExit)
