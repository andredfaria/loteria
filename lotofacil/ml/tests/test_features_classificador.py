import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest
from features_classificador import calcular_features_numero, montar_dataset

def make_concurso(numero_concurso, dezenas):
    return {'concurso': numero_concurso, 'dezenas': dezenas}

HISTORICO = [
    make_concurso(1,  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]),
    make_concurso(2,  [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]),
    make_concurso(3,  [3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]),
    make_concurso(4,  [4,5,6,7,8,9,10,11,12,13,14,15,16,17,18]),
    make_concurso(5,  [5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]),
]

def test_no_ultimo_verdadeiro():
    feats = calcular_features_numero(HISTORICO, 19)
    assert feats['no_ultimo'] == 1

def test_no_ultimo_falso():
    feats = calcular_features_numero(HISTORICO, 1)
    assert feats['no_ultimo'] == 0

def test_ciclo_ausente_verdadeiro():
    feats = calcular_features_numero(HISTORICO, 1)
    assert feats['ciclo_ausente'] == 1

def test_ciclo_ausente_falso():
    feats = calcular_features_numero(HISTORICO, 10)
    assert feats['ciclo_ausente'] == 0

def test_freq_k5_numero_presente_sempre():
    feats = calcular_features_numero(HISTORICO, 10)
    assert feats['freq_k5'] == pytest.approx(1.0)

def test_freq_k5_numero_ausente():
    feats = calcular_features_numero(HISTORICO, 25)
    assert feats['freq_k5'] == pytest.approx(0.0)

def test_atraso_numero_nunca_apareceu():
    feats = calcular_features_numero(HISTORICO, 25)
    assert feats['atraso'] == len(HISTORICO)

def test_atraso_numero_ultimo_concurso():
    feats = calcular_features_numero(HISTORICO, 19)
    assert feats['atraso'] == 0

def test_par_numero_par():
    feats = calcular_features_numero(HISTORICO, 4)
    assert feats['par'] == 1

def test_par_numero_impar():
    feats = calcular_features_numero(HISTORICO, 5)
    assert feats['par'] == 0

def test_faixa_baixa():
    feats = calcular_features_numero(HISTORICO, 3)
    assert feats['faixa'] == 0

def test_faixa_media():
    feats = calcular_features_numero(HISTORICO, 12)
    assert feats['faixa'] == 1

def test_faixa_alta():
    feats = calcular_features_numero(HISTORICO, 20)
    assert feats['faixa'] == 2

def test_soma_contribution():
    feats = calcular_features_numero(HISTORICO, 25)
    assert feats['soma_contribution'] == pytest.approx(25 / 25.0)

def test_montar_dataset_shape():
    import pandas as pd
    X, y = montar_dataset(HISTORICO, warmup=3)
    assert len(X) == 50
    assert len(y) == 50
    assert list(X.columns) == [
        'numero', 'freq_k5', 'freq_k15', 'freq_k30', 'freq_k100',
        'freq_all', 'atraso', 'no_ultimo', 'ciclo_ausente',
        'par', 'faixa', 'soma_contribution',
    ]

def test_montar_dataset_target_15_por_concurso():
    X, y = montar_dataset(HISTORICO, warmup=3)
    assert y.sum() == 30

def test_montar_dataset_vazio_retorna_estrutura_correta():
    import pandas as pd
    X, y = montar_dataset(HISTORICO, warmup=100)  # warmup > len(HISTORICO)
    assert len(X) == 0
    assert list(X.columns) == [
        'numero', 'freq_k5', 'freq_k15', 'freq_k30', 'freq_k100',
        'freq_all', 'atraso', 'no_ultimo', 'ciclo_ausente',
        'par', 'faixa', 'soma_contribution',
    ]
