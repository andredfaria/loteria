# Dataset ML + Schema + Dicionário de Dados Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir um dataset ML tidy (uma linha por concurso) juntando sorteios + clima + lua, com schema/dicionário de dados auto-gerados, e treinar/avaliar honestamente um LightGBM que prevê quais 15 dezenas saem no próximo concurso.

**Architecture:** Um módulo `dataset_ml.py` define as colunas como fonte única de verdade (alimenta DataFrame, `schema.json` e o markdown do dicionário), monta a tabela canônica via left-join e deriva a matriz de modelagem long (por dezena) com alvo deslocado para `t+1` (sem vazamento). Um módulo `modelo_ordem_lgbm.py` treina o LightGBM com split temporal e reporta acertos@15 vs baseline aleatório. Dois scripts orquestram tudo.

**Tech Stack:** Python, pandas, numpy, LightGBM, scikit-learn (métricas), pytest. Reaproveita `climate_loader.load_all_climate`, `lunar_loader.compute_lunar_features` / `_parse_iso` / `LUNAR_FEATURE_NAMES`.

---

### Task 1: Dependência LightGBM + diretório de saída

**Files:**
- Modify: `pyproject.toml`
- Test: `src/lotofacil/experimentos/tests/test_dataset_ml.py`

- [ ] **Step 1: Adicionar lightgbm às dependências**

Em `pyproject.toml`, na lista `dependencies = [...]`, adicione (mantendo ordem alfabética se houver):

```toml
    "lightgbm>=4.0",
```

- [ ] **Step 2: Instalar**

Run: `source venv/bin/activate && pip install -e . && python -c "import lightgbm; print(lightgbm.__version__)"`
Expected: imprime a versão (ex.: `4.x.x`) sem erro.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build: adiciona lightgbm como dependência"
```

---

### Task 2: Definição de colunas (fonte única de verdade)

**Files:**
- Create: `src/lotofacil/experimentos/data/dataset_ml.py`
- Test: `src/lotofacil/experimentos/tests/test_dataset_ml.py`

- [ ] **Step 1: Escrever o teste falhando**

Crie `src/lotofacil/experimentos/tests/test_dataset_ml.py`:

```python
from lotofacil.experimentos.data import dataset_ml


def test_canonical_columns_cobrem_grupos_esperados():
    nomes = [c.name for c in dataset_ml.CANONICAL_COLUMNS]
    # meta
    assert {"concurso", "data", "local"} <= set(nomes)
    # alvo bruto
    assert "dezenas_ordem_sorteio" in nomes
    assert "primeira_dezena" in nomes
    # 25 colunas binárias do sorteio
    assert all(f"bola_{k:02d}" in nomes for k in range(1, 26))
    # clima (8) e lua (7)
    assert "temp_sorteio" in nomes and "wcode_dominante" in nomes
    assert "phase" in nomes and "is_full" in nomes
    # temporal e cobertura
    assert {"dow_sin", "dow_cos", "mes_sin", "mes_cos"} <= set(nomes)
    assert {"tem_clima", "tem_lua"} <= set(nomes)


def test_cada_coluna_tem_papel_valido():
    papeis = {c.role for c in dataset_ml.CANONICAL_COLUMNS}
    assert papeis <= {"meta", "feature", "alvo", "cobertura"}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest src/lotofacil/experimentos/tests/test_dataset_ml.py -v`
Expected: FAIL com `ModuleNotFoundError` / `AttributeError: CANONICAL_COLUMNS`.

- [ ] **Step 3: Implementar a definição de colunas**

Crie `src/lotofacil/experimentos/data/dataset_ml.py`:

```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest src/lotofacil/experimentos/tests/test_dataset_ml.py -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/experimentos/data/dataset_ml.py src/lotofacil/experimentos/tests/test_dataset_ml.py
git commit -m "feat(dataset_ml): definição canônica de colunas (fonte única de verdade)"
```

---

### Task 3: Loader de sorteios brutos (com dezenasOrdemSorteio)

**Files:**
- Modify: `src/lotofacil/experimentos/data/dataset_ml.py`
- Test: `src/lotofacil/experimentos/tests/test_dataset_ml.py`

- [ ] **Step 1: Escrever o teste falhando**

Adicione ao topo do arquivo de teste:

```python
import json as _json


