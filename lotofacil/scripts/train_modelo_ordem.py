"""Treina o modelo_ordem (LightGBM) e gera relatório honesto.

Wrapper fino — equivalente a `lotofacil lab train-ordem`.

Uso:
    python scripts/train_modelo_ordem.py
"""

from lotofacil.experimentos.main import app

if __name__ == "__main__":
    app(["train-ordem"])
