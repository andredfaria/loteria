import os
from pathlib import Path
from tempfile import TemporaryDirectory

import responses
from typer.testing import CliRunner

from supersete.infra.config import API_SUPERSETE
from supersete.interface.cli.app import app
from supersete.infra.dados.banco import DatabaseManager

runner = CliRunner()


def _make_concurso(n: int) -> dict:
    return {"concurso": n, "data": "10/10/2021", "dezenas": ["0", "6", "2", "0", "7", "8", "4"]}


@responses.activate
def test_dados_atualizar_com_novos():
    responses.get(API_SUPERSETE, json=[_make_concurso(100)])
    with TemporaryDirectory() as tmp:
        env = {**os.environ, "SUPERSETE_DB_PATH": str(Path(tmp) / "supersete.db")}
        result = runner.invoke(app, ["dados", "atualizar"], env=env)
        assert result.exit_code == 0
        assert "1 concurso(s) sincronizado" in result.stdout


@responses.activate
def test_dados_atualizar_ja_atualizado():
    responses.get(API_SUPERSETE, json=[_make_concurso(100)])
    with TemporaryDirectory() as tmp:
        env = {**os.environ, "SUPERSETE_DB_PATH": str(Path(tmp) / "supersete.db")}
        runner.invoke(app, ["dados", "atualizar"], env=env)
        responses.reset()
        responses.get(f"{API_SUPERSETE}/latest", json=_make_concurso(100))
        result = runner.invoke(app, ["dados", "atualizar"], env=env)
        assert result.exit_code == 0
        assert "atualizados" in result.stdout


@responses.activate
def test_dados_status_sem_dados():
    with TemporaryDirectory() as tmp:
        env = {**os.environ, "SUPERSETE_DB_PATH": str(Path(tmp) / "supersete.db")}
        result = runner.invoke(app, ["dados", "status"], env=env)
        assert result.exit_code == 0
        assert "Nenhum concurso encontrado" in result.stdout


@responses.activate
def test_dados_status_com_dados():
    with TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "supersete.db"
        db = DatabaseManager(db_path)
        db.upsert_concurso(100, "10/10/2021", [0, 6, 2, 0, 7, 8, 4])
        env = {**os.environ, "SUPERSETE_DB_PATH": str(db_path)}
        result = runner.invoke(app, ["dados", "status"], env=env)
        assert result.exit_code == 0
        assert "Total de concursos:" in result.stdout
        assert "100" in result.stdout
