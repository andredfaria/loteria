"""Treina LightGBM binário para prever quais números sairão no próximo concurso."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import joblib
import pandas as pd
import lightgbm as lgb
from pathlib import Path

from features_classificador import montar_dataset
from geracao.gerador_jogos_lotofacil import carregar_dados_historicos

WARMUP = 100
MODEL_PATH = Path(__file__).parent / 'modelos' / 'classificador_numero.joblib'


def treinar():
    print("Carregando dados históricos...")
    concursos = carregar_dados_historicos()
    if not concursos:
        print("ERRO: Nenhum dado histórico encontrado. Execute busca_sorteios.py primeiro.")
        return None
    print(f"  {len(concursos)} concursos disponíveis.")

    print(f"\nMontando dataset (warmup={WARMUP})...")
    X, y = montar_dataset(concursos, warmup=WARMUP)
    print(f"  Dataset: {X.shape[0]} linhas × {X.shape[1]} features")
    print(f"  Positivos: {y.sum()} ({y.mean()*100:.1f}%)")

    split = int(len(X) * 0.8)
    X_train, X_val = X.iloc[:split], X.iloc[split:]
    y_train, y_val = y.iloc[:split], y.iloc[split:]
    print(f"  Treino: {len(X_train)} linhas | Validação: {len(X_val)} linhas")

    print("\nTreinando LightGBM...")
    model = lgb.LGBMClassifier(
        n_estimators=500,
        learning_rate=0.01,
        num_leaves=15,
        min_child_samples=5,
        objective='binary',
        metric='binary_logloss',
        class_weight='balanced',
        random_state=42,
        verbose=-1,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(100)],
    )

    print("\nFeature importances (gain):")
    importances = pd.Series(
        model.booster_.feature_importance(importance_type='gain'),
        index=X.columns,
    ).sort_values(ascending=False)
    for feat, imp in importances.items():
        print(f"  {feat:<22} {imp:.1f}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"\nModelo salvo em {MODEL_PATH}")
    return model


if __name__ == '__main__':
    treinar()
