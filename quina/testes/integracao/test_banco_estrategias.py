import sqlite3

import pytest

from quina.infra.dados.banco import DatabaseManager


@pytest.fixture
def db(tmp_path):
    return DatabaseManager(db_path=tmp_path / "test_estrategias.db")


class TestTabelasNovas:
    def test_estrategias_backtest_table_exists(self, db):
        conn = sqlite3.connect(db.db_path)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='estrategias_backtest'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_jogos_gerados_table_exists(self, db):
        conn = sqlite3.connect(db.db_path)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='jogos_gerados'"
        ).fetchone()
        conn.close()
        assert row is not None


class TestSalvarBacktest:
    def test_salvar_e_listar(self, db):
        metricas = {"taxa_estrategia": {"2": 0.1, "3": 0.0, "4": 0.0, "5": 0.0}}
        backtest_id = db.salvar_backtest("filtros", 300, metricas)
        assert backtest_id is not None

        registros = db.listar_backtests()
        assert len(registros) == 1
        assert registros[0]["estrategia"] == "filtros"
        assert registros[0]["janela"] == 300
        assert registros[0]["metricas"] == metricas

    def test_listar_ordenado_do_mais_recente(self, db):
        db.salvar_backtest("filtros", 100, {"a": 1})
        db.salvar_backtest("frequencia_atraso", 200, {"b": 2})

        registros = db.listar_backtests()

        assert registros[0]["estrategia"] == "frequencia_atraso"
        assert registros[1]["estrategia"] == "filtros"

    def test_limite(self, db):
        for i in range(5):
            db.salvar_backtest("filtros", i, {"i": i})

        registros = db.listar_backtests(limite=2)

        assert len(registros) == 2


class TestJogosGerados:
    def test_salvar_e_listar(self, db):
        jogo_id = db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[1, 2, 3, 4, 5],
            score=0.75, custo=3.0,
        )
        assert jogo_id is not None

        jogos = db.listar_jogos_gerados()
        assert len(jogos) == 1
        assert jogos[0]["dezenas"] == [1, 2, 3, 4, 5]
        assert jogos[0]["score"] == 0.75
        assert jogos[0]["custo"] == 3.0
        assert jogos[0]["acertos"] is None
        assert jogos[0]["concurso_alvo_validacao"] is None

    def test_salvar_com_concurso_alvo(self, db):
        db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[1, 2, 3, 4, 5],
            score=0.75, custo=3.0, concurso_alvo_validacao=7060,
        )
        jogos = db.listar_jogos_gerados()
        assert jogos[0]["concurso_alvo_validacao"] == 7060

    def test_listar_com_paginacao(self, db):
        for i in range(5):
            db.salvar_jogo_gerado(
                estrategia="filtros", tamanho_aposta=5, dezenas=[1, 2, 3, 4, 5 + i],
                score=0.5, custo=3.0,
            )
        pagina = db.listar_jogos_gerados(limite=2, offset=2)
        assert len(pagina) == 2


class TestAtualizarAcertosPendentes:
    def test_atualiza_jogo_pendente(self, db):
        db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[27, 47, 57, 70, 78],
            score=0.8, custo=3.0, concurso_alvo_validacao=7059,
        )

        atualizados = db.atualizar_acertos_pendentes(7059, [27, 47, 57, 70, 78])

        assert atualizados == 1
        jogos = db.listar_jogos_gerados()
        assert jogos[0]["acertos"] == 5

    def test_nao_atualiza_concurso_diferente(self, db):
        db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[27, 47, 57, 70, 78],
            score=0.8, custo=3.0, concurso_alvo_validacao=9999,
        )

        atualizados = db.atualizar_acertos_pendentes(7059, [27, 47, 57, 70, 78])

        assert atualizados == 0

    def test_acertos_parciais(self, db):
        db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[1, 2, 3, 47, 78],
            score=0.8, custo=3.0, concurso_alvo_validacao=7059,
        )

        db.atualizar_acertos_pendentes(7059, [27, 47, 57, 70, 78])

        jogos = db.listar_jogos_gerados()
        assert jogos[0]["acertos"] == 2
