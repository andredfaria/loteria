import pytest

from quina.servicos.portfolio import gerar_portfolio


def _draws_fixture():
    return [
        {"concurso": 1, "data": "01/01/2026", "dezenas": [1, 2, 3, 4, 5]},
        {"concurso": 2, "data": "02/01/2026", "dezenas": [6, 7, 8, 9, 10]},
    ]


class TestGerarPortfolio:
    def test_perfil_desconhecido_levanta_erro(self):
        with pytest.raises(ValueError, match="perfil desconhecido"):
            gerar_portfolio(orcamento=100, perfil="inexistente", draws=_draws_fixture())

    def test_orcamento_invalido_levanta_erro(self):
        with pytest.raises(ValueError, match="orçamento"):
            gerar_portfolio(orcamento=0, perfil="conservador", draws=_draws_fixture())

    def test_orcamento_insuficiente_retorna_vazio(self):
        resultado = gerar_portfolio(orcamento=1.0, perfil="conservador", draws=_draws_fixture())

        assert resultado["jogos"] == []
        assert resultado["custo_total"] == 0.0
        assert resultado["orcamento_sobra"] == 1.0

    def test_conservador_gera_apenas_jogos_de_5_dezenas(self):
        resultado = gerar_portfolio(orcamento=30.0, perfil="conservador", draws=_draws_fixture())

        assert all(j["tamanho_aposta"] == 5 for j in resultado["jogos"])
        assert resultado["custo_total"] <= 30.0

    def test_custo_total_mais_sobra_igual_ao_orcamento(self):
        resultado = gerar_portfolio(orcamento=50.0, perfil="equilibrado", draws=_draws_fixture())

        assert resultado["custo_total"] <= 50.0
        assert resultado["custo_total"] + resultado["orcamento_sobra"] == pytest.approx(50.0)

    def test_agressivo_com_orcamento_suficiente_para_exatamente_um_jogo(self):
        resultado = gerar_portfolio(orcamento=1000.0, perfil="agressivo", draws=_draws_fixture())

        # custo_aposta(10)=756.00; custo_aposta(12)=2376.00 e custo_aposta(15)=9009.00
        # excedem 1000, entao so cabe 1 jogo de tamanho 10
        assert len(resultado["jogos"]) == 1
        assert resultado["jogos"][0]["tamanho_aposta"] == 10
        assert resultado["custo_total"] == 756.0
        assert resultado["orcamento_sobra"] == 244.0
