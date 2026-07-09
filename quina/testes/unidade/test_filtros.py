from quina.servicos.estrategias import filtros


def _draws(*listas_dezenas):
    return [{"concurso": i + 1, "data": "", "dezenas": d} for i, d in enumerate(listas_dezenas)]


class TestScoreSoma:
    def test_soma_igual_a_media_historica_escalada_e_score_maximo(self):
        draws = _draws([10, 20, 30, 40, 50])  # soma=150, unica amostra -> desvio=0 -> fallback 1.0
        candidato = [10, 20, 30, 40, 50]  # soma=150, mesmo fator (n=5)
        assert filtros.score_soma(candidato, draws) == 1.0

    def test_soma_muito_distante_da_media_e_score_minimo(self):
        draws = _draws([10, 20, 30, 40, 50])  # media=150, desvio fallback=1.0
        candidato = [41, 42, 43, 44, 80]  # soma=250, diff=100 >> 2*1.0
        assert filtros.score_soma(candidato, draws) == 0.0


class TestScoreParidade:
    def test_equilibrado_e_score_maximo(self):
        assert filtros.score_paridade([1, 2, 3, 4]) == 1.0  # 2 pares, 2 impares, ideal=2

    def test_todos_pares_e_score_minimo(self):
        assert filtros.score_paridade([2, 4, 6, 8]) == 0.0  # 4 pares, ideal=2, desvio max


class TestScoreQuadrantes:
    def test_um_por_quadrante_e_score_maximo(self):
        assert filtros.score_quadrantes([10, 30, 50, 70]) == 1.0

    def test_todos_no_mesmo_quadrante_e_score_minimo(self):
        assert filtros.score_quadrantes([1, 2, 3, 4]) == 0.0


class TestScorePrimos:
    def test_proporcao_igual_ao_universo_e_score_maximo(self):
        candidato = list(range(1, 81))  # 22 primos em 80 = mesma proporcao do universo
        assert filtros.score_primos(candidato) == 1.0

    def test_so_primos_e_score_minimo(self):
        assert filtros.score_primos([2, 3, 5, 7, 11]) == 0.0


class TestScoreRepeticao:
    def test_sem_sobreposicao_historica_e_sem_sobreposicao_no_candidato_e_score_maximo(self):
        draws = _draws([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])  # 0 overlap entre os 2 sorteios
        candidato = [1, 2, 3, 4, 5]  # 0 overlap com o ultimo sorteio [6..10]
        assert filtros.score_repeticao(candidato, draws) == 1.0

    def test_repeticao_total_quando_esperado_e_zero_e_score_minimo(self):
        draws = _draws([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])
        candidato = [6, 7, 8, 9, 10]  # repete 100% do ultimo sorteio
        assert filtros.score_repeticao(candidato, draws) == 0.0


class TestScoreConsecutivos:
    def test_sem_consecutivos_historicos_e_sem_consecutivos_no_candidato_e_score_maximo(self):
        draws = _draws([1, 3, 5, 7, 9])  # 0 pares consecutivos
        candidato = [10, 20, 30, 40, 50]  # 0 pares consecutivos
        assert filtros.score_consecutivos(candidato, draws) == 1.0

    def test_totalmente_consecutivo_quando_esperado_e_zero_e_score_minimo(self):
        draws = _draws([1, 3, 5, 7, 9])
        candidato = [1, 2, 3, 4, 5]  # 4 pares consecutivos
        assert filtros.score_consecutivos(candidato, draws) == 0.0


class TestScoreAntiPopularidade:
    def test_sem_numeros_populares_e_score_maximo(self):
        assert filtros.score_anti_popularidade([40, 50, 60, 70, 80]) == 1.0

    def test_so_numeros_populares_e_score_minimo(self):
        assert filtros.score_anti_popularidade([1, 2, 3, 4, 5]) == 0.0