def _escrever_concurso(tmp_path, concurso, data, dezenas, ordem):
    payload = {
        "concurso": concurso,
        "data": data,
        "local": "TESTE",
        "dezenas": [f"{d:02d}" for d in dezenas],
        "dezenasOrdemSorteio": [f"{d:02d}" for d in ordem],
    }
    (tmp_path / f"concurso_{concurso}.json").write_text(_json.dumps(payload), encoding="utf-8")
```

E o teste:

```python
def test_load_raw_draws_le_ordem_e_ordena(tmp_path):
    _escrever_concurso(tmp_path, 2, "06/10/2003", [1, 2, 3], [3, 1, 2])
    _escrever_concurso(tmp_path, 1, "29/09/2003", [5, 6, 7], [7, 6, 5])
    rows = dataset_ml._load_raw_draws(tmp_path)
    assert [r["concurso"] for r in rows] == [1, 2]          # ordenado asc
    assert rows[0]["dezenas"] == [5, 6, 7]                   # convertido p/ int e sorted
    assert rows[0]["dezenas_ordem_sorteio"] == [7, 6, 5]     # ordem preservada
    assert rows[0]["local"] == "TESTE"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest src/lotofacil/experimentos/tests/test_dataset_ml.py::test_load_raw_draws_le_ordem_e_ordena -v`
Expected: FAIL com `AttributeError: _load_raw_draws`.

- [ ] **Step 3: Implementar o loader**

Adicione em `dataset_ml.py`:

```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest src/lotofacil/experimentos/tests/test_dataset_ml.py::test_load_raw_draws_le_ordem_e_ordena -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/experimentos/data/dataset_ml.py src/lotofacil/experimentos/tests/test_dataset_ml.py
git commit -m "feat(dataset_ml): loader de sorteios brutos com ordem de sorteio"
```

---

### Task 4: Helpers de clima e temporal

**Files:**
- Modify: `src/lotofacil/experimentos/data/dataset_ml.py`
- Test: `src/lotofacil/experimentos/tests/test_dataset_ml.py`

- [ ] **Step 1: Escrever os testes falhando**

```python
import math as _math


def test_clima_fields_ausente_vira_nan():
    out = dataset_ml._clima_fields(None)
    assert set(out) == set(dataset_ml.CLIMA_COLS)
    assert all(_math.isnan(v) for v in out.values())


def test_clima_fields_mapeia_chaves_do_resumo():
    resumo = {"temp_sorteio": 20.8, "precipitacao_media": None,
              "weathercode_dominante": 3}
    out = dataset_ml._clima_fields(resumo)
    assert out["temp_sorteio"] == 20.8
    assert out["wcode_dominante"] == 3
    assert _math.isnan(out["precip_media"])     # None -> NaN


def test_temporal_fields_quarta_feira():
    # 2003-10-01 é quarta-feira (weekday=2)
    out = dataset_ml._temporal_fields("2003-10-01")
    assert abs(out["dow_sin"] - _math.sin(2 * _math.pi * 2 / 7)) < 1e-6
    assert set(out) == set(dataset_ml.TEMPORAL_COLS)


def test_temporal_fields_data_invalida_vira_nan():
    out = dataset_ml._temporal_fields("")
    assert all(_math.isnan(v) for v in out.values())
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest src/lotofacil/experimentos/tests/test_dataset_ml.py -k "clima_fields or temporal_fields" -v`
Expected: FAIL com `AttributeError`.

- [ ] **Step 3: Implementar os helpers**

Adicione em `dataset_ml.py`:

```python
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
    dt = datetime.strptime(data_iso, "%Y-%m-%d")
    dow = dt.weekday()
    month = dt.month - 1
    return {
        "dow_sin": math.sin(2 * math.pi * dow / 7),
        "dow_cos": math.cos(2 * math.pi * dow / 7),
        "mes_sin": math.sin(2 * math.pi * month / 12),
        "mes_cos": math.cos(2 * math.pi * month / 12),
    }
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest src/lotofacil/experimentos/tests/test_dataset_ml.py -k "clima_fields or temporal_fields" -v`
Expected: PASS (4 testes).

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/experimentos/data/dataset_ml.py src/lotofacil/experimentos/tests/test_dataset_ml.py
git commit -m "feat(dataset_ml): helpers de clima (raw + NaN) e temporal cíclico"
```

---

