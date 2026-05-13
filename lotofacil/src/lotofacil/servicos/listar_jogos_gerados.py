from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from lotofacil.infra.config import JOGOS_DIR


@dataclass(frozen=True)
class JogoGeradoInfo:
    nome_arquivo: str
    caminho: Path
    tamanho_bytes: int
    concurso: Optional[int] = None


def listar_jogos_gerados() -> List[JogoGeradoInfo]:
    if not JOGOS_DIR.exists():
        return []

    jogos: List[JogoGeradoInfo] = []
    for f in sorted(JOGOS_DIR.iterdir()):
        if f.is_file() and f.suffix == ".json":
            concurso = None
            parts = f.stem.split("_")
            if len(parts) >= 2 and parts[-1].isdigit():
                concurso = int(parts[-1])
            jogos.append(
                JogoGeradoInfo(
                    nome_arquivo=f.name,
                    caminho=f,
                    tamanho_bytes=f.stat().st_size,
                    concurso=concurso,
                )
            )
    return jogos
