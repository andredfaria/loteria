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
        if result.exit_code != 0:
            # Sem base sincronizada nem modelo treinado (o caso da CI e de um
            # checkout limpo) o comando sai com erro por design. O que importa
            # aqui é que ele falhe com mensagem útil, não com stack trace.
            saida = result.stdout + str(result.exception or "")
            assert any(t in saida for t in ("dados", "modelo", "Nenhum", "insuficient")), (
                f"esperava erro explicativo, veio: {saida[:300]}"
            )
            pytest.skip("sem dados/modelo local para exercitar o caminho feliz")
        assert result.exit_code == 0
        assert "dezenas" in result.stdout or "Predição" in result.stdout or "Confiança" in result.stdout