### Task 5: build_dataset() — a tabela canônica joinada

**Files:**
- Modify: `src/lotofacil/experimentos/data/dataset_ml.py`
- Test: `src/lotofacil/experimentos/tests/test_dataset_ml.py`

- [ ] **Step 1: Escrever o teste falhando**

```python
def test_build_dataset_uma_linha_por_concurso_e_binarios(tmp_path, monkeypatch):
    _escrever_concurso(tmp_path, 1, "29/09/2003", [2, 3, 5], [5, 3, 2])
    _escrever_concurso(tmp_path, 2, "06/10/2003", [1, 2, 4], [4, 2, 1])
    # Sem clima/lua reais nesse tmp: força ausência
    monkeypatch.setattr(dataset_ml, "load_all_climate", lambda: {})
    monkeypatch.setattr(dataset_ml, "compute_lunar_features",
                        lambda iso: __import__("numpy").zeros(len(dataset_ml.LUNAR_FEATURE_NAMES)))

    df = dataset_ml.build_dataset(tmp_path)
    assert len(df) == 2
    linha1 = df[df["concurso"] == 1].iloc[0]
    assert linha1["bola_02"] == 1 and linha1["bola_03"] == 1 and linha1["bola_05"] == 1
    assert linha1["bola_01"] == 0
    assert linha1["primeira_dezena"] == 5            # 1º da ordem
    assert linha1["tem_clima"] == 0                  # forçado ausente
    assert linha1["data"] == "2003-09-29"            # normalizado p/ ISO
    # todas as colunas canônicas presentes
    nomes = {c.name for c in dataset_ml.CANONICAL_COLUMNS}
    assert nomes <= set(df.columns)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest src/lotofacil/experimentos/tests/test_dataset_ml.py::test_build_dataset_uma_linha_por_concurso_e_binarios -v`
Expected: FAIL com `AttributeError: build_dataset`.

- [ ] **Step 3: Implementar build_dataset**

Adicione em `dataset_ml.py`:

```python
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
            rec["tem_lua"] = 1
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
    return pd.DataFrame.from_records(records)[col_order]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest src/lotofacil/experimentos/tests/test_dataset_ml.py::test_build_dataset_uma_linha_por_concurso_e_binarios -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/experimentos/data/dataset_ml.py src/lotofacil/experimentos/tests/test_dataset_ml.py
git commit -m "feat(dataset_ml): build_dataset com join sorteio+clima+lua+temporal"
```

---

### Task 6: to_training_matrix() — matriz long com alvo t+1 (sem vazamento)

**Files:**
- Modify: `src/lotofacil/experimentos/data/dataset_ml.py`
- Test: `src/lotofacil/experimentos/tests/test_dataset_ml.py`

- [ ] **Step 1: Escrever o teste falhando**

```python
def test_to_training_matrix_alvo_vem_do_proximo_concurso(tmp_path, monkeypatch):
    # concurso 1 sorteia {1,2,3}; concurso 2 sorteia {3,4,5}
    _escrever_concurso(tmp_path, 1, "29/09/2003", [1, 2, 3], [3, 2, 1])
    _escrever_concurso(tmp_path, 2, "06/10/2003", [3, 4, 5], [5, 4, 3])
    monkeypatch.setattr(dataset_ml, "load_all_climate", lambda: {})
    monkeypatch.setattr(dataset_ml, "compute_lunar_features",
                        lambda iso: __import__("numpy").zeros(len(dataset_ml.LUNAR_FEATURE_NAMES)))

    df = dataset_ml.build_dataset(tmp_path)
    long_df = dataset_ml.to_training_matrix(df)

    # Última linha (concurso 2, sem t+1) é descartada -> só concurso 1
    assert set(long_df["concurso"].unique()) == {1}
    # 25 números por concurso
    assert len(long_df) == 25
    # alvo = sorteio do concurso 2 ({3,4,5})
    alvo = set(long_df[long_df["saiu_no_proximo"] == 1]["numero"])
    assert alvo == {3, 4, 5}
    # saiu_no_anterior reflete o concurso 1 ({1,2,3})
    anterior = set(long_df[long_df["saiu_no_anterior"] == 1]["numero"])
    assert anterior == {1, 2, 3}


def test_sliding_freq_e_days_since():
    import numpy as np
    binary = np.array([[1, 0], [0, 0], [1, 1]], dtype=float)
    freq = dataset_ml._sliding_freq(binary, window=10)
    assert freq[0].tolist() == [0.0, 0.0]                 # 1ª linha sem histórico
    assert abs(freq[2][0] - 0.5) < 1e-6                   # nº0 saiu 1 de 2 linhas anteriores
    days = dataset_ml._days_since_last(binary)
    assert days[2][0] == 2                                # nº0 visto pela última vez na linha 0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest src/lotofacil/experimentos/tests/test_dataset_ml.py -k "training_matrix or sliding_freq" -v`
