import json
import os
import random
import tempfile

import pytest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from analisar_diadesorte import (
    carregar_dados,
    calc_frequencia,
    calc_atraso,
    calc_distribuicao_paridade,
    calc_distribuicao_faixa,
    calc_frequencia_mes,
    calcular_metricas,
    gerar_jogo,
    gerar_e_ranquear,
    TODOS_MESES,
    TODOS_NUMEROS,
    CONFIG_PADRAO,
)


def _fazer_json(tmp_dir, n, numeros, mes):
    data = {
        "concurso": n,
        "data": "01/01/2020",
        "dezenas": [str(x).zfill(2) for x in numeros],
        "mesSorte": mes,
    }
    path = os.path.join(tmp_dir, f"diadesorte_{n}.json")
    with open(path, "w") as f:
        json.dump(data, f)


HISTORICO_FIXO = [
    {"concurso": 1, "data": "01/01/2019", "numeros": [1, 2, 3, 4, 5, 6, 7],  "mes_sorte": "Janeiro"},
    {"concurso": 2, "data": "03/01/2019", "numeros": [1, 2, 3, 4, 5, 6, 8],  "mes_sorte": "Março"},
    {"concurso": 3, "data": "05/01/2019", "numeros": [1, 2, 3, 4, 5, 6, 9],  "mes_sorte": "Março"},
]

random.seed(0)
HISTORICO_GRANDE = [
    {
        "concurso": i,
        "data": "01/01/2020",
        "numeros": sorted(random.sample(range(1, 32), 7)),
        "mes_sorte": TODOS_MESES[i % 12],
    }
    for i in range(1, 101)
]


def test_carregar_diretorio_retorna_lista_ordenada():
    with tempfile.TemporaryDirectory() as tmp:
        _fazer_json(tmp, 2, [5, 10, 15, 20, 25, 27, 30], "Março")
        _fazer_json(tmp, 1, [1, 2, 3, 4, 5, 6, 7], "Janeiro")
        historico = carregar_dados(tmp)
    assert len(historico) == 2
    assert historico[0]["concurso"] == 1
    assert historico[1]["concurso"] == 2


def test_normalizar_dezenas_para_ints():
    with tempfile.TemporaryDirectory() as tmp:
        _fazer_json(tmp, 1, [1, 2, 3, 4, 5, 6, 7], "Janeiro")
        historico = carregar_dados(tmp)
    assert historico[0]["numeros"] == [1, 2, 3, 4, 5, 6, 7]
    assert all(isinstance(n, int) for n in historico[0]["numeros"])


def test_normalizar_mes_sorte():
    with tempfile.TemporaryDirectory() as tmp:
        _fazer_json(tmp, 1, [1, 2, 3, 4, 5, 6, 7], "Outubro")
        historico = carregar_dados(tmp)
    assert historico[0]["mes_sorte"] == "Outubro"


