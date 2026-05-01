"""
Backtest walk-forward: re-treina o modelo para cada um dos últimos N concursos
e mede acertos, comparando com o baseline de 9.20 (20%ML + 80% padrões).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import pandas as pd
import lightgbm as lgb

from features_classificador import calcular_features_numero, montar_dataset
from geracao.gerador_jogos_lotofacil import carregar_dados_historicos

N_BACKTEST = 30
WARMUP = 100
BASELINE_MEDIA = 9.20


def treinar_modelo(X_train, y_train):
    model = lgb.LGBMClassifier(
        n_estimators=200,
        learning_rate=0.01,
        num_leaves=15,
        min_child_samples=5,
        objective='binary',
        class_weight='balanced',
        random_state=42,
        verbose=-1,
    )
    model.fit(X_train, y_train)
    return model


def predizer_com_modelo(model, historico):
    rows = [calcular_features_numero(historico, n) for n in range(1, 26)]
    X = pd.DataFrame(rows)
    probs = model.predict_proba(X)[:, 1]
    jogo = sorted([int(i) + 1 for i in np.argsort(probs)[-15:]])
    return jogo


def backtest(todos_concursos, n=N_BACKTEST):
    resultados = []
    alvos = todos_concursos[-n:]

    for i, alvo in enumerate(alvos):
        idx_alvo = len(todos_concursos) - n + i
        historico = todos_concursos[:idx_alvo]

        if len(historico) < WARMUP + 1:
            print(f"  Concurso {alvo['concurso']}: histórico insuficiente, pulando.")
            continue

        print(f"  [{i+1:02d}/{n}] Concurso {alvo['concurso']}: treinando...", end=' ', flush=True)
        X_train, y_train = montar_dataset(historico, warmup=WARMUP)
        model = treinar_modelo(X_train, y_train)

        jogo = predizer_com_modelo(model, historico)
        acertos = len(set(jogo) & set(alvo['dezenas']))
        resultados.append((alvo['concurso'], jogo, sorted(alvo['dezenas']), acertos))
        print(f"{acertos} acertos")

    return resultados


def main():
    print("Carregando dados históricos...")
    todos = carregar_dados_historicos()
    print(f"  {len(todos)} concursos.\n")

    print(f"Backtest walk-forward — últimos {N_BACKTEST} concursos:\n")
    resultados = backtest(todos)

    acertos_lista = [r[3] for r in resultados]
    media = np.mean(acertos_lista)
    maximo = max(acertos_lista)
    minimo = min(acertos_lista)
    dist = {p: acertos_lista.count(p) for p in range(7, 16)}

    print(f"\n{'='*60}")
    print(f"  Média de acertos : {media:.2f}")
    print(f"  Mínimo           : {minimo}")
    print(f"  Máximo           : {maximo}")
    print(f"  Baseline atual   : {BASELINE_MEDIA:.2f}")
    delta = media - BASELINE_MEDIA
    sinal = '+' if delta >= 0 else ''
    print(f"  Delta vs baseline: {sinal}{delta:.2f}")
    print(f"\n  Distribuição de acertos:")
    for p in range(7, 16):
        barra = '█' * dist.get(p, 0)
        print(f"    {p:2d} pts: {dist.get(p, 0):2d}x  {barra}")
    print(f"{'='*60}")

    print(f"\nDetalhe por concurso:")
    print(f"  {'Concurso':>10}  {'Pts':>3}  Jogo gerado")
    print(f"  {'-'*55}")
    for num, jogo, resultado, pts in resultados:
        print(f"  {num:>10}  {pts:>3}  {jogo}")


if __name__ == '__main__':
    main()
