"""Smoke tests for the `lab backtest` CLI command."""
from unittest.mock import patch

from typer.testing import CliRunner

from lotofacil.experimentos.main import app
from lotofacil.servicos.rodar_backtest_lab import ResultadoBacktestLab

runner = CliRunner()


def test_backtest_command_writes_result_path(tmp_path):
    fake_resultado = ResultadoBacktestLab(
        report={"results": [
            {"name": "neural_base+temp+priors", "mean_hits": 9.5, "n_evaluated": 10},
        ]},
        warnings=[],
    )
    with patch(
        "lotofacil.servicos.rodar_backtest_lab.rodar_backtest_lab",
        return_value=fake_resultado,
    ), patch("lotofacil.experimentos.config.PROJECT_ROOT", tmp_path):
        result = runner.invoke(
            app,
            ["backtest", "--configs", "base+temp+priors", "--start", "100", "--end", "110"],
        )

    assert result.exit_code == 0, result.stdout
    assert "BACKTEST_RESULT_PATH:" in result.stdout
    written = list((tmp_path / "saida" / "backtests").glob("backtest_*.json"))
    assert len(written) == 1


def test_backtest_command_reports_value_error(tmp_path):
    with patch(
        "lotofacil.servicos.rodar_backtest_lab.rodar_backtest_lab",
        side_effect=ValueError("intervalo inválido"),
    ):
        result = runner.invoke(
            app,
            ["backtest", "--configs", "base+temp+priors", "--start", "200", "--end", "100"],
        )

    assert result.exit_code == 1
    assert "intervalo inválido" in result.stdout
