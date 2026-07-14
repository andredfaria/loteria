from __future__ import annotations

import pytest
from typer.testing import CliRunner

from quina.interface.cli.app import app
from quina.infra.config import MODELOS_DIR

runner = CliRunner()


class TestPrever:
    def test_prever_help(self):
        result = runner.invoke(app, ["prever", "--help"])
        assert result.exit_code == 0
        assert "Predizer" in result.stdout

    def test_prever_executa(self):
        result = runner.invoke(app, ["prever", "prever"])
        assert result.exit_code == 0
        assert "dezenas" in result.stdout or "Predição" in result.stdout or "Confiança" in result.stdout