from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from lotofacil.infra.config import MODELOS_DIR


@dataclass(frozen=True)
class ListaModelos:
    modelos: list[dict]
    total: int


def listar_modelos_treinados(
    modelos_dir: Optional[Path] = None,
) -> ListaModelos:
    modelos_dir = modelos_dir or MODELOS_DIR
    modelos: list[dict] = []

    if modelos_dir.exists():
        for entry in sorted(modelos_dir.iterdir()):
            if entry.is_file():
                stat = entry.stat()
                modelos.append({
                    "nome": entry.name,
                    "caminho": str(entry),
                    "tamanho_bytes": stat.st_size,
                    "modificado_em": stat.st_mtime,
                })

    return ListaModelos(modelos=modelos, total=len(modelos))