Expected: FAIL com `AttributeError`.

- [ ] **Step 3: Implementar a transformação long + helpers numéricos**

Adicione em `dataset_ml.py`:

```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest src/lotofacil/experimentos/tests/test_dataset_ml.py -k "training_matrix or sliding_freq" -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/experimentos/data/dataset_ml.py src/lotofacil/experimentos/tests/test_dataset_ml.py
git commit -m "feat(dataset_ml): matriz de treino long com alvo t+1 sem vazamento"
```

---

### Task 7: schema.json + dicionário de dados (markdown)

**Files:**
- Modify: `src/lotofacil/experimentos/data/dataset_ml.py`
- Test: `src/lotofacil/experimentos/tests/test_dataset_ml.py`

- [ ] **Step 1: Escrever o teste falhando**

```python
def test_write_schema_json_lista_todas_colunas(tmp_path):
    destino = tmp_path / "schema.json"
    dataset_ml.write_schema_json(destino)
    data = _json.loads(destino.read_text(encoding="utf-8"))
    nomes = {c["name"] for c in data["columns"]}
    assert nomes == {c.name for c in dataset_ml.CANONICAL_COLUMNS}
    assert all({"name", "dtype", "unit", "source", "role", "description"} <= set(c)
               for c in data["columns"])


def test_gerar_dicionario_md_contem_alvo(tmp_path):
    destino = tmp_path / "dic.md"
    dataset_ml.generate_data_dictionary_md(destino)
    texto = destino.read_text(encoding="utf-8")
    assert "dezenas_ordem_sorteio" in texto
    assert "| coluna |" in texto.lower() or "| Coluna |" in texto
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest src/lotofacil/experimentos/tests/test_dataset_ml.py -k "schema_json or dicionario_md" -v`
Expected: FAIL com `AttributeError`.

- [ ] **Step 3: Implementar geradores**

Adicione em `dataset_ml.py`:

```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest src/lotofacil/experimentos/tests/test_dataset_ml.py -k "schema_json or dicionario_md" -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/experimentos/data/dataset_ml.py src/lotofacil/experimentos/tests/test_dataset_ml.py
git commit -m "feat(dataset_ml): geradores de schema.json e dicionário de dados"
```

---

### Task 8: Modelo A — LightGBM com split temporal e avaliação honesta

**Files:**
- Create: `src/lotofacil/experimentos/models/modelo_ordem_lgbm.py`
- Test: `src/lotofacil/experimentos/tests/test_modelo_ordem.py`

- [ ] **Step 1: Escrever o teste falhando**

Crie `src/lotofacil/experimentos/tests/test_modelo_ordem.py`:

```python
import numpy as np
import pandas as pd

from lotofacil.experimentos.models import modelo_ordem_lgbm as mod


def _long_sintetico(n_concursos=40, seed=0):
    rng = np.random.default_rng(seed)
    recs = []
    for c in range(1, n_concursos + 1):
        ganhadores = set(rng.choice(range(1, 26), size=15, replace=False))
        for numero in range(1, 26):
            recs.append({
                "concurso": c,
                "numero": numero,
                "freq_10": rng.random(),
                "freq_30": rng.random(),
                "freq_100": rng.random(),
                "freq_all": rng.random(),
                "days_since_last": rng.random(),
                "saiu_no_anterior": int(rng.random() > 0.4),
                "saiu_no_proximo": 1 if numero in ganhadores else 0,
            })
    df = pd.DataFrame(recs)
    # Colunas clima/lua/temporal exigidas pelo FEATURE_COLS (preenche com 0)
    for col in mod.FEATURE_COLS:
        if col not in df.columns:
            df[col] = 0.0
    return df


def test_temporal_split_nao_vaza_concursos():
    df = _long_sintetico()
    train, test = mod.temporal_split(df, frac=0.75)
    assert train["concurso"].max() < test["concurso"].min()


def test_train_and_evaluate_retorna_metricas():
    df = _long_sintetico()
    train, test = mod.temporal_split(df, frac=0.75)
    model = mod.train_model(train)
    metrics = mod.evaluate(model, test)
    assert metrics["baseline_aleatorio"] == 9.0
    assert 0 <= metrics["acertos_medio"] <= 15
    assert metrics["n_concursos_teste"] > 0
    assert "logloss" in metrics and "auc" in metrics
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest src/lotofacil/experimentos/tests/test_modelo_ordem.py -v`
Expected: FAIL com `ModuleNotFoundError`.

