"""Smoke test do comando CLI `portfolio fechar`."""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from lotofacil.infra.config import DADOS_DIR
from lotofacil.infra.dados.leitor import load_draws
from lotofacil.interface.cli.portfolio import app

runner = CliRunner()


@pytest.mark.skipif(not load_draws(DADOS_DIR), reason="sem dados locais")
def test_fechar_roda_e_mostra_garantia():
    result = runner.invoke(app, ["fechar", "--pool-size", "16", "--jogos", "3"])
    assert result.exit_code == 0, result.output
    assert "garantia" in result.output.lower()


@pytest.mark.skipif(not load_draws(DADOS_DIR), reason="sem dados locais")
def test_fechar_respeita_excluir():
    result = runner.invoke(
        app, ["fechar", "--pool-size", "16", "--jogos", "2", "--excluir", "1,2,3"]
    )
    assert result.exit_code == 0, result.output
