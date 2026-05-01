"""
Preditor combinado: score de padrões dos últimos 21 draws + LightGBM.
Encontra alpha ótimo via backtest walk-forward e gera jogo para o próximo concurso.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from padroes_21 import calcular_score_padroes
from features_classificador import calcular_features_numero
from geracao.gerador_jogos_lotofacil import carregar_dados_historicos

MODEL_PATH = Path(__file__).parent / 'modelos' / 'classificador_numero.joblib'
OUTPUT_DIR = Path(__file__).parent.parent / 'saida' / 'jogos'
N_BACKTEST = 30
JANELA_PADROES = 21
BASELINE = 9.20


def obter_prob_ml(model, historico: list) -> np.ndarray:
    rows = [calcular_features_numero(historico, n) for n in range(1, 26)]
    X = pd.DataFrame(rows)
    return model.predict_proba(X)[:, 1]


def _normalizar(arr: np.ndarray) -> np.ndarray:
    lo, hi = arr.min(), arr.max()
    if hi > lo:
        return (arr - lo) / (hi - lo)
    return np.full(len(arr), 0.5)


def combinar_e_selecionar(score_padroes: list, prob_ml: np.ndarray, alpha: float) -> list:
    norm_p = _normalizar(np.array(score_padroes))
    norm_m = _normalizar(prob_ml)
    score_final = alpha * norm_p + (1.0 - alpha) * norm_m
    return sorted([int(i) + 1 for i in np.argsort(score_final)[-15:]])


def aplicar_filtro_soma(jogo: list) -> list:
    """Troca números para manter soma entre 171–220."""
    todos = set(range(1, 26))
    dentro = list(jogo)
    fora = sorted(todos - set(dentro))
    soma = sum(dentro)
    tentativas = 0

    while soma < 171 and fora and tentativas < 20:
        maiores_fora = [n for n in fora if n > min(dentro)]
        if not maiores_fora:
            break
        sai = min(dentro)
        entra = min(maiores_fora)
        dentro.remove(sai)
        fora.remove(entra)
        fora.append(sai)
        dentro.append(entra)
        soma = sum(dentro)
        tentativas += 1

    tentativas = 0
    while soma > 220 and fora and tentativas < 20:
        menores_fora = [n for n in fora if n < max(dentro)]
        if not menores_fora:
            break
        sai = max(dentro)
        entra = max(menores_fora)
        dentro.remove(sai)
        fora.remove(entra)
        fora.append(sai)
        dentro.append(entra)
        soma = sum(dentro)
        tentativas += 1

    return sorted(dentro)


def aplicar_filtro_consecutivo(jogo: list) -> list:
    """Garante ao menos 1 par de números consecutivos no jogo."""
    nums = sorted(jogo)
    tem_consecutivo = any(nums[i+1] == nums[i] + 1 for i in range(len(nums)-1))
    if tem_consecutivo:
        return jogo

    # Sem consecutivo: trocar o número de maior freq_21 por seu vizinho disponível
    todos = set(range(1, 26))
    fora = sorted(todos - set(jogo))
    for n in sorted(jogo):
        for viz in [n - 1, n + 1]:
            if 1 <= viz <= 25 and viz in fora:
                dentro = list(jogo)
                dentro.remove(n)
                dentro.append(viz)
                return sorted(dentro)
    return jogo  # fallback: não foi possível ajustar


def backtest_alphas(todos: list, model, alphas: list) -> dict:
    resultados: dict = {a: [] for a in alphas}
    alvos = todos[-N_BACKTEST:]

    for i, alvo in enumerate(alvos):
        idx = len(todos) - N_BACKTEST + i
        historico = todos[:idx]
        if len(historico) < JANELA_PADROES + 1:
            continue

        score_p = calcular_score_padroes(historico, janela=JANELA_PADROES)
        prob_m = obter_prob_ml(model, historico)

        for alpha in alphas:
            jogo = combinar_e_selecionar(score_p, prob_m, alpha)
            jogo = aplicar_filtro_soma(jogo)
            jogo = aplicar_filtro_consecutivo(jogo)
            acertos = len(set(jogo) & set(alvo['dezenas']))
            resultados[alpha].append(acertos)

    return resultados


def main():
    if not MODEL_PATH.exists():
        print(f"Modelo não encontrado: {MODEL_PATH}")
        print("Execute primeiro: python ml/treino_classificador.py")
        return

    print("Carregando dados e modelo...")
    todos = carregar_dados_historicos()
    if not todos:
        print("ERRO: Nenhum dado histórico encontrado.")
        return
    model = joblib.load(MODEL_PATH)

    alphas = [round(a * 0.1, 1) for a in range(0, 11)]

    print(f"\nBacktest walk-forward ({N_BACKTEST} concursos, alpha 0.0→1.0)...\n")
    resultados = backtest_alphas(todos, model, alphas)

    medias = {a: np.mean(v) for a, v in resultados.items() if v}

    if not medias:
        print("ERRO: Backtest não produziu resultados (histórico insuficiente).")
        return

    print(f"  {'Alpha':>5}  {'Padrões':>7}  {'ML':>5}  {'Média':>6}")
    print("  " + "-" * 35)
    for a in alphas:
        if a in medias:
            print(f"  {a:.1f}     {a*100:>5.0f}%   {100-a*100:>4.0f}%   {medias[a]:>6.2f}")

    alpha_otimo = max(medias, key=medias.get)
    media_otima = medias[alpha_otimo]
    delta = media_otima - BASELINE
    sinal = '+' if delta >= 0 else ''

    print(f"\n  Alpha ótimo  : {alpha_otimo} ({alpha_otimo*100:.0f}% padrões + {100-alpha_otimo*100:.0f}% ML)")
    print(f"  Média acertos: {media_otima:.2f}")
    print(f"  Baseline     : {BASELINE:.2f}")
    print(f"  Delta        : {sinal}{delta:.2f}")

    # Jogo final com histórico completo
    ultimo = todos[-1]['concurso']
    proximo = ultimo + 1
    score_p = calcular_score_padroes(todos, janela=JANELA_PADROES)
    prob_m = obter_prob_ml(model, todos)
    jogo = combinar_e_selecionar(score_p, prob_m, alpha_otimo)
    jogo = aplicar_filtro_soma(jogo)
    jogo = aplicar_filtro_consecutivo(jogo)

    print(f"\nJogo previsto para o concurso {proximo} (alpha={alpha_otimo}):")
    print(f"  {', '.join(f'{n:02d}' for n in jogo)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f'jogo_combinado_{proximo}.json'
    output_path.write_text(json.dumps({
        'concurso': proximo,
        'metodo': 'combinado_padroes21_lgbm',
        'alpha': alpha_otimo,
        'jogo': jogo,
        'score_padroes': {str(i + 1): round(float(score_p[i]), 4) for i in range(25)},
        'prob_ml': {str(i + 1): round(float(prob_m[i]), 4) for i in range(25)},
    }, indent=2, ensure_ascii=False))
    print(f"Salvo em {output_path}")


if __name__ == '__main__':
    main()
