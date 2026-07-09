from functools import partial

from typer.testing import CliRunner

from quina.infra.dados.banco import DatabaseManager
from quina.interface.cli import jogos as jogos_cli

runner = CliRunner()


def _patch_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(jogos_cli, "DatabaseManager", partial(DatabaseManager, db_path=db_path))
    return db_path


def _seed_draws(db):
    for i in range(1, 6):
        db.upsert_concurso(i, f"0{i}/01/2026", [i, i + 10, i + 20, i + 30, i + 40])


class TestGerarCommand:
    def test_dados_insuficientes(self, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        result = runner.invoke(jogos_cli.app, ["gerar"])

        assert result.exit_code == 1

    def test_gerar_com_filtros(self, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        result = runner.invoke(jogos_cli.app, ["gerar", "--estrategia", "filtros", "--tamanho", "5", "--n", "3"])

        assert result.exit_code == 0
        assert "Custo total" in result.stdout

    def test_gerar_persiste_no_banco(self, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        _seed_draws(db)

        runner.invoke(jogos_cli.app, ["gerar", "--estrategia", "filtros", "--tamanho", "5", "--n", "3"])

        assert len(db.listar_jogos_gerados()) == 3

    def test_tamanho_fora_do_intervalo_da_erro_limpo(self, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        result = runner.invoke(jogos_cli.app, ["gerar", "--estrategia", "filtros", "--tamanho", "20", "--n", "3"])

        assert result.exit_code == 1
        assert "Tamanho de aposta" in result.stdout
        assert isinstance(result.exception, SystemExit)


class TestFechamentoCommand:
    def test_fechamento_valido(self, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        result = runner.invoke(jogos_cli.app, ["fechamento", "--dezenas", "1,2,3,4,5", "--garantia", "5,5"])

        assert result.exit_code == 0
        assert "custo total" in result.stdout.lower()

    def test_fechamento_invalido(self, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        result = runner.invoke(jogos_cli.app, ["fechamento", "--dezenas", "1,2,3", "--garantia", "3,3"])

        assert result.exit_code != 0
