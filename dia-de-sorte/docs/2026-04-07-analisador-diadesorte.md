# Analisador Dia de Sorte — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar `analisar_diadesorte.py` — script Python completo que analisa histórico de concursos do Dia de Sorte, calcula métricas estatísticas e sugere jogos configuráveis com razão para cada número.

**Architecture:** Arquivo único `analisar_diadesorte.py` com funções puras organizadas em seções (loader → métricas → estratégias → gerador → exibição → CLI). Testes em `tests/test_analise.py`. Sem classes, sem frameworks externos além de `pandas` opcional.

**Tech Stack:** Python 3.10+, `json`, `csv`, `random`, `argparse`, `collections` (stdlib). `pandas` para exportação CSV opcional.

---

## Estrutura de Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `analisar_diadesorte.py` | Todo o código de análise e CLI |
| `tests/__init__.py` | Marcador de pacote |
| `tests/test_analise.py` | Testes unitários de todas as funções |

### Estruturas de dados centrais

```python
# Concurso normalizado (saída do loader)
concurso = {
    "concurso": 100,
    "data": "15/01/2019",
    "numeros": [3, 4, 8, 15, 16, 20, 21],   # ints ordenados
    "mes_sorte": "Maio",
}

# Métricas (saída de calcular_metricas)
metricas = {
    "frequencia":     {1: 45, 2: 38, ..., 31: 50},   # número → total de aparições
    "atraso":         {1: 3,  2: 15, ..., 31: 0},    # número → concursos desde última aparição
    "paridade": {"media_pares": 3.2, "media_impares": 3.8},
    "faixa":    {"media_baixos": 3.5, "media_altos": 3.5},  # baixos = 1..15, altos = 16..31
    "frequencia_mes": {"Janeiro": 45, "Fevereiro": 30, ...},
    "total_concursos": 1197,
}

# Jogo gerado
jogo = {
    "numeros":  [3, 7, 12, 18, 24, 27, 31],
    "mes_sorte": "Maio",
    "razoes":   {3: "Atrasado há 12 concursos", 7: "3º mais frequente (156 aparições)", ...},
    "score":    82.4,   # 0-100
    "estrategia": "mista",
    "metricas_jogo": {"pares": 3, "impares": 4, "baixos": 3, "altos": 4},
}

# Config padrão
CONFIG_PADRAO = {
    "estrategia": "mista",      # frequentes | atrasados | mista | equilibrada
    "min_frequentes": 2,
    "max_frequentes": 4,
    "min_atrasados":  1,
    "max_atrasados":  3,
    "min_pares":      2,
    "max_pares":      5,
    "min_baixos":     2,
    "max_baixos":     5,
    "n_jogos":        1,
}
```

---

## Task 1: Scaffold + Data Loader

**Files:**
- Create: `analisar_diadesorte.py`
- Create: `tests/__init__.py`
- Create: `tests/test_analise.py`

- [ ] **Step 1.1: Criar `tests/__init__.py` vazio**

```bash
touch tests/__init__.py
```

- [ ] **Step 1.2: Escrever testes do loader**

Em `tests/test_analise.py`:

```python
import json
import os
import tempfile
import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from analisar_diadesorte import carregar_dados


def _fazer_json(tmp_dir, n, numeros, mes):
    data = {
        "concurso": n,
        "data": "01/01/2020",
        "dezenas": [str(x).zfill(2) for x in numeros],
        "mesSorte": mes,
    }
    path = os.path.join(tmp_dir, f"diadesorte_{n}.json")
    with open(path, "w") as f:
        json.dump(data, f)


def test_carregar_diretorio_retorna_lista_ordenada():
    with tempfile.TemporaryDirectory() as tmp:
        _fazer_json(tmp, 2, [5, 10, 15, 20, 25, 27, 30], "Março")
        _fazer_json(tmp, 1, [1, 2, 3, 4, 5, 6, 7], "Janeiro")
        historico = carregar_dados(tmp)

    assert len(historico) == 2
    assert historico[0]["concurso"] == 1
    assert historico[1]["concurso"] == 2


def test_normalizar_dezenas_para_ints():
    with tempfile.TemporaryDirectory() as tmp:
        _fazer_json(tmp, 1, [1, 2, 3, 4, 5, 6, 7], "Janeiro")
        historico = carregar_dados(tmp)

    assert historico[0]["numeros"] == [1, 2, 3, 4, 5, 6, 7]
    assert all(isinstance(n, int) for n in historico[0]["numeros"])


def test_normalizar_mes_sorte():
    with tempfile.TemporaryDirectory() as tmp:
        _fazer_json(tmp, 1, [1, 2, 3, 4, 5, 6, 7], "Outubro")
        historico = carregar_dados(tmp)

    assert historico[0]["mes_sorte"] == "Outubro"


def test_carregar_json_lista():
    raw = [
        {"concurso": 1, "data": "01/01/2020",
         "dezenas": ["01","02","03","04","05","06","07"], "mesSorte": "Janeiro"},
        {"concurso": 2, "data": "03/01/2020",
         "dezenas": ["08","09","10","11","12","13","14"], "mesSorte": "Fevereiro"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(raw, f)
        path = f.name
    try:
        historico = carregar_dados(path)
        assert len(historico) == 2
        assert historico[1]["numeros"] == [8, 9, 10, 11, 12, 13, 14]
    finally:
        os.unlink(path)


def test_erro_formato_desconhecido():
    with pytest.raises(ValueError):
        carregar_dados("arquivo.xlsx")
```