- [ ] **Step 3: Implementar o modelo**

Crie `src/lotofacil/experimentos/models/modelo_ordem_lgbm.py`:

```python
"""Modelo A — LightGBM que prevê quais 15 dezenas saem no próximo concurso.

Treina sobre a matriz long (concurso × número) de dataset_ml.to_training_matrix.
Avaliação honesta: acertos@15 vs baseline aleatório (~9 esperados, hipergeométrico).
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

from lotofacil.experimentos.data.dataset_ml import (
    CLIMA_COLS, LUNAR_FEATURE_NAMES, TEMPORAL_COLS,
)

FEATURE_COLS = (
    ["numero", "freq_10", "freq_30", "freq_100", "freq_all",
     "days_since_last", "saiu_no_anterior"]
    + list(CLIMA_COLS) + list(LUNAR_FEATURE_NAMES) + list(TEMPORAL_COLS)
)
TARGET = "saiu_no_proximo"
BASELINE_ALEATORIO = 15 * 15 / 25  # = 9.0 (média hipergeométrica)


def temporal_split(long_df: pd.DataFrame, frac: float = 0.8) -> Tuple[pd.DataFrame, pd.DataFrame]:
    concursos = sorted(long_df["concurso"].unique())
    cut_idx = int(len(concursos) * frac)
    cut = concursos[cut_idx]
    train = long_df[long_df["concurso"] < cut].copy()
    test = long_df[long_df["concurso"] >= cut].copy()
    return train, test


def train_model(train_df: pd.DataFrame):
    import lightgbm as lgb
    X = train_df[FEATURE_COLS]
    y = train_df[TARGET]
    model = lgb.LGBMClassifier(
        n_estimators=200, learning_rate=0.05, num_leaves=31,
        random_state=42, n_jobs=-1, verbose=-1,
    )
    model.fit(X, y)
    return model


def evaluate(model, test_df: pd.DataFrame) -> dict:
    from sklearn.metrics import log_loss, roc_auc_score

    proba = model.predict_proba(test_df[FEATURE_COLS])[:, 1]
    test_df = test_df.assign(_proba=proba)

    hits = []
    for _, grp in test_df.groupby("concurso"):
        top15 = set(grp.sort_values("_proba", ascending=False).head(15)["numero"])
        actual = set(grp[grp[TARGET] == 1]["numero"])
        hits.append(len(top15 & actual))

    y_true = test_df[TARGET].to_numpy()
    metrics = {
        "acertos_medio": float(np.mean(hits)),
        "acertos_std": float(np.std(hits)),
        "baseline_aleatorio": BASELINE_ALEATORIO,
        "n_concursos_teste": len(hits),
        "auc": float(roc_auc_score(y_true, proba)) if len(set(y_true)) > 1 else float("nan"),
        "logloss": float(log_loss(y_true, proba, labels=[0, 1])),
    }
    return metrics
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest src/lotofacil/experimentos/tests/test_modelo_ordem.py -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/experimentos/models/modelo_ordem_lgbm.py src/lotofacil/experimentos/tests/test_modelo_ordem.py
git commit -m "feat(modelo_ordem): LightGBM com split temporal e avaliação honesta"
```

---

### Task 9: Script de build (dataset + schema + dicionário)

**Files:**
- Create: `scripts/build_ml_dataset.py`

- [ ] **Step 1: Implementar o script**

Crie `scripts/build_ml_dataset.py`:

```python
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
```

- [ ] **Step 2: Rodar o script de ponta a ponta**

Run: `source venv/bin/activate && python scripts/build_ml_dataset.py`
Expected: logs com nº de concursos/colunas, cobertura clima/lua, e arquivos criados em `saida/datasets/` + `docs/dicionario_dados_ml.md`.

