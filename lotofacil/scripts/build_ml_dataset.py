"""Gera o dataset ML canônico, o schema.json e o dicionário de dados.

Uso:
    python scripts/build_ml_dataset.py
"""

import logging
from pathlib import Path

from lotofacil.infra.config import SAIDA_DIR
from lotofacil.experimentos.data import dataset_ml

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    out_dir = SAIDA_DIR / "datasets"
    out_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)

    log.info("Montando tabela canônica (join sorteio+clima+lua)...")
    df = dataset_ml.build_dataset()
    parquet_path = out_dir / "lotofacil_ml.parquet"
    csv_path = out_dir / "lotofacil_ml.csv"
    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)
    log.info("Dataset: %d concursos, %d colunas", len(df), len(df.columns))
    log.info("  -> %s", parquet_path)
    log.info("  -> %s", csv_path)

    schema_path = out_dir / "schema.json"
    dataset_ml.write_schema_json(schema_path)
    log.info("Schema: %s", schema_path)

    dic_path = docs_dir / "dicionario_dados_ml.md"
    dataset_ml.generate_data_dictionary_md(dic_path)
    log.info("Dicionário: %s", dic_path)

    cobertura_clima = df["tem_clima"].mean() * 100
    cobertura_lua = df["tem_lua"].mean() * 100
    log.info("Cobertura clima: %.1f%% | lua: %.1f%%", cobertura_clima, cobertura_lua)


if __name__ == "__main__":
    main()
