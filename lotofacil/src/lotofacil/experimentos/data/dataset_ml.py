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
        ColumnSpec("primeira_dezena", "int", "1-25 ou nulo", "sorteio", "feature", "Primeira bola sorteada (derivada da ordem); nulo se a ordem estiver ausente."),
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
        unit = "[-1,1]" if name in ("phase_sin", "phase_cos") else "[0,1]"
        cols.append(ColumnSpec(name, "float", unit, "lua", "feature", lua_desc[name]))
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


def _clima_fields(resumo: Optional[dict]) -> dict:
    if not resumo:
        return {c: float("nan") for c in CLIMA_COLS}
    out = {}
    for col, chave in CLIMA_COLS.items():
        val = resumo.get(chave)
        out[col] = float("nan") if val is None else val
    return out


def _temporal_fields(data_iso: str) -> dict:
    if not data_iso:
        return {c: float("nan") for c in TEMPORAL_COLS}
    try:
        dt = datetime.strptime(data_iso, "%Y-%m-%d")
    except ValueError:
        return {c: float("nan") for c in TEMPORAL_COLS}
    dow = dt.weekday()
    month = dt.month - 1
    return {
        "dow_sin": math.sin(2 * math.pi * dow / 7),
        "dow_cos": math.cos(2 * math.pi * dow / 7),
        "mes_sin": math.sin(2 * math.pi * month / 12),
        "mes_cos": math.cos(2 * math.pi * month / 12),
    }


def build_dataset(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Monta a tabela canônica: uma linha por concurso, join sorteio+clima+lua+temporal."""
    rows = _load_raw_draws(data_dir)
    climate_map = load_all_climate()
    records = []
    for r in rows:
        concurso = r["concurso"]
        dezenas = r["dezenas"]
        ordem = r["dezenas_ordem_sorteio"]
        data_iso = _parse_iso(r["data"])
        rec = {
            "concurso": concurso,
            "data": data_iso,
            "local": r["local"],
            "dezenas": json.dumps(dezenas),
            "dezenas_ordem_sorteio": json.dumps(ordem),
            "primeira_dezena": ordem[0] if ordem else None,
        }
        for n in range(1, 26):
            rec[f"bola_{n:02d}"] = 1 if n in dezenas else 0
        resumo = climate_map.get(concurso)
        rec["tem_clima"] = 1 if resumo else 0
        rec.update(_clima_fields(resumo))
        if data_iso:
            lua = compute_lunar_features(data_iso)
            # .any() guards against compute_lunar_features returning zeros when
            # data/pylunar is unavailable — zeros mean no actual lunar data.
            rec["tem_lua"] = 1 if lua.any() else 0
            for name, val in zip(LUNAR_FEATURE_NAMES, lua):
                rec[name] = float(val)
        else:
            rec["tem_lua"] = 0
            for name in LUNAR_FEATURE_NAMES:
                rec[name] = float("nan")
        rec.update(_temporal_fields(data_iso))
        records.append(rec)
    # Garante ordem de colunas canônica
    col_order = [c.name for c in CANONICAL_COLUMNS]
    if not records:
        return pd.DataFrame(columns=col_order)
    return pd.DataFrame.from_records(records)[col_order]


def _sliding_freq(binary: np.ndarray, window: int) -> np.ndarray:
    n = len(binary)
    freq = np.zeros_like(binary)
    for i in range(n):
        start = max(0, i - window)
        freq[i] = binary[start:i].mean(axis=0) if i > 0 else np.zeros(binary.shape[1])
    return freq


def _days_since_last(binary: np.ndarray) -> np.ndarray:
    n, m = binary.shape
    result = np.zeros((n, m))
    last_seen = np.full(m, -1, dtype=int)
    for i in range(n):
        for j in range(m):
            result[i, j] = i if last_seen[j] < 0 else i - last_seen[j]
            if binary[i, j] == 1:
                last_seen[j] = i
    return result


def to_training_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Converte a tabela canônica em formato long (concurso × número) com alvo t+1."""
    df = df.sort_values("concurso").reset_index(drop=True)
    n = len(df)
    bin_cols = [f"bola_{k:02d}" for k in range(1, 26)]
    bin_mat = df[bin_cols].to_numpy(dtype=float)

    freqs = {w: _sliding_freq(bin_mat, w) for w in FREQ_WINDOWS}
    freq_all = _sliding_freq(bin_mat, n)
    days_since_norm = np.clip(_days_since_last(bin_mat) / 50.0, 0.0, 1.0)

    extra_cols = list(CLIMA_COLS) + list(LUNAR_FEATURE_NAMES) + TEMPORAL_COLS
    records = []
    for i in range(n - 1):                       # descarta última (sem t+1)
        target_row = bin_mat[i + 1]
        base = {c: df.at[i, c] for c in extra_cols}
        concurso = int(df.at[i, "concurso"])
        for j in range(25):
            rec = {
                "concurso": concurso,
                "numero": j + 1,
                "freq_10": freqs[10][i, j],
                "freq_30": freqs[30][i, j],
                "freq_100": freqs[100][i, j],
                "freq_all": freq_all[i, j],
                "days_since_last": days_since_norm[i, j],
                "saiu_no_anterior": int(bin_mat[i, j]),
                **base,
                "saiu_no_proximo": int(target_row[j]),
            }
            records.append(rec)
    return pd.DataFrame.from_records(records)


def write_schema_json(path: Path) -> None:
    payload = {
        "dataset": "lotofacil_ml",
        "alvo_treino": "saiu_no_proximo (derivado de bola_* do concurso t+1)",
        "columns": [
            {"name": c.name, "dtype": c.dtype, "unit": c.unit,
             "source": c.source, "role": c.role, "description": c.description}
            for c in CANONICAL_COLUMNS
        ],
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_data_dictionary_md(path: Path) -> None:
    linhas = [
        "# Dicionário de Dados — Dataset ML Lotofácil",
        "",
        "Tabela canônica: uma linha por concurso. Alvo de treino derivado: "
        "`saiu_no_proximo` (sorteio do concurso `t+1`, ver `to_training_matrix`).",
        "",
        "| Coluna | Tipo | Unidade | Fonte | Papel | Descrição |",
        "|--------|------|---------|-------|-------|-----------|",
    ]
    for c in CANONICAL_COLUMNS:
        linhas.append(f"| `{c.name}` | {c.dtype} | {c.unit} | {c.source} | {c.role} | {c.description} |")
    linhas.append("")
    Path(path).write_text("\n".join(linhas), encoding="utf-8")
