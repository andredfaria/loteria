"""Dataset ML para Lotofácil: join sorteios + clima + lua, schema e dicionário.

Fonte única de verdade: CANONICAL_COLUMNS alimenta o DataFrame, o schema.json
e o markdown do dicionário de dados.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from lotofacil.experimentos.config import DATA_DIR
from lotofacil.experimentos.data.climate_loader import load_all_climate
from lotofacil.experimentos.data.lunar_loader import (
    compute_lunar_features,
    _parse_iso,
    LUNAR_FEATURE_NAMES,
)

# ── Mapeamento clima: coluna do dataset -> chave do resumo JSON ───────────────
CLIMA_COLS = {
    "temp_min": "temp_min",
    "temp_max": "temp_max",
    "temp_media": "temp_media",
    "temp_sorteio": "temp_sorteio",
    "precip_media": "precipitacao_media",
    "precip_sorteio": "precipitacao_sorteio",
    "wcode_sorteio": "weathercode_sorteio",
    "wcode_dominante": "weathercode_dominante",
}
TEMPORAL_COLS = ["dow_sin", "dow_cos", "mes_sin", "mes_cos"]
FREQ_WINDOWS = (10, 30, 100)


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    dtype: str
    unit: str
    source: str       # sorteio | clima | lua | temporal | cobertura
    role: str         # meta | feature | alvo | cobertura
    description: str


def _build_canonical_columns() -> List[ColumnSpec]:
    cols: List[ColumnSpec] = [
        ColumnSpec("concurso", "int", "—", "sorteio", "meta", "Número do concurso (chave primária)."),
        ColumnSpec("data", "date", "YYYY-MM-DD", "sorteio", "meta", "Data do sorteio (ISO)."),
        ColumnSpec("local", "text", "—", "sorteio", "meta", "Local do sorteio."),
        ColumnSpec("dezenas", "json[int]", "—", "sorteio", "feature", "15 dezenas sorteadas, ordenadas asc."),
        ColumnSpec("dezenas_ordem_sorteio", "json[int]", "—", "sorteio", "alvo", "15 dezenas na ordem física de saída. Fonte do alvo."),
        ColumnSpec("primeira_dezena", "int", "1-25", "sorteio", "feature", "Primeira bola sorteada (derivada da ordem)."),
    ]
    for k in range(1, 26):
        cols.append(ColumnSpec(f"bola_{k:02d}", "int", "0/1", "sorteio", "feature",
                               f"1 se a dezena {k} saiu neste concurso."))
    clima_unit = {
        "temp_min": "°C", "temp_max": "°C", "temp_media": "°C", "temp_sorteio": "°C",
        "precip_media": "mm", "precip_sorteio": "mm",
        "wcode_sorteio": "código WMO", "wcode_dominante": "código WMO",
    }
    for c in CLIMA_COLS:
        cols.append(ColumnSpec(c, "float", clima_unit[c], "clima", "feature",
                               f"Clima ({c}) no dia/horário do sorteio. NaN se ausente."))
    lua_desc = {
        "phase": "Fase fracionária [0,1): 0=nova, 0.5=cheia.",
        "phase_sin": "sin(2π·phase) — codificação cíclica.",
        "phase_cos": "cos(2π·phase) — codificação cíclica.",
        "illumination": "Fração do disco iluminada [0,1].",
        "age_norm": "Dias desde a lua nova / 29.53 → [0,1].",
        "is_new": "1 se ±1.5d da lua nova.",
        "is_full": "1 se ±1.5d da lua cheia.",
    }
    for name in LUNAR_FEATURE_NAMES:
        cols.append(ColumnSpec(name, "float", "[0,1]", "lua", "feature", lua_desc[name]))
    for c in TEMPORAL_COLS:
        cols.append(ColumnSpec(c, "float", "[-1,1]", "temporal", "feature",
                               f"Codificação cíclica temporal ({c})."))
    cols.append(ColumnSpec("tem_clima", "int", "0/1", "cobertura", "cobertura", "1 se há dado de clima para o concurso."))
    cols.append(ColumnSpec("tem_lua", "int", "0/1", "cobertura", "cobertura", "1 se há dado de lua para a data."))
    return cols


CANONICAL_COLUMNS: List[ColumnSpec] = _build_canonical_columns()


def _load_raw_draws(data_dir: Optional[Path] = None) -> List[dict]:
    """Lê concurso_*.json incluindo dezenasOrdemSorteio e local. Ordena por concurso."""
    root = data_dir or DATA_DIR
    out: List[dict] = []
    for fp in Path(root).glob("concurso_*.json"):
        try:
            raw = json.loads(fp.read_text(encoding="utf-8"))
            dez = raw.get("dezenas", [])
            if not dez:
                continue
            out.append({
                "concurso": int(raw["concurso"]),
                "data": raw["data"],
                "local": raw.get("local"),
                "dezenas": sorted(int(d) for d in dez),
                "dezenas_ordem_sorteio": [int(d) for d in raw.get("dezenasOrdemSorteio", [])],
            })
        except (KeyError, ValueError, json.JSONDecodeError):
            continue
    out.sort(key=lambda r: r["concurso"])
    return out
