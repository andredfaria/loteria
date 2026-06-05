"""Treina e avalia o Modelo A (LightGBM) com relatório honesto.

Uso:
    python scripts/train_modelo_ordem.py
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
    train, test = mod.temporal_split(long_df, frac=0.8)
    log.info("Treino: %d concursos | Teste: %d concursos",
             train["concurso"].nunique(), test["concurso"].nunique())

    log.info("Treinando LightGBM...")
    model = mod.train_model(train)
    metrics = mod.evaluate(model, test)

    log.info("\n===== RELATÓRIO HONESTO =====")
    log.info("Acertos@15 médio : %.3f (±%.3f)", metrics["acertos_medio"], metrics["acertos_std"])
    log.info("Baseline aleatório: %.3f", metrics["baseline_aleatorio"])
    log.info("AUC               : %.4f", metrics["auc"])
    log.info("LogLoss           : %.4f", metrics["logloss"])
    delta = metrics["acertos_medio"] - metrics["baseline_aleatorio"]
    if abs(delta) < 0.3:
        log.info("Conclusão: empate estatístico com o acaso (esperado — a ordem do "
                 "sorteio é fisicamente aleatória).")
    elif delta > 0:
        log.info("Conclusão: +%.3f acima do acaso. Investigar antes de confiar "
                 "(pode ser ruído/overfit do split).", delta)
    else:
        log.info("Conclusão: abaixo do acaso (%.3f). Consistente com sinal ausente.", delta)


if __name__ == "__main__":
    main()