- [ ] **Step 1.3: Rodar para confirmar falha**

```bash
cd /home/andre/Projetos/pessoal/dia-de-sorte
python -m pytest tests/test_analise.py::test_carregar_diretorio_retorna_lista_ordenada -v
```

Saída esperada: `ImportError` ou `ModuleNotFoundError` (arquivo não existe ainda).

- [ ] **Step 1.4: Criar `analisar_diadesorte.py` com o loader**

```python
#!/usr/bin/env python3
"""
Analisador Dia de Sorte — análise estatística e sugestão de jogos.
Uso: python analisar_diadesorte.py --dados dados/ --estrategia mista --jogos 5
"""
import csv
import json
import os
import random
from collections import Counter

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
TODOS_NUMEROS = list(range(1, 32))           # 1..31
TODOS_MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
NUM_BAIXO_MAX = 15    # 1..15 = baixos, 16..31 = altos
TOTAL_DEZENAS = 7

CONFIG_PADRAO = {
    "estrategia": "mista",
    "min_frequentes": 2,
    "max_frequentes": 4,
    "min_atrasados":  1,
    "max_atrasados":  3,
    "min_pares":      2,
    "max_pares":      5,
    "min_baixos":     2,
    "max_baixos":     5,
    "n_jogos":        1,
}

# ---------------------------------------------------------------------------
# Seção 1 — Carregamento de dados
# ---------------------------------------------------------------------------

def carregar_dados(caminho: str) -> list[dict]:
    """
    Carrega histórico de concursos.
    Aceita:
      - diretório com arquivos diadesorte_N.json
      - arquivo .json com lista de concursos
      - arquivo .csv com colunas: concurso,data,n1..n7,mes_sorte
    Retorna lista de concursos normalizados, ordenados por número.
    """
    if os.path.isdir(caminho):
        return _carregar_diretorio(caminho)
    if caminho.endswith(".json"):
        return _carregar_json_arquivo(caminho)
    if caminho.endswith(".csv"):
        return _carregar_csv(caminho)
    raise ValueError(f"Formato não suportado: {caminho!r}. Use diretório, .json ou .csv.")


def _carregar_diretorio(caminho: str) -> list[dict]:
    historico = []
    for nome in sorted(os.listdir(caminho)):
        if not nome.endswith(".json"):
            continue
        filepath = os.path.join(caminho, nome)
        with open(filepath, encoding="utf-8") as f:
            raw = json.load(f)
        historico.append(_normalizar_json(raw))
    historico.sort(key=lambda x: x["concurso"])
    return historico


def _carregar_json_arquivo(caminho: str) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        raw = json.load(f)
    registros = raw if isinstance(raw, list) else [raw]
    historico = [_normalizar_json(r) for r in registros]
    historico.sort(key=lambda x: x["concurso"])
    return historico


def _carregar_csv(caminho: str) -> list[dict]:
    historico = []
    with open(caminho, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            numeros = sorted(int(row[f"n{i}"]) for i in range(1, 8))
            historico.append({
                "concurso": int(row["concurso"]),
                "data":     row.get("data", ""),
                "numeros":  numeros,
                "mes_sorte": row.get("mes_sorte", ""),
            })
    historico.sort(key=lambda x: x["concurso"])
    return historico


def _normalizar_json(raw: dict) -> dict:
    return {
        "concurso":  int(raw["concurso"]),
        "data":      raw.get("data", ""),
        "numeros":   sorted(int(d) for d in raw["dezenas"]),
        "mes_sorte": raw.get("mesSorte", raw.get("mes_sorte", "")),
    }
```

- [ ] **Step 1.5: Rodar testes do loader**

```bash
python -m pytest tests/test_analise.py -k "carregar" -v
```

Saída esperada: todos os 5 testes PASS.

- [ ] **Step 1.6: Commit**

```bash
git add analisar_diadesorte.py tests/__init__.py tests/test_analise.py
git commit -m "feat: add data loader for diadesorte JSON/CSV/directory"
```

---

## Task 2: Cálculo de Métricas

**Files:**
- Modify: `analisar_diadesorte.py` (adicionar Seção 2)
- Modify: `tests/test_analise.py` (adicionar testes de métricas)

- [ ] **Step 2.1: Escrever testes de métricas**

Adicionar em `tests/test_analise.py`:

