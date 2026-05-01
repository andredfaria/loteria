from __future__ import annotations
from typing import Dict, List, Tuple
import pandas as pd


def calcular_features_numero(historico: List[Dict], numero: int) -> Dict:
    """
    Calcula as 12 features para um número dado um histórico de concursos.
    historico: concursos ANTERIORES ao concurso alvo (não inclui o alvo).
    """
    n = len(historico)

    def freq_janela(k: int) -> float:
        janela = historico[-k:] if n >= k else historico
        if not janela:
            return 0.0
        return sum(1 for c in janela if numero in c['dezenas']) / len(janela)

    # Atraso: quantos concursos desde a última aparição
    atraso = n  # nunca apareceu: distância máxima possível
    for i, c in enumerate(reversed(historico)):
        if numero in c['dezenas']:
            atraso = i
            break

    no_ultimo = 1 if historico and numero in historico[-1]['dezenas'] else 0

    # Ciclo: ausente nos últimos 4 concursos
    ultimos4: set = set()
    for c in historico[-4:]:
        ultimos4.update(c['dezenas'])
    ciclo_ausente = 1 if numero not in ultimos4 else 0

    freq_all = sum(1 for c in historico if numero in c['dezenas']) / n if n > 0 else 0.0

    if numero <= 8:
        faixa = 0
    elif numero <= 17:
        faixa = 1
    else:
        faixa = 2

    return {
        'numero': numero,
        'freq_k5': freq_janela(5),
        'freq_k15': freq_janela(15),
        'freq_k30': freq_janela(30),
        'freq_k100': freq_janela(100),
        'freq_all': freq_all,
        'atraso': atraso,
        'no_ultimo': no_ultimo,
        'ciclo_ausente': ciclo_ausente,
        'par': 1 if numero % 2 == 0 else 0,
        'faixa': faixa,
        'soma_contribution': numero / 25.0,
    }


def montar_dataset(concursos: List[Dict], warmup: int = 100) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Monta dataset supervisionado: para cada concurso t >= warmup e cada número 1-25,
    calcula features usando historico[:t] e registra y=1 se número saiu em concurso t.
    """
    rows = []
    for idx in range(warmup, len(concursos)):
        historico = concursos[:idx]
        alvo = concursos[idx]
        dezenas_alvo = set(alvo['dezenas'])
        for numero in range(1, 26):
            feats = calcular_features_numero(historico, numero)
            feats['y'] = 1 if numero in dezenas_alvo else 0
            rows.append(feats)

    feature_cols = [
        'numero', 'freq_k5', 'freq_k15', 'freq_k30', 'freq_k100',
        'freq_all', 'atraso', 'no_ultimo', 'ciclo_ausente',
        'par', 'faixa', 'soma_contribution',
    ]
    if not rows:
        return pd.DataFrame(columns=feature_cols), pd.Series(dtype=int)
    df = pd.DataFrame(rows)
    X = df[feature_cols]
    y = df['y']
    return X, y
