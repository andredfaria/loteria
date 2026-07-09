from functools import partial

from typer.testing import CliRunner

from quina.infra.dados.banco import DatabaseManager
from quina.interface.cli import modelo as modelo_cli

runner = CliRunner()


def _patch_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(modelo_cli, "DatabaseManager", partial(DatabaseManager, db_path=db_path))
    return db_path


def _seed_draws(db):
    for i in range(1, 6):
        db.upsert_concurso(i, f"0{i}/01/2026", [i, i + 10, i + 20, i + 30, i + 40])


class TestTreinarCommand:
    def test_dados_insuficientes(self, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        result = runner.invoke(modelo_cli.app, ["treinar"])

        assert result.exit_code == 1
        assert "insuficientes" in result.stdout

    def test_treinar_com_dados(self, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        result = runner.invoke(modelo_cli.app, ["treinar", "--estrategia", "frequencia_atraso", "--janela", "3"])

        assert result.exit_code == 0
        assert "Backtest" in result.stdout

    def test_estrategia_desconhecida_da_erro_limpo(self, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        result = runner.invoke(modelo_cli.app, ["treinar", "--estrategia", "bogus"])

        assert result.exit_code == 1
        assert "desconhecida" in result.stdout
        assert isinstance(result.exception, SystemExit)


class TestLeaderboardCommand:
    def test_sem_backtests(self, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        result = runner.invoke(modelo_cli.app, ["leaderboard"])

        assert result.exit_code == 0
        assert "Nenhum backtest" in result.stdout

    def test_com_backtests(self, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.salvar_backtest("filtros", 100, {
            "taxa_estrategia": {"2": 0.1, "3": 0.0, "4": 0.0, "5": 0.0},
            "taxa_baseline": {"2": 0.1, "3": 0.0, "4": 0.0, "5": 0.0},
        })

        result = runner.invoke(modelo_cli.app, ["leaderboard"])

        assert result.exit_code == 0
        assert "filtros" in result.stdout