```python
from analisar_diadesorte import (
    calc_frequencia, calc_atraso,
    calc_distribuicao_paridade, calc_distribuicao_faixa,
    calc_frequencia_mes, calcular_metricas,
)

HISTORICO_FIXO = [
    {"concurso": 1, "data": "01/01/2019", "numeros": [1, 2, 3, 4, 5, 6, 7],  "mes_sorte": "Janeiro"},
    {"concurso": 2, "data": "03/01/2019", "numeros": [1, 2, 3, 4, 5, 6, 8],  "mes_sorte": "Março"},
    {"concurso": 3, "data": "05/01/2019", "numeros": [1, 2, 3, 4, 5, 6, 9],  "mes_sorte": "Março"},
]


def test_frequencia_conta_aparicoes():
    freq = calc_frequencia(HISTORICO_FIXO)
    assert freq[1] == 3   # aparece nos 3 concursos
    assert freq[7] == 1   # só no concurso 1
    assert freq[8] == 1   # só no concurso 2
    assert freq[9] == 1   # só no concurso 3
    assert freq[31] == 0  # nunca apareceu


def test_atraso_numero_nunca_visto():
    atraso = calc_atraso(HISTORICO_FIXO)
    assert atraso[31] == 3   # nunca visto, atraso = total concursos


def test_atraso_numero_mais_recente():
    atraso = calc_atraso(HISTORICO_FIXO)
    assert atraso[9] == 0   # visto no último concurso (3)


def test_atraso_numero_intermediario():
    atraso = calc_atraso(HISTORICO_FIXO)
    assert atraso[7] == 2   # visto no concurso 1, atual=3, delay=2


def test_paridade_media():
    par = calc_distribuicao_paridade(HISTORICO_FIXO)
    # concurso 1: pares = [2,4,6] = 3; concurso 2: [2,4,6,8] = 4; concurso 3: [2,4,6] = 3
    assert abs(par["media_pares"] - (3 + 4 + 3) / 3) < 0.01
    assert abs(par["media_impares"] - (4 + 3 + 4) / 3) < 0.01


def test_faixa_media():
    faixa = calc_distribuicao_faixa(HISTORICO_FIXO)
    # todos os números são <=15, então baixos = 7 por jogo
    assert abs(faixa["media_baixos"] - 7.0) < 0.01
    assert abs(faixa["media_altos"] - 0.0) < 0.01


def test_frequencia_mes():
    freq_mes = calc_frequencia_mes(HISTORICO_FIXO)
    assert freq_mes["Janeiro"] == 1
    assert freq_mes["Março"] == 2
    assert freq_mes["Fevereiro"] == 0


def test_calcular_metricas_retorna_todas_chaves():
    m = calcular_metricas(HISTORICO_FIXO)
    assert "frequencia" in m
    assert "atraso" in m
    assert "paridade" in m
    assert "faixa" in m
    assert "frequencia_mes" in m
    assert m["total_concursos"] == 3
```

- [ ] **Step 2.2: Rodar para confirmar falha**

```bash
python -m pytest tests/test_analise.py -k "frequencia or atraso or paridade or faixa or metricas" -v
```

Saída esperada: `ImportError` (funções ainda não existem).

- [ ] **Step 2.3: Implementar funções de métricas em `analisar_diadesorte.py`**

Adicionar após Seção 1:

```python
# ---------------------------------------------------------------------------
# Seção 2 — Cálculo de métricas
# ---------------------------------------------------------------------------

def calc_frequencia(historico: list[dict]) -> dict[int, int]:
    """Conta quantas vezes cada número (1-31) apareceu no histórico."""
    freq = {n: 0 for n in TODOS_NUMEROS}
    for concurso in historico:
        for n in concurso["numeros"]:
            freq[n] += 1
    return freq


def calc_atraso(historico: list[dict]) -> dict[int, int]:
    """
    Retorna, para cada número, quantos concursos se passaram desde a última aparição.
    Números que nunca apareceram recebem atraso = total de concursos.
    """
    ultimo_visto = {n: 0 for n in TODOS_NUMEROS}
    for concurso in historico:
        for n in concurso["numeros"]:
            ultimo_visto[n] = concurso["concurso"]
    ultimo_id = historico[-1]["concurso"]
    return {n: ultimo_id - ultimo_visto[n] for n in TODOS_NUMEROS}


def calc_distribuicao_paridade(historico: list[dict]) -> dict:
    """Calcula média histórica de pares e ímpares por concurso."""
    pares_por_jogo = [
        sum(1 for n in c["numeros"] if n % 2 == 0)
        for c in historico
    ]
    media_pares = sum(pares_por_jogo) / len(historico)
    return {
        "media_pares":   media_pares,
        "media_impares": TOTAL_DEZENAS - media_pares,
    }


def calc_distribuicao_faixa(historico: list[dict]) -> dict:
    """Calcula média histórica de números baixos (1-15) e altos (16-31) por concurso."""
    baixos_por_jogo = [
        sum(1 for n in c["numeros"] if n <= NUM_BAIXO_MAX)
        for c in historico
    ]
    media_baixos = sum(baixos_por_jogo) / len(historico)
    return {
        "media_baixos": media_baixos,
        "media_altos":  TOTAL_DEZENAS - media_baixos,
    }


def calc_frequencia_mes(historico: list[dict]) -> dict[str, int]:
    """Conta quantas vezes cada mês da sorte foi sorteado."""
    freq = {m: 0 for m in TODOS_MESES}
    for c in historico:
        mes = c.get("mes_sorte", "")
        if mes in freq:
            freq[mes] += 1
    return freq


def calcular_metricas(historico: list[dict]) -> dict:
    """Agrega todas as métricas em um único dicionário."""
    return {
        "frequencia":     calc_frequencia(historico),
        "atraso":         calc_atraso(historico),
        "paridade":       calc_distribuicao_paridade(historico),
        "faixa":          calc_distribuicao_faixa(historico),
        "frequencia_mes": calc_frequencia_mes(historico),
        "total_concursos": len(historico),
    }
```

- [ ] **Step 2.4: Rodar testes de métricas**

```bash
python -m pytest tests/test_analise.py -k "frequencia or atraso or paridade or faixa or metricas" -v
```

