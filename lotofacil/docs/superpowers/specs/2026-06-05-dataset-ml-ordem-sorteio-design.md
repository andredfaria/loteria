# Design — Dataset ML + Schema + Dicionário de Dados (Lotofácil)

**Data:** 2026-06-05
**Alvo declarado:** `dezenasOrdemSorteio`
**Abordagem escolhida:** A (predição de conjunto — "quais 15 dezenas") + dataset/dicionário completos

---

## Contexto e premissa honesta

`dezenasOrdemSorteio` é a ordem física em que as 15 bolas saem da máquina — um
sorteio mecânico justo. A **ordem** não carrega sinal aprendível: clima, lua,
dia da semana, nada desloca qual bola sai em 3º. Portanto:

- O alvo trein**ável** é **quais 15 dezenas** saem no próximo concurso (vetor
  binário de 25 posições). É o único alvo com alguma estrutura (deriva de
  frequência, gap desde a última aparição) — ainda assim próximo do aleatório.
- `dezenasOrdemSorteio` é preservado no schema como coluna bruta (fonte do
  alvo e base para features descritivas como `primeira_dezena`), não como o
  alvo de regressão/classificação.
- A avaliação reporta honestamente acertos@15 vs baseline aleatório (~9
  esperados). Empatar com o acaso é o resultado correto a reportar, não um bug.

---

## 1. Montagem / Join

Novo módulo: `src/lotofacil/experimentos/data/dataset_ml.py`.
Produz **uma tabela tidy, uma linha por concurso**, juntando três fontes
existentes (reaproveitando loaders já presentes):

| Fonte | Chave de join | Como |
|-------|---------------|------|
| Sorteios (`dados/concurso_*.json` / tabela `concursos`) | `concurso` | base — `dezenas`, `dezenasOrdemSorteio`, `data`, `local` |
| Clima (`dados/clima/`) | `concurso` | `climate_loader.load_all_climate()` → 8 campos do `resumo` (left join) |
| Lua (`dados/lua/`) | data ISO | `lunar_loader.compute_lunar_features(iso)` → 7 campos (left join) |

- Normalização de data `DD/MM/YYYY → YYYY-MM-DD` reaproveita
  `lunar_loader._parse_iso`.
- Left join: concursos sem clima/lua recebem `NaN` nas colunas
  correspondentes + flags `tem_clima` / `tem_lua` (0/1). Sem imputação
  inventada na tabela canônica.

---

## 2. Schema da tabela canônica (descritiva, por concurso)

Valores **brutos interpretáveis** (não normalizados) para o dicionário fazer
sentido. A normalização acontece só na etapa de modelagem.

**Meta**
- `concurso` — int, PK
- `data` — date (ISO `YYYY-MM-DD`)
- `local` — text

**Sorteio do próprio concurso**
- `dezenas` — JSON `list[int]` (15, ordenadas asc)
- `dezenas_ordem_sorteio` — JSON `list[int]` (15, na ordem sorteada) — **fonte do alvo**
- `primeira_dezena` — int (derivada: 1ª bola sorteada)
- `bola_01` … `bola_25` — binário (1 = número saiu neste concurso)

**Clima (8, brutos)**
- `temp_min`, `temp_max`, `temp_media`, `temp_sorteio` (°C)
- `precip_media`, `precip_sorteio` (mm)
- `wcode_sorteio`, `wcode_dominante` (código WMO)

**Lua (7, já em [0,1] ou flags)**
- `phase`, `phase_sin`, `phase_cos`, `illumination`, `age_norm`, `is_new`, `is_full`

**Temporal (derivado da data)**
- `dow_sin`, `dow_cos`, `mes_sin`, `mes_cos`

**Cobertura**
- `tem_clima`, `tem_lua` — 0/1

**Persistência:** `saida/datasets/lotofacil_ml.parquet` + `.csv`.

---

## 3. Alvo e transformação de modelagem (Modelo A — "quais 15")

Para prever **sem vazamento temporal**, o alvo é o sorteio do concurso `t+1`.
A função `to_training_matrix()` converte a tabela canônica para o formato
**long (por dezena)** — 1 linha por `(concurso, numero)`:

**Features (por número, no concurso `t`)**
- `freq_10`, `freq_30`, `freq_100`, `freq_all` — frequência do número nas
  últimas N janelas (lógica reaproveitada de `infra/dados/preprocessador.py`)
- `days_since_last` — sorteios desde a última aparição (cap/normalização 50)
- `saiu_no_anterior` — binário (estava no concurso `t`)
- clima (8) + lua (7) + temporal (4) do concurso `t`
- `numero` — id 1–25 (feature categórica)

**Alvo**
- `saiu_no_proximo` — binário (número está no sorteio do concurso `t+1`)

Regra anti-vazamento: features usam apenas informação até e incluindo `t`;
clima/lua são os do concurso `t` (defasados), nunca os de `t+1`. A última linha
(sem `t+1` conhecido) é descartada do treino.

**Modelo:** um único **LightGBM** binário sobre o formato long → probabilidade
por número → ordena desc → seleciona **top-15** por concurso.

---

## 4. Avaliação honesta

- **Split temporal:** treina nos concursos antigos, valida nos mais recentes
  (sem shuffle — respeita a ordem cronológica).
- **Métricas:**
  - acertos@15 médio vs **baseline aleatório (~9 esperados)** e baseline de
    frequência pura
  - logloss e AUC da classificação binária por número
- **Relatório:** texto explícito dizendo se o modelo supera o acaso. Resultado
  esperado: empate estatístico — reportado como tal.

---

## 5. Dicionário de dados (entregável central)

- `docs/dicionario_dados_ml.md` — tabela legível por humano:
  `coluna · tipo · unidade · fonte · papel (meta/feature/alvo) · descrição`.
- `saida/datasets/schema.json` — versão máquina-legível, **gerada pelo módulo**
  a partir da definição única de colunas (nunca dessincroniza do código).

Fonte única de verdade: uma estrutura de definição de colunas no módulo
`dataset_ml.py` alimenta tanto o DataFrame quanto o `schema.json` quanto a
geração do markdown.

---

## 6. Entrega, execução e testes

**Deliveráveis de código**
- `src/lotofacil/experimentos/data/dataset_ml.py` — `build_dataset()`,
  `to_training_matrix()`, `write_schema_json()`, definição de colunas.
- `src/lotofacil/experimentos/models/modelo_ordem_lgbm.py` (ou similar) —
  treino/avaliação LightGBM.
- `scripts/build_ml_dataset.py` — gera parquet/csv + schema.json + dicionário.
- `scripts/train_modelo_ordem.py` — treina e avalia o Modelo A, imprime
  relatório honesto.

**Dependência**
- Adicionar `lightgbm` ao `pyproject.toml`.

**Testes (`pytest`, usando `dados/sample/`)**
- join correto (linhas = concursos; valores de clima/lua batem com o sample)
- flags de cobertura `tem_clima`/`tem_lua` corretas
- normalização de data `DD/MM/YYYY → ISO`
- **shift do alvo sem vazamento** (`saiu_no_proximo` vem de `t+1`; última linha
  descartada)
- seleção top-15 retorna exatamente 15 números distintos
- `schema.json` lista exatamente as colunas reais do DataFrame

---

## Out of scope (YAGNI)

- Predição da ordem específica das bolas (Modelo B / learning-to-rank).
- Integração com o dashboard Flask.
- Subcomando CLI (`lab dataset ...`) — scripts bastam para reprodutibilidade.
- Imputação sofisticada de clima/lua ausentes (left join + flags é suficiente).
