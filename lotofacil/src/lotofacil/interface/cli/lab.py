"""lab subcommands — re-exposes lotofacil_lab Typer app."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Re-export: o app raiz faz `from ...cli.lab import app`. O ruff lê isso como
# import nao usado — ver a per-file-ignore de F401 em ruff.toml.
from lotofacil.experimentos.main import app  # noqa: F401,E402
