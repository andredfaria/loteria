"""Resolução de caminhos configuráveis sem efeitos colaterais na importação."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from loteria_nucleo.spec import LoteriaSpec


@dataclass(frozen=True)
class Caminhos:
    raiz: Path
    dados: Path
    saida: Path
    banco: Path


def caminhos_do_projeto(
    spec: LoteriaSpec, raiz: Path, banco_padrao: str | None = None
) -> Caminhos:
    prefixo = spec.prefixo_env
    dados = Path(os.environ.get(f"{prefixo}_DADOS_DIR", raiz / "dados"))
    saida = Path(os.environ.get(f"{prefixo}_SAIDA_DIR", raiz / "saida"))
    padrao = banco_padrao or f"{spec.slug}.db"
    banco = Path(os.environ.get(f"{prefixo}_DB_PATH", dados / padrao))
    return Caminhos(raiz=raiz, dados=dados, saida=saida, banco=banco)