- [ ] **Step 3: Verificar artefatos**

Run: `ls -la saida/datasets/ && head -20 docs/dicionario_dados_ml.md`
Expected: `lotofacil_ml.parquet`, `lotofacil_ml.csv`, `schema.json` presentes; markdown com a tabela de colunas.

- [ ] **Step 4: Commit**

```bash
git add scripts/build_ml_dataset.py docs/dicionario_dados_ml.md
git commit -m "feat(scripts): build do dataset ML + schema.json + dicionário de dados"
```

---

### Task 10: Script de treino + avaliação do Modelo A

**Files:**
- Create: `scripts/train_modelo_ordem.py`

- [ ] **Step 1: Implementar o script**

Crie `scripts/train_modelo_ordem.py`:

```python
"""Treina e avalia o Modelo A (LightGBM) com relatório honesto.

Uso:
    python scripts/train_modelo_ordem.py
"""

import logging

from lotofacil.experimentos.data import dataset_ml
from lotofacil.experimentos.models import modelo_ordem_lgbm as mod

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    log.info("Construindo dataset e matriz de treino...")
    df = dataset_ml.build_dataset()
    long_df = dataset_ml.to_training_matrix(df)
    train, test = mod.temporal_split(long_df, frac=0.8)
    log.info("Treino: %d concursos | Teste: %d concursos",
             train["concurso"].nunique(), test["concurso"].nunique())

    log.info("Treinando LightGBM...")
    model = mod.train_model(train)
    metrics = mod.evaluate(model, test)

    log.info("\n===== RELATÓRIO HONESTO =====")
    log.info("Acertos@15 médio : %.3f (±%.3f)", metrics["acertos_medio"], metrics["acertos_std"])
    log.info("Baseline aleatório: %.3f", metrics["baseline_aleatorio"])
    log.info("AUC               : %.4f", metrics["auc"])
    log.info("LogLoss           : %.4f", metrics["logloss"])
    delta = metrics["acertos_medio"] - metrics["baseline_aleatorio"]
    if abs(delta) < 0.3:
        log.info("Conclusão: empate estatístico com o acaso (esperado — a ordem do "
                 "sorteio é fisicamente aleatória).")
    elif delta > 0:
        log.info("Conclusão: +%.3f acima do acaso. Investigar antes de confiar "
                 "(pode ser ruído/overfit do split).", delta)
    else:
        log.info("Conclusão: abaixo do acaso (%.3f). Consistente com sinal ausente.", delta)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Rodar o treino**

Run: `source venv/bin/activate && python scripts/train_modelo_ordem.py`
Expected: relatório com acertos@15 médio próximo de ~9, AUC próximo de 0.5, e a conclusão de empate com o acaso.

- [ ] **Step 3: Commit**

```bash
git add scripts/train_modelo_ordem.py
git commit -m "feat(scripts): treino + avaliação honesta do Modelo A (LightGBM)"
```

---

### Task 11: Suíte completa verde

**Files:**
- (nenhum novo — verificação final)

- [ ] **Step 1: Rodar todos os testes do dataset e do modelo**

Run: `source venv/bin/activate && pytest src/lotofacil/experimentos/tests/test_dataset_ml.py src/lotofacil/experimentos/tests/test_modelo_ordem.py -v`
Expected: todos PASS.

- [ ] **Step 2: Rodar a suíte do projeto para garantir que nada quebrou**

Run: `pytest -q`
Expected: sem novas falhas introduzidas por esta mudança.

- [ ] **Step 3: Commit final (se houver ajustes pendentes)**

```bash
git add -A
git commit -m "test: garante suíte verde para dataset ML e modelo de ordem" || echo "nada a commitar"
```

---

## Notas de implementação

- **NaN em features:** LightGBM trata `NaN` nativamente — clima/lua ausentes não precisam de imputação.
- **Sem vazamento:** `to_training_matrix` descarta a última linha (sem `t+1`) e usa apenas clima/lua/temporal do concurso `t`.
- **Honestidade:** o relatório do Task 10 deve reportar empate com o acaso como o resultado correto, não como falha.
- **Reaproveitamento:** clima via `load_all_climate` (chave=concurso), lua via `compute_lunar_features` (chave=data ISO), data via `_parse_iso`.
