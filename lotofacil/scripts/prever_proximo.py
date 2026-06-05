"""Prevê as 15 dezenas do próximo concurso com o Modelo A (LightGBM).

Treina em TODO o histórico rotulado disponível e gera o top-15 para o concurso
seguinte ao último sorteado.

ATENÇÃO (honestidade): a Lotofácil é um sorteio físico justo. Na avaliação fora
de amostra este modelo empata com o acaso (AUC ≈ 0.5, ~9 acertos@15, igual a um
palpite aleatório). Esta predição NÃO tem vantagem estatística real — é apenas o
ranking do modelo, equivalente na prática a uma aposta estruturada.

Uso:
    python scripts/prever_proximo.py
"""

import logging

from lotofacil.experimentos.data import dataset_ml
from lotofacil.experimentos.models import modelo_ordem_lgbm as mod

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    log.info("Construindo dataset e matriz de treino...")
    df = dataset_ml.build_dataset()
    long_df = dataset_ml.to_training_matrix(df)

    ultimo = int(df["concurso"].max())
    proximo = ultimo + 1
    log.info("Histórico: %d concursos (último = %d). Prevendo concurso %d.",
             len(df), ultimo, proximo)

    log.info("Treinando LightGBM em todo o histórico rotulado...")
    model = mod.train_model(long_df)

    inf = dataset_ml.build_inference_matrix(df)
    top15, ranking = mod.predict_top15(model, inf)

    log.info("\n===== PREDIÇÃO — CONCURSO %d =====", proximo)
    log.info("15 dezenas (ordenadas): %s", " ".join(f"{n:02d}" for n in top15))
    log.info("\nRanking completo (dezena · probabilidade):")
    for _, row in ranking.iterrows():
        marca = "★" if int(row["numero"]) in top15 else " "
        log.info("  %s %02d   %.4f", marca, int(row["numero"]), row["proba"])

    log.info("\n--- AVISO ---")
    log.info("Fora de amostra o modelo empata com o acaso (AUC ~ 0.5). Use esta "
             "predição como uma aposta estruturada, sem vantagem real. Jogue com "
             "responsabilidade.")


if __name__ == "__main__":
    main()
