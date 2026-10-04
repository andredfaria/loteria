"""Adapter Mega-Sena para o banco compartilhado do pacote núcleo."""
from __future__ import annotations

from pathlib import Path

from loteria_nucleo.dados.banco import BancoSorteios
from megasena.infra.config import get_db_path


class DatabaseManager(BancoSorteios):
    """Mantém o nome e o caminho padrão públicos da aplicação Mega-Sena."""

    def __init__(self, db_path: Path | None = None):
        super().__init__(db_path or get_db_path())
