"""Smoke tests for the unified CLI."""

from typer.testing import CliRunner
from lotofacil.interface.cli.app import app


def test_cli_app_importable():
    assert app is not None


def test_dados_help():
    runner = CliRunner()
    result = runner.invoke(app, ["dados", "--help"])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    assert "atualizar" in result.output
    assert "status" in result.output


def test_modelo_help():
    runner = CliRunner()
    result = runner.invoke(app, ["modelo", "--help"])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    assert "treinar" in result.output
    assert "backtest" in result.output
    assert "historico" in result.output
    assert "validar" in result.output


def test_portfolio_help():
    runner = CliRunner()
    result = runner.invoke(app, ["portfolio", "--help"])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    assert "validar" in result.output


def test_lab_help():
    runner = CliRunner()
    result = runner.invoke(app, ["lab", "--help"])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    assert "backfill-clima" in result.output
    assert "lunar-check" in result.output
    assert "train-ordem" in result.output
    assert "prever-ordem" in result.output


def test_lab_train_ordem_help():
    runner = CliRunner()
    result = runner.invoke(app, ["lab", "train-ordem", "--help"])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    assert "--name" in result.output


def test_lab_prever_ordem_help():
    runner = CliRunner()
    result = runner.invoke(app, ["lab", "prever-ordem", "--help"])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    assert "--name" in result.output