Saída esperada: todos os 9 testes PASS.

- [ ] **Step 2.5: Commit**

```bash
git add analisar_diadesorte.py tests/test_analise.py
git commit -m "feat: add metrics calculation (frequency, delay, parity, range, lucky month)"
```

---

## Task 3: Estratégias + Gerador de Jogo

**Files:**
- Modify: `analisar_diadesorte.py` (adicionar Seções 3 e 4)
- Modify: `tests/test_analise.py` (adicionar testes de geração)

- [ ] **Step 3.1: Escrever testes de geração**

Adicionar em `tests/test_analise.py`:

```python
from analisar_diadesorte import gerar_jogo, TODOS_MESES, TODOS_NUMEROS, calcular_metricas

HISTORICO_GRANDE = [
    {
        "concurso": i,
        "data": "01/01/2020",
        "numeros": sorted(random.sample(range(1, 32), 7)),
        "mes_sorte": TODOS_MESES[i % 12],
    }
    for i in range(1, 101)
]


def test_jogo_tem_7_numeros():
    import random as _r; _r.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogo = gerar_jogo(m, CONFIG_PADRAO)
    assert len(jogo["numeros"]) == 7


def test_jogo_numeros_dentro_do_intervalo():
    import random as _r; _r.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogo = gerar_jogo(m, CONFIG_PADRAO)
    assert all(1 <= n <= 31 for n in jogo["numeros"])


def test_jogo_numeros_sem_repeticao():
    import random as _r; _r.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogo = gerar_jogo(m, CONFIG_PADRAO)
    assert len(set(jogo["numeros"])) == 7


def test_jogo_mes_sorte_valido():
    import random as _r; _r.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogo = gerar_jogo(m, CONFIG_PADRAO)
    assert jogo["mes_sorte"] in TODOS_MESES


def test_jogo_tem_razoes_para_cada_numero():
    import random as _r; _r.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogo = gerar_jogo(m, CONFIG_PADRAO)
    for n in jogo["numeros"]:
        assert n in jogo["razoes"]
        assert isinstance(jogo["razoes"][n], str)
        assert len(jogo["razoes"][n]) > 0


def test_jogo_score_entre_0_e_100():
    import random as _r; _r.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogo = gerar_jogo(m, CONFIG_PADRAO)
    assert 0 <= jogo["score"] <= 100


def test_todas_estrategias_geram_jogo_valido():
    import random as _r; _r.seed(42)
    m = calcular_metricas(HISTORICO_GRANDE)
    for estrategia in ["frequentes", "atrasados", "mista", "equilibrada"]:
        cfg = {**CONFIG_PADRAO, "estrategia": estrategia}
        jogo = gerar_jogo(m, cfg)
        assert len(jogo["numeros"]) == 7
        assert all(1 <= n <= 31 for n in jogo["numeros"])
        assert jogo["mes_sorte"] in TODOS_MESES
```

Adicionar `import random` no topo do arquivo de teste.

- [ ] **Step 3.2: Rodar para confirmar falha**

```bash
python -m pytest tests/test_analise.py -k "jogo or estrategia" -v
```

Saída esperada: `ImportError` (funções ainda não existem).

- [ ] **Step 3.3: Implementar estratégias e gerador em `analisar_diadesorte.py`**

Adicionar após Seção 2:

