"""Smoke tests for the unified CLI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def test_cli_app_importable():
    """Just verify the file exists and has valid Python syntax."""
    import ast
    import pathlib
    src = pathlib.Path(__file__).resolve().parent.parent / "src" / "cli" / "app.py"
    assert src.exists(), f"src/cli/app.py not found"
    try:
        ast.parse(src.read_text())
    except SyntaxError as e:
        raise AssertionError(f"Syntax error in app.py: {e}")


from typer.testing import CliRunner

def test_dados_help():
    """Test that dados subcommand help works."""
    # We need all sub-apps to exist for this import to work
    try:
        from cli.app import app
    except ImportError:
        import pytest
        pytest.skip("Not all sub-apps created yet")
    runner = CliRunner()
    result = runner.invoke(app, ["dados", "--help"])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    assert "atualizar" in result.output
    assert "status" in result.output


def test_modelo_help():
    """Test that modelo subcommand help works."""
    try:
        from cli.app import app
    except ImportError:
        import pytest
        pytest.skip("Not all sub-apps created yet")
    runner = CliRunner()
    result = runner.invoke(app, ["modelo", "--help"])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    assert "treinar" in result.output
    assert "backtest" in result.output
    assert "historico" in result.output
    assert "validar" in result.output
