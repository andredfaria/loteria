"""Testes da flag --sem-validar de `lotofacil dados atualizar`."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from lotofacil.interface.cli import dados as cli_dados
from lotofacil.interface.cli.app import app

runner = CliRunner()


@pytest.fixture
def cli_isolada(monkeypatch, tmp_path):
    """Isola a CLI: dados em tmp_path, sem rede, lua/clima desligados."""
    dados_dir = tmp_path / "dados"
    dados_dir.mkdir()
    monkeypatch.setattr(cli_dados, "_DADOS_DIR", dados_dir)
    monkeypatch.setattr(
        cli_dados,
        "_fetch_draw",
        lambda endpoint: (
            102,
            "2024-06-28",
            {"concurso": 102, "data": "28/06/2024", "dezenas": list(range(1, 16))},
        ),
    )
    monkeypatch.setattr(cli_dados, "_sync_lua", lambda missing, console: None)
    monkeypatch.setattr(cli_dados, "_sync_clima", lambda missing, console: None)

    chamadas: list[int] = []
    monkeypatch.setattr(
        cli_dados, "_validar_predicoes_pendentes", lambda console: chamadas.append(1)
    )
    return chamadas


def test_atualizar_valida_por_padrao(cli_isolada):
    result = runner.invoke(app, ["dados", "atualizar", "--escopo", "ultimo"])

    assert result.exit_code == 0, result.output
    assert cli_isolada == [1]


def test_atualizar_sem_validar_pula_validacao(cli_isolada):
    result = runner.invoke(
        app, ["dados", "atualizar", "--escopo", "ultimo", "--sem-validar"]
    )

    assert result.exit_code == 0, result.output
    assert cli_isolada == []
    assert "Validação de predições pulada" in result.output


def test_atualizar_help_mostra_flag():
    result = runner.invoke(app, ["dados", "atualizar", "--help"])

    assert result.exit_code == 0
    assert "--sem-validar" in result.output