```python
# ---------------------------------------------------------------------------
# Seção 3 — Estratégias de seleção
# ---------------------------------------------------------------------------

def _rankear(valores: dict[int, int | float], reverso: bool = True) -> dict[int, int]:
    """Retorna {número: rank} onde rank=1 é o melhor. Empates recebem o mesmo rank."""
    ordenado = sorted(TODOS_NUMEROS, key=lambda n: valores[n], reverse=reverso)
    return {n: i + 1 for i, n in enumerate(ordenado)}


def _normalizar_pesos(valores: dict[int, float]) -> list[float]:
    """Transforma valores em pesos normalizados (soma=1) preservando a ordem de TODOS_NUMEROS."""
    total = sum(values := [max(valores[n], 0.001) for n in TODOS_NUMEROS])
    return [v / total for v in values]


def _amostrar_sem_repeticao(pesos: list[float], k: int) -> list[int]:
    """Seleciona k números de TODOS_NUMEROS sem repetição usando pesos proporcionais."""
    pool = list(TODOS_NUMEROS)
    pesos_mut = list(pesos)
    escolhidos = []
    for _ in range(k):
        idx = random.choices(range(len(pool)), weights=pesos_mut)[0]
        escolhidos.append(pool[idx])
        pool.pop(idx)
        pesos_mut.pop(idx)
    return escolhidos


def _selecionar_frequentes(metricas: dict, n: int = TOTAL_DEZENAS) -> tuple[list[int], dict]:
    freq = metricas["frequencia"]
    rank = _rankear(freq, reverso=True)   # rank 1 = mais frequente
    pesos = _normalizar_pesos({num: 1 / rank[num] for num in TODOS_NUMEROS})
    escolhidos = _amostrar_sem_repeticao(pesos, n)
    razoes = {
        num: f"Frequente: {freq[num]}x no histórico (rank #{rank[num]})"
        for num in escolhidos
    }
    return escolhidos, razoes


def _selecionar_atrasados(metricas: dict, n: int = TOTAL_DEZENAS) -> tuple[list[int], dict]:
    atraso = metricas["atraso"]
    rank = _rankear(atraso, reverso=True)   # rank 1 = mais atrasado
    pesos = _normalizar_pesos({num: 1 / rank[num] for num in TODOS_NUMEROS})
    escolhidos = _amostrar_sem_repeticao(pesos, n)
    razoes = {
        num: f"Atrasado: {atraso[num]} concursos sem aparecer (rank #{rank[num]})"
        for num in escolhidos
    }
    return escolhidos, razoes


def _selecionar_mista(metricas: dict, config: dict) -> tuple[list[int], dict]:
    """
    Mistura números frequentes e atrasados conforme limites do config.
    Preenche o restante com seleção ponderada pelo score combinado.
    """
    freq   = metricas["frequencia"]
    atraso = metricas["atraso"]
    rank_f = _rankear(freq,   reverso=True)
    rank_a = _rankear(atraso, reverso=True)

    n_freq    = random.randint(config["min_frequentes"], config["max_frequentes"])
    n_atraso  = random.randint(config["min_atrasados"],  config["max_atrasados"])
    n_freq    = min(n_freq, TOTAL_DEZENAS)
    n_atraso  = min(n_atraso, TOTAL_DEZENAS - n_freq)
    n_resto   = TOTAL_DEZENAS - n_freq - n_atraso

    # Pega os top-n de cada categoria sem sobreposição
    top_freq   = sorted(TODOS_NUMEROS, key=lambda n: rank_f[n])
    top_atraso = sorted(TODOS_NUMEROS, key=lambda n: rank_a[n])

    escolhidos_f = []
    for n in top_freq:
        if len(escolhidos_f) == n_freq:
            break
        escolhidos_f.append(n)

    escolhidos_a = []
    usados = set(escolhidos_f)
    for n in top_atraso:
        if len(escolhidos_a) == n_atraso:
            break
        if n not in usados:
            escolhidos_a.append(n)
            usados.add(n)

    # Resto: score combinado (50% freq + 50% atraso)
    disponiveis = [n for n in TODOS_NUMEROS if n not in usados]
    pesos_resto = _normalizar_pesos({
        n: (1 / rank_f[n] + 1 / rank_a[n]) for n in disponiveis
    })
    # Remapear para TODOS_NUMEROS na ordem de disponiveis
    pool = disponiveis
    pw   = pesos_resto
    escolhidos_r = []
    for _ in range(n_resto):
        if not pool:
            break
        idx = random.choices(range(len(pool)), weights=pw)[0]
        escolhidos_r.append(pool[idx])
        pool.pop(idx)
        pw.pop(idx)

    razoes = {}
    for n in escolhidos_f:
        razoes[n] = f"Frequente: {freq[n]}x (rank #{rank_f[n]})"
    for n in escolhidos_a:
        razoes[n] = f"Atrasado: {atraso[n]} concursos (rank #{rank_a[n]})"
    for n in escolhidos_r:
        razoes[n] = f"Complementar: freq={freq[n]}, atraso={atraso[n]}"

    return escolhidos_f + escolhidos_a + escolhidos_r, razoes


def _selecionar_equilibrada(metricas: dict, config: dict) -> tuple[list[int], dict]:
    """
    Seleciona com restrições de paridade e faixa usando rejection sampling.
    Score por número = 0.5*normalized_freq + 0.5*normalized_atraso.
    """
    freq   = metricas["frequencia"]
    atraso = metricas["atraso"]
    rank_f = _rankear(freq,   reverso=True)
    rank_a = _rankear(atraso, reverso=True)

    pesos_base = _normalizar_pesos({
        n: (1 / rank_f[n] + 1 / rank_a[n]) for n in TODOS_NUMEROS
    })

    min_pares  = config.get("min_pares",  2)
    max_pares  = config.get("max_pares",  5)
    min_baixos = config.get("min_baixos", 2)
    max_baixos = config.get("max_baixos", 5)

    for _ in range(2000):   # rejection sampling com limite
        candidatos = _amostrar_sem_repeticao(pesos_base, TOTAL_DEZENAS)
        pares  = sum(1 for n in candidatos if n % 2 == 0)
        baixos = sum(1 for n in candidatos if n <= NUM_BAIXO_MAX)
        if min_pares <= pares <= max_pares and min_baixos <= baixos <= max_baixos:
            razoes = {
                n: (
                    f"Equilibrado: freq={freq[n]} (#{rank_f[n]}), "
                    f"atraso={atraso[n]} (#{rank_a[n]}), "
                    f"{'par' if n % 2 == 0 else 'ímpar'}, "
                    f"{'baixo' if n <= NUM_BAIXO_MAX else 'alto'}"
                )
                for n in candidatos
            }
            return candidatos, razoes

    # Fallback: top-7 por score combinado sem restrição
    top7 = sorted(TODOS_NUMEROS, key=lambda n: (1 / rank_f[n] + 1 / rank_a[n]), reverse=True)[:7]
    razoes = {n: f"Fallback equilibrado: freq={freq[n]}, atraso={atraso[n]}" for n in top7}
    return top7, razoes


def _selecionar_mes(metricas: dict) -> str:
    """Escolhe mês da sorte com probabilidade proporcional à frequência histórica."""
    freq_mes = metricas["frequencia_mes"]
    total    = sum(freq_mes.values())
    if total == 0:
        return random.choice(TODOS_MESES)
    pesos = [freq_mes[m] / total for m in TODOS_MESES]
    return random.choices(TODOS_MESES, weights=pesos)[0]


# ---------------------------------------------------------------------------
# Seção 4 — Gerador de jogo + pontuação
# ---------------------------------------------------------------------------

def _calcular_score(numeros: list[int], mes_sorte: str, metricas: dict, config: dict) -> float:
    """
    Retorna score 0-100 para o jogo com base em:
      30% — equilíbrio de paridade (quão próximo de 3-4)
      30% — equilíbrio de faixa (quão próximo de 3-4)
      20% — rank médio de frequência dos números escolhidos
      20% — rank médio de atraso dos números escolhidos
    """
    freq   = metricas["frequencia"]
    atraso = metricas["atraso"]
    rank_f = _rankear(freq,   reverso=True)
    rank_a = _rankear(atraso, reverso=True)

    pares  = sum(1 for n in numeros if n % 2 == 0)
    baixos = sum(1 for n in numeros if n <= NUM_BAIXO_MAX)

    # Pontuação de paridade: máx quando pares=3 ou pares=4
    ideal_pares = 3.5
    score_paridade = max(0.0, 100 - abs(pares - ideal_pares) * 25)

    # Pontuação de faixa: máx quando baixos=3 ou baixos=4
    ideal_baixos = 3.5
    score_faixa = max(0.0, 100 - abs(baixos - ideal_baixos) * 25)

    # Pontuação de frequência: rank médio normalizado (rank 1 → 100, rank 31 → ~0)
    score_freq = sum((31 - rank_f[n]) / 30 * 100 for n in numeros) / len(numeros)

    # Pontuação de atraso: rank médio normalizado
    score_atraso = sum((31 - rank_a[n]) / 30 * 100 for n in numeros) / len(numeros)

    score = (
        score_paridade * 0.30 +
        score_faixa    * 0.30 +
        score_freq     * 0.20 +
        score_atraso   * 0.20
    )
    return round(score, 2)


def gerar_jogo(metricas: dict, config: dict) -> dict:
    """
    Gera um jogo com 7 números e 1 mês da sorte conforme a estratégia e config.
    Retorna dict com: numeros, mes_sorte, razoes, score, estrategia, metricas_jogo.
    """
    estrategia = config.get("estrategia", "mista")

    if estrategia == "frequentes":
        numeros, razoes = _selecionar_frequentes(metricas)
    elif estrategia == "atrasados":
        numeros, razoes = _selecionar_atrasados(metricas)
    elif estrategia == "mista":
        numeros, razoes = _selecionar_mista(metricas, config)
    elif estrategia == "equilibrada":
        numeros, razoes = _selecionar_equilibrada(metricas, config)
    else:
        raise ValueError(f"Estratégia desconhecida: {estrategia!r}")

    numeros = sorted(numeros)
    mes_sorte = _selecionar_mes(metricas)
    score = _calcular_score(numeros, mes_sorte, metricas, config)

    return {
        "numeros":   numeros,
        "mes_sorte": mes_sorte,
        "razoes":    razoes,
        "score":     score,
        "estrategia": estrategia,
        "metricas_jogo": {
            "pares":   sum(1 for n in numeros if n % 2 == 0),
            "impares": sum(1 for n in numeros if n % 2 != 0),
            "baixos":  sum(1 for n in numeros if n <= NUM_BAIXO_MAX),
            "altos":   sum(1 for n in numeros if n > NUM_BAIXO_MAX),
        },
    }
```

