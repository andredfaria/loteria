import json
import logging
from pathlib import Path
from typing import List

from supersete.dominio.entidades import Sorteio
from supersete.dominio.regras import DIGITOS, NUM_COLUNAS

logger = logging.getLogger(__name__)


def load_draws(dados_dir: Path) -> List[Sorteio]:
    sorteios = []
    for path in sorted(dados_dir.glob("concurso_*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            sorteio = _parse_raw(raw)
            if sorteio:
                sorteios.append(sorteio)
        except Exception as exc:
            logger.debug("Skipping %s: %s", path.name, exc)
    return sorteios


def _parse_raw(raw: dict) -> Sorteio | None:
    try:
        concurso = int(raw["concurso"])
        data = str(raw.get("data", ""))
        digitos = [int(d) for d in raw["dezenas"]]
        if len(digitos) != NUM_COLUNAS:
            logger.warning("Concurso %d: expected %d digitos, got %d", concurso, NUM_COLUNAS, len(digitos))
            return None
        if not all(d in DIGITOS for d in digitos):
            logger.warning("Concurso %d: digitos out of range 0-9", concurso)
            return None
        return Sorteio(concurso=concurso, data=data, digitos=digitos)
    except (KeyError, ValueError, TypeError) as exc:
        logger.debug("Skipping invalid record: %s", exc)
        return None
