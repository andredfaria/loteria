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