- [ ] **Step 3.4: Rodar testes de geração**

```bash
python -m pytest tests/test_analise.py -k "jogo or estrategia" -v
```

Saída esperada: todos os 7 testes PASS.

- [ ] **Step 3.5: Commit**

```bash
git add analisar_diadesorte.py tests/test_analise.py
git commit -m "feat: add strategy selectors and game generator with scoring"
```

---

## Task 4: Ranker + Display + CLI

**Files:**
- Modify: `analisar_diadesorte.py` (adicionar Seções 5, 6, 7)
- Modify: `tests/test_analise.py` (adicionar testes de ranker)

- [ ] **Step 4.1: Escrever testes do ranker**

Adicionar em `tests/test_analise.py`:

```python
from analisar_diadesorte import gerar_e_ranquear


def test_ranquear_retorna_n_jogos():
    import random as _r; _r.seed(99)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogos = gerar_e_ranquear(m, CONFIG_PADRAO, n_jogos=5)
    assert len(jogos) == 5


def test_ranquear_ordenado_por_score_desc():
    import random as _r; _r.seed(99)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogos = gerar_e_ranquear(m, CONFIG_PADRAO, n_jogos=10)
    scores = [j["score"] for j in jogos]
    assert scores == sorted(scores, reverse=True)


def test_ranquear_todos_jogos_validos():
    import random as _r; _r.seed(99)
    m = calcular_metricas(HISTORICO_GRANDE)
    jogos = gerar_e_ranquear(m, CONFIG_PADRAO, n_jogos=5)
    for jogo in jogos:
        assert len(jogo["numeros"]) == 7
        assert all(1 <= n <= 31 for n in jogo["numeros"])
        assert jogo["mes_sorte"] in TODOS_MESES
```

