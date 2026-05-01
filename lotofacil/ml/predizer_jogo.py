"""Carrega o classificador treinado e gera o jogo top-15 para o próximo concurso."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import joblib
import pandas as pd
from pathlib import Path

from features_classificador import calcular_features_numero
from geracao.gerador_jogos_lotofacil import carregar_dados_historicos

MODEL_PATH = Path(__file__).parent / 'modelos' / 'classificador_numero.joblib'
OUTPUT_DIR = Path(__file__).parent.parent / 'saida' / 'jogos'


def predizer_jogo():
    if not MODEL_PATH.exists():
        print(f"Modelo não encontrado: {MODEL_PATH}")
        print("Execute primeiro: python ml/treino_classificador.py")
        return None

    model = joblib.load(MODEL_PATH)

    concursos = carregar_dados_historicos()
    if not concursos:
        print("ERRO: Nenhum dado histórico encontrado. Execute busca_sorteios.py primeiro.")
        return None
    ultimo_concurso = concursos[-1]['concurso']
    proximo_concurso = ultimo_concurso + 1

    rows = [calcular_features_numero(concursos, n) for n in range(1, 26)]
    X = pd.DataFrame(rows)
    probs = model.predict_proba(X)[:, 1]

    ranking = sorted(zip(range(1, 26), probs), key=lambda x: x[1], reverse=True)
    jogo = sorted([num for num, _ in ranking[:15]])

    print(f"\nJogo previsto para o concurso {proximo_concurso} (classificador LightGBM):")
    print(f"  {', '.join(f'{n:02d}' for n in jogo)}")

    print(f"\nProbabilidades por número (top 20):")
    for num, prob in ranking[:20]:
        marcado = '✓' if num in jogo else ' '
        print(f"  [{marcado}] {num:02d}  {prob:.4f}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f'jogo_classificador_{proximo_concurso}.json'
    output_path.write_text(json.dumps({
        'concurso': proximo_concurso,
        'metodo': 'classificador_lgbm',
        'jogo': jogo,
        'probabilidades': {str(num): round(float(prob), 4) for num, prob in ranking},
    }, indent=2, ensure_ascii=False))
    print(f"\nSalvo em {output_path}")
    return jogo


if __name__ == '__main__':
    predizer_jogo()
