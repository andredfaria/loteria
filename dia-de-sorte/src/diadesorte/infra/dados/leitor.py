import json
import logging
from pathlib import Path
from typing import List

from diadesorte.dominio.entidades import Sorteio
from diadesorte.dominio.regras import NUMEROS_POR_SORTEIO, TOTAL_NUMEROS

logger = logging.getLogger(__name__)


def load_draws(dados_dir: Path) -> List[Sorteio]:
    sorteios = []
    for path in sorted(dados_dir.glob("diadesorte_*.json")):
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
        dezenas = [int(d) for d in raw["dezenas"]]
        if len(dezenas) != NUMEROS_POR_SORTEIO:
            logger.warning("Concurso %d: expected %d dezenas, got %d", concurso, NUMEROS_POR_SORTEIO, len(dezenas))
            return None
        if not all(1 <= d <= TOTAL_NUMEROS for d in dezenas):
            logger.warning("Concurso %d: dezenas out of range 1-%d", concurso, TOTAL_NUMEROS)
            return None
        mes_sorte = raw.get("mesSorte") or raw.get("mes_sorte", "")
        return Sorteio(concurso=concurso, data=data, dezenas=sorted(dezenas), mes_sorte=mes_sorte)
    except (KeyError, ValueError, TypeError) as exc:
        logger.debug("Skipping invalid record: %s", exc)
        return None
