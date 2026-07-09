import pytest

from quina.servicos.fechamento import gerar_fechamento


class TestGerarFechamento:
    def test_pool_do_tamanho_minimo_gera_um_unico_jogo(self):
        resultado = gerar_fechamento([1, 2, 3, 4, 5], garantia=(5, 5))

        assert resultado["quantidade"] == 1
        assert resultado["jogos"] == [[1, 2, 3, 4, 5]]
        assert resultado["custo_total"] == 3.00

    def test_pool_de_6_com_garantia_quina_se_5_saem(self):
        resultado = gerar_fechamento([1, 2, 3, 4, 5, 6], garantia=(5, 5))

        # cada bilhete de 5 so cobre a si mesmo (dois subconjuntos de 5 de um
        # pool de 6 compartilham no maximo 4 elementos) -> precisa dos 6 bilhetes
        assert resultado["quantidade"] == 6
        assert resultado["custo_total"] == 18.00
        assert all(len(jogo) == 5 for jogo in resultado["jogos"])
        # todos os jogos sao distintos
        assert len({tuple(j) for j in resultado["jogos"]}) == 6

    def test_pool_com_dezenas_repetidas_levanta_erro(self):
        with pytest.raises(ValueError, match="repetidas"):
            gerar_fechamento([1, 2, 2, 3, 4], garantia=(4, 4))

    def test_pool_menor_que_5_levanta_erro(self):
        with pytest.raises(ValueError, match="pelo menos"):
            gerar_fechamento([1, 2, 3], garantia=(3, 3))

    def test_pool_maior_que_limite_levanta_erro(self):
        with pytest.raises(ValueError, match="no máximo"):
            gerar_fechamento(list(range(1, 14)), garantia=(5, 5))

    def test_faixa_fora_do_intervalo_levanta_erro(self):
        with pytest.raises(ValueError, match="faixa"):
            gerar_fechamento([1, 2, 3, 4, 5, 6], garantia=(5, 6))

    def test_k_fora_do_intervalo_levanta_erro(self):
        with pytest.raises(ValueError, match="k deve"):
            gerar_fechamento([1, 2, 3, 4, 5, 6], garantia=(2, 4))
