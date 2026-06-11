"""Prevê as 15 dezenas do próximo concurso com o modelo_ordem (LightGBM).

Wrapper fino — equivalente a `lotofacil lab prever-ordem`. Requer um modelo
previamente treinado com `lotofacil lab train-ordem` (ou `train_modelo_ordem.py`).

ATENÇÃO (honestidade): a Lotofácil é um sorteio físico justo. Na avaliação fora
de amostra este modelo empata com o acaso (AUC ≈ 0.5, ~9 acertos@15, igual a um
palpite aleatório). Esta predição NÃO tem vantagem estatística real — é apenas o
ranking do modelo, equivalente na prática a uma aposta estruturada.

Uso:
    python scripts/prever_proximo.py
"""

from lotofacil.experimentos.main import app

if __name__ == "__main__":
    app(["prever-ordem"])