- [ ] **Step 4.2: Rodar para confirmar falha**

```bash
python -m pytest tests/test_analise.py -k "ranquear" -v
```

Saída esperada: `ImportError`.

- [ ] **Step 4.3: Implementar ranker, display e CLI em `analisar_diadesorte.py`**

Adicionar após Seção 4:

```python
# ---------------------------------------------------------------------------
# Seção 5 — Ranqueador de múltiplos jogos
# ---------------------------------------------------------------------------

def gerar_e_ranquear(metricas: dict, config: dict, n_jogos: int = 10) -> list[dict]:
    """
    Gera n_jogos candidatos e os ordena por score decrescente.
    Cada jogo tem campos extras: 'posicao' (1-based rank).
    """
    jogos = [gerar_jogo(metricas, config) for _ in range(n_jogos)]
    jogos.sort(key=lambda j: j["score"], reverse=True)
    for i, jogo in enumerate(jogos, start=1):
        jogo["posicao"] = i
    return jogos


# ---------------------------------------------------------------------------
# Seção 6 — Funções de exibição
# ---------------------------------------------------------------------------

def exibir_metricas(metricas: dict) -> None:
    """Imprime resumo das métricas no terminal."""
    total = metricas["total_concursos"]
    freq  = metricas["frequencia"]
    atraso = metricas["atraso"]
    par   = metricas["paridade"]
    faixa = metricas["faixa"]
    freq_mes = metricas["frequencia_mes"]

    print("\n" + "=" * 60)
    print(f"  MÉTRICAS — Dia de Sorte ({total} concursos analisados)")
    print("=" * 60)

    print("\n[Frequência — Top 10 mais sorteados]")
    top10_freq = sorted(TODOS_NUMEROS, key=lambda n: freq[n], reverse=True)[:10]
    for n in top10_freq:
        barra = "█" * int(freq[n] / total * 200)
        print(f"  {n:02d}: {freq[n]:4d}x  {barra}")

    print("\n[Atraso — Top 10 mais ausentes]")
    top10_atraso = sorted(TODOS_NUMEROS, key=lambda n: atraso[n], reverse=True)[:10]
    for n in top10_atraso:
        print(f"  {n:02d}: {atraso[n]:4d} concursos sem aparecer")

    print(f"\n[Paridade histórica]")
    print(f"  Média de pares por jogo:   {par['media_pares']:.2f}")
    print(f"  Média de ímpares por jogo: {par['media_impares']:.2f}")

    print(f"\n[Faixa histórica]")
    print(f"  Média de baixos (1-15):  {faixa['media_baixos']:.2f}")
    print(f"  Média de altos  (16-31): {faixa['media_altos']:.2f}")

    print(f"\n[Mês da Sorte — frequência]")
    for mes in TODOS_MESES:
        pct = freq_mes[mes] / total * 100 if total else 0
        barra = "█" * int(pct / 2)
        print(f"  {mes:<11}: {freq_mes[mes]:4d}x ({pct:5.1f}%)  {barra}")

    print()


def exibir_jogo(jogo: dict, posicao: int | None = None) -> None:
    """Imprime o jogo sugerido com razões e métricas."""
    titulo = f"  JOGO SUGERIDO" if posicao is None else f"  JOGO #{posicao}"
    print("\n" + "=" * 60)
    print(titulo + f"  [estratégia: {jogo['estrategia']}]  score: {jogo['score']:.1f}/100")
    print("=" * 60)

    print(f"\n  Números: {' '.join(f'{n:02d}' for n in jogo['numeros'])}")
    print(f"  Mês da Sorte: {jogo['mes_sorte']}")

    mj = jogo["metricas_jogo"]
    print(f"\n  Composição: {mj['pares']} par(es) / {mj['impares']} ímpar(es)  |  "
          f"{mj['baixos']} baixo(s) / {mj['altos']} alto(s)")

    print("\n  Razão de cada número:")
    for n in jogo["numeros"]:
        razao = jogo["razoes"].get(n, "—")
        print(f"    {n:02d} → {razao}")

    print()


def exibir_ranking(jogos: list[dict]) -> None:
    """Imprime lista ranqueada de jogos."""
    print("\n" + "=" * 60)
    print(f"  RANKING DE {len(jogos)} JOGOS GERADOS")
    print("=" * 60)
    for jogo in jogos:
        nums = " ".join(f"{n:02d}" for n in jogo["numeros"])
        print(f"  #{jogo['posicao']:2d}  score={jogo['score']:5.1f}  "
              f"nums=[{nums}]  mês={jogo['mes_sorte']}")
    print()


# ---------------------------------------------------------------------------
# Seção 7 — CLI principal
# ---------------------------------------------------------------------------

def _parse_args():
    import argparse
    p = argparse.ArgumentParser(
        description="Analisador Dia de Sorte — sugere jogos com base em estatísticas históricas.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        "--dados", default="dados",
        help="Diretório com JSONs, arquivo .json ou .csv (padrão: dados/)",
    )
    p.add_argument(
        "--estrategia", default="mista",
        choices=["frequentes", "atrasados", "mista", "equilibrada"],
        help=(
            "Estratégia de seleção:\n"
            "  frequentes  — números que mais apareceram\n"
            "  atrasados   — números que estão ausentes há mais tempo\n"
            "  mista       — combina frequentes + atrasados (padrão)\n"
            "  equilibrada — balança paridade e faixa"
        ),
    )
    p.add_argument("--jogos",         type=int, default=1,  help="Quantos jogos gerar (padrão: 1)")
    p.add_argument("--min-frequentes",type=int, default=2,  help="Mín. de números frequentes (mista)")
    p.add_argument("--max-frequentes",type=int, default=4,  help="Máx. de números frequentes (mista)")
    p.add_argument("--min-atrasados", type=int, default=1,  help="Mín. de números atrasados (mista)")
    p.add_argument("--max-atrasados", type=int, default=3,  help="Máx. de números atrasados (mista)")
    p.add_argument("--min-pares",     type=int, default=2,  help="Mín. de números pares (equilibrada)")
    p.add_argument("--max-pares",     type=int, default=5,  help="Máx. de números pares (equilibrada)")
    p.add_argument("--min-baixos",    type=int, default=2,  help="Mín. de números baixos 1-15 (equilibrada)")
    p.add_argument("--max-baixos",    type=int, default=5,  help="Máx. de números baixos 1-15 (equilibrada)")
    p.add_argument("--sem-metricas",  action="store_true",  help="Oculta o resumo de métricas")
    p.add_argument("--seed",          type=int, default=None, help="Semente aleatória para reprodutibilidade")
    return p.parse_args()


def main():
    args = _parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    config = {
        "estrategia":     args.estrategia,
        "min_frequentes": args.min_frequentes,
        "max_frequentes": args.max_frequentes,
        "min_atrasados":  args.min_atrasados,
        "max_atrasados":  args.max_atrasados,
        "min_pares":      args.min_pares,
        "max_pares":      args.max_pares,
        "min_baixos":     args.min_baixos,
        "max_baixos":     args.max_baixos,
        "n_jogos":        args.jogos,
    }

    print(f"\nCarregando dados de: {args.dados!r} ...")
    try:
        historico = carregar_dados(args.dados)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERRO: {e}")
        raise SystemExit(1)

    if not historico:
        print("ERRO: Nenhum concurso encontrado.")
        raise SystemExit(1)

    print(f"{len(historico)} concursos carregados (#{historico[0]['concurso']} → #{historico[-1]['concurso']})")

    metricas = calcular_metricas(historico)

    if not args.sem_metricas:
        exibir_metricas(metricas)

    n = config["n_jogos"]
    if n == 1:
        jogo = gerar_jogo(metricas, config)
        exibir_jogo(jogo)
    else:
        jogos = gerar_e_ranquear(metricas, config, n_jogos=n * 3)  # gera 3x e rankeia
        melhores = jogos[:n]
        # Reatribui posições
        for i, j in enumerate(melhores, start=1):
            j["posicao"] = i
        exibir_ranking(melhores)
        print("\n--- Detalhes do melhor jogo ---")
        exibir_jogo(melhores[0], posicao=1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4.4: Rodar todos os testes**

```bash
python -m pytest tests/test_analise.py -v
```

Saída esperada: todos os testes PASS.

- [ ] **Step 4.5: Teste de integração rápido**

```bash
python analisar_diadesorte.py --dados dados/ --estrategia mista --jogos 3 --seed 42
```

Saída esperada: métricas + ranking de 3 jogos + detalhes do melhor.

- [ ] **Step 4.6: Commit final**

```bash
git add analisar_diadesorte.py tests/test_analise.py
git commit -m "feat: add ranker, display functions, and CLI for diadesorte analyzer"
```

---

## Exemplo de Uso

```bash
# Jogo único com estratégia padrão (mista)
python analisar_diadesorte.py --dados dados/