def test_carregar_json_lista():
    raw = [
        {"concurso": 1, "data": "01/01/2020",
         "dezenas": ["01", "02", "03", "04", "05", "06", "07"], "mesSorte": "Janeiro"},
        {"concurso": 2, "data": "03/01/2020",
         "dezenas": ["08", "09", "10", "11", "12", "13", "14"], "mesSorte": "Fevereiro"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(raw, f)
        path = f.name
    try:
        historico = carregar_dados(path)
        assert len(historico) == 2
        assert historico[1]["numeros"] == [8, 9, 10, 11, 12, 13, 14]
    finally:
        os.unlink(path)


def test_erro_formato_desconhecido():
    with pytest.raises(ValueError):
        carregar_dados("arquivo.xlsx")


def test_frequencia_conta_aparicoes():
    freq = calc_frequencia(HISTORICO_FIXO)
    assert freq[1] == 3
    assert freq[7] == 1
    assert freq[8] == 1
    assert freq[9] == 1
    assert freq[31] == 0


def test_atraso_numero_nunca_visto():
    atraso = calc_atraso(HISTORICO_FIXO)
    assert atraso[31] == 3


def test_atraso_numero_mais_recente():
    atraso = calc_atraso(HISTORICO_FIXO)
    assert atraso[9] == 0


def test_atraso_numero_intermediario():
    atraso = calc_atraso(HISTORICO_FIXO)
    assert atraso[7] == 2


def test_paridade_media():
    par = calc_distribuicao_paridade(HISTORICO_FIXO)
    assert abs(par["media_pares"] - (3 + 4 + 3) / 3) < 0.01
    assert abs(par["media_impares"] - (4 + 3 + 4) / 3) < 0.01


def test_faixa_media():
    faixa = calc_distribuicao_faixa(HISTORICO_FIXO)
    assert abs(faixa["media_baixos"] - 7.0) < 0.01
    assert abs(faixa["media_altos"] - 0.0) < 0.01


def test_frequencia_mes():
    freq_mes = calc_frequencia_mes(HISTORICO_FIXO)
    assert freq_mes["Janeiro"] == 1
    assert freq_mes["Março"] == 2
    assert freq_mes["Fevereiro"] == 0


def test_calcular_metricas_retorna_todas_chaves():
    m = calcular_metricas(HISTORICO_FIXO)
    assert "frequencia" in m
    assert "atraso" in m
    assert "paridade" in m
    assert "faixa" in m
    assert "frequencia_mes" in m
    assert m["total_concursos"] == 3


def test_jogo_tem_7_numeros():
    random.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogo = gerar_jogo(m, CONFIG_PADRAO)
    assert len(jogo["numeros"]) == 7


def test_jogo_numeros_dentro_do_intervalo():
    random.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogo = gerar_jogo(m, CONFIG_PADRAO)
    assert all(1 <= n <= 31 for n in jogo["numeros"])


def test_jogo_numeros_sem_repeticao():
    random.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogo = gerar_jogo(m, CONFIG_PADRAO)
    assert len(set(jogo["numeros"])) == 7


def test_jogo_mes_sorte_valido():
    random.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogo = gerar_jogo(m, CONFIG_PADRAO)
    assert jogo["mes_sorte"] in TODOS_MESES


def test_jogo_tem_razoes_para_cada_numero():
    random.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogo = gerar_jogo(m, CONFIG_PADRAO)
    for n in jogo["numeros"]:
        assert n in jogo["razoes"]
        assert isinstance(jogo["razoes"][n], str)
        assert len(jogo["razoes"][n]) > 0


def test_jogo_score_entre_0_e_100():
    random.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogo = gerar_jogo(m, CONFIG_PADRAO)
    assert 0 <= jogo["score"] <= 100


def test_todas_estrategias_geram_jogo_valido():
    random.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    for estrategia in ["frequentes", "atrasados", "mista", "equilibrada"]:
        cfg = {**CONFIG_PADRAO, "estrategia": estrategia}
        jogo = gerar_jogo(m, cfg)
        assert len(jogo["numeros"]) == 7, f"Falhou para estratégia: {estrategia}"
        assert all(1 <= n <= 31 for n in jogo["numeros"])
        assert jogo["mes_sorte"] in TODOS_MESES


def test_ranquear_retorna_n_jogos():
    random.seed(99)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogos = gerar_e_ranquear(m, CONFIG_PADRAO, n_jogos=5)
    assert len(jogos) == 5


def test_ranquear_ordenado_por_score_desc():
    random.seed(99)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogos = gerar_e_ranquear(m, CONFIG_PADRAO, n_jogos=10)
    scores = [j["score"] for j in jogos]
    assert scores == sorted(scores, reverse=True)


def test_ranquear_todos_jogos_validos():
    random.seed(99)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogos = gerar_e_ranquear(m, CONFIG_PADRAO, n_jogos=5)
    for jogo in jogos:
        assert len(jogo["numeros"]) == 7
        assert all(1 <= n <= 31 for n in jogo["numeros"])
        assert jogo["mes_sorte"] in TODOS_MESES
