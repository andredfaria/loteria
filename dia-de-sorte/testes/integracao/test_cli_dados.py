import os
from pathlib import Path
from tempfile import TemporaryDirectory

import responses
from typer.testing import CliRunner

from diadesorte.infra.config import API_DIADESORTE
from diadesorte.interface.cli.app import app
from diadesorte.infra.dados.banco import DatabaseManager

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sample_draws"

runner = CliRunner()


def _make_concurso(n: int) -> dict:
    return {"concurso": n, "data": "23/01/2020", "dezenas": ["04", "10", "11", "19", "20", "25", "26"], "mesSorte": "Julho"}


@responses.activate
def test_dados_atualizar_com_novos():
    responses.get(API_DIADESORTE, json=[_make_concurso(100)])
    with TemporaryDirectory() as tmp:
        env = {**os.environ, "DIADESORTE_DB_PATH": str(Path(tmp) / "diadesorte.db")}
        result = runner.invoke(app, ["dados", "atualizar"], env=env)
        assert result.exit_code == 0
        assert "1 concurso(s) sincronizado" in result.stdout


@responses.activate
def test_dados_atualizar_ja_atualizado():
    responses.get(API_DIADESORTE, json=[_make_concurso(100)])
    with TemporaryDirectory() as tmp:
        env = {**os.environ, "DIADESORTE_DB_PATH": str(Path(tmp) / "diadesorte.db")}
        runner.invoke(app, ["dados", "atualizar"], env=env)
        responses.reset()
        responses.get(f"{API_DIADESORTE}/latest", json=_make_concurso(100))
        result = runner.invoke(app, ["dados", "atualizar"], env=env)
        assert result.exit_code == 0
        assert "atualizados" in result.stdout


@responses.activate
def test_dados_status_sem_dados():
    with TemporaryDirectory() as tmp:
        env = {**os.environ, "DIADESORTE_DB_PATH": str(Path(tmp) / "diadesorte.db")}
        result = runner.invoke(app, ["dados", "status"], env=env)
        assert result.exit_code == 0
        assert "Nenhum concurso encontrado" in result.stdout


@responses.activate
def test_dados_status_com_dados():
    with TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "diadesorte.db"
        db = DatabaseManager(db_path)
        db.upsert_concurso(100, "23/01/2020", [4, 10, 11, 19, 20, 25, 26], "Julho")
        env = {**os.environ, "DIADESORTE_DB_PATH": str(db_path)}
        result = runner.invoke(app, ["dados", "status"], env=env)
        assert result.exit_code == 0
        assert "Total de concursos:" in result.stdout
        assert "100" in result.stdout