# 5 jogos com estratégia equilibrada, sem mostrar métricas
python analisar_diadesorte.py --dados dados/ --estrategia equilibrada --jogos 5 --sem-metricas

# Jogo reprodutível (mesma seed = mesmo jogo)
python analisar_diadesorte.py --dados dados/ --estrategia frequentes --seed 123

# Estratégia atrasados com restrição de paridade customizada
python analisar_diadesorte.py --dados dados/ --estrategia atrasados --min-pares 3 --max-pares 4

# A partir de CSV
python analisar_diadesorte.py --dados historico.csv --estrategia mista --jogos 10
```

---

## Self-Review

**Cobertura de spec:**
- ✅ Req 1: loader aceita JSON (diretório, arquivo) e CSV
- ✅ Req 2: frequência, atraso, paridade, faixa, mês da sorte
- ✅ Req 3: 4 estratégias implementadas
- ✅ Req 4: função `gerar_jogo` produz 7 números + 1 mês
- ✅ Req 5: config com min/max para frequentes, atrasados, pares, baixos
- ✅ Req 6: `razoes` dict com motivo de cada número
- ✅ Req 7: `score` 0-100 + exibição de métricas do jogo
- ✅ Req 8: funções separadas com docstrings, tratamento de erros na CLI
- ✅ Req 9: `gerar_e_ranquear` gera N jogos e ordena por score
- ✅ Req 10: seção "Exemplo de Uso" + `--help` via argparse

**Placeholder scan:** nenhum TBD/TODO encontrado.

**Type consistency:** `gerar_jogo` retorna `dict` com `"razoes": dict[int, str]` — consistente com `exibir_jogo` que itera `jogo["razoes"]`.
