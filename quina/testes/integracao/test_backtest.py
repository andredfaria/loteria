from pathlib import Path

import pytest

from quina.infra.dados.leitor import load_draws
from quina.servicos.backtest import rodar_backtest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "sample_draws"


def _draws_como_dicts():
    return [
        {"concurso": d.concurso, "data": d.data, "dezenas": d.dezenas}
        for d in load_draws(FIXTURES_DIR)
    ]


class TestRodarBacktest:
    def test_estrutura_do_resultado(self):
        resultado = rodar_backtest(estrategia="frequencia_atraso", janela=5, draws=_draws_como_dicts())

        assert set(resultado.keys()) == {
            "janela", "total_rodadas", "taxa_estrategia", "taxa_baseline", "tempo_execucao_segundos"
        }
        assert resultado["janela"] == 5
        assert resultado["total_rodadas"] == 5
        assert set(resultado["taxa_estrategia"].keys()) == {"2", "3", "4", "5"}
        assert set(resultado["taxa_baseline"].keys()) == {"2", "3", "4", "5"}

    def test_taxas_entre_zero_e_um(self):
        resultado = rodar_backtest(estrategia="frequencia_atraso", janela=5, draws=_draws_como_dicts())

        for taxa in {**resultado["taxa_estrategia"], **resultado["taxa_baseline"]}.values():
            assert 0.0 <= taxa <= 1.0

    def test_janela_maior_que_historico_e_clampada(self):
        draws = _draws_como_dicts()
        resultado = rodar_backtest(estrategia="frequencia_atraso", janela=1000, draws=draws)

        assert resultado["janela"] == len(draws) - 1
        assert resultado["total_rodadas"] == len(draws) - 1

    def test_estrategia_filtros_roda_sem_erro(self):
        resultado = rodar_backtest(estrategia="filtros", janela=3, draws=_draws_como_dicts())
        assert resultado["total_rodadas"] == 3

    def test_estrategia_desconhecida_levanta_erro(self):
        with pytest.raises(ValueError, match="desconhecida"):
            rodar_backtest(estrategia="inexistente", janela=5, draws=_draws_como_dicts())

    def test_dados_insuficientes_levanta_erro(self):
        um_concurso = [{"concurso": 1, "data": "x", "dezenas": [1, 2, 3, 4, 5]}]
        with pytest.raises(ValueError, match="insuficientes"):
            rodar_backtest(estrategia="filtros", janela=5, draws=um_concurso)
