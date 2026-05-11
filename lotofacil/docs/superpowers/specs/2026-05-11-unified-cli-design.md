# Design: CLI Unificado — Lotofácil Prediction System

**Data:** 2026-05-11  
**Status:** Aprovado

---

## Contexto

O sistema de previsão da Lotofácil evoluiu ao longo do tempo em três camadas paralelas (`src/main.py`, `src/lotofacil_ml/main.py`, `src/lotofacil_lab/main.py`) mais scripts avulsos na raiz (`predict_portfolio.py`, `predict_3680.py`, etc.). Para publicação pública no GitHub, é necessário um único ponto de entrada coeso, com código legado separado claramente do código ativo.

**Objetivo:** CLI unificado (`lotofacil <grupo> <comando>`) que expõe todas as funcionalidades ativas, código legado arquivado em `legacy/`, e repositório pronto para publicação.

---

## Estrutura de Pastas (após refatoração)

```
lotofacil/
├── src/
│   ├── cli/                      # NOVO — entry point unificado
│   │   ├── __init__.py
│   │   ├── app.py                # Typer app raiz + registro dos grupos
│   │   ├── dados.py              # grupo: dados atualizar / status
│   │   ├── modelo.py             # grupo: modelo treinar / backtest / historico / validar
│   │   ├── portfolio.py          # comando: portfolio (absorve predict_portfolio.py)
│   │   └── lab.py                # grupo: lab backfill-clima / lunar-check / ablation / treinar
│   ├── core/                     # mantido (models, config, lottery utils)
│   ├── data/                     # mantido (fetcher, database, loader, climate_loader)
│   ├── features/                 # mantido (base, advanced, builder)
│   ├── strategies/               # mantido (eleven_numbers, quinze_numbers)
│   ├── models/                   # mantido
│   ├── evaluation/               # mantido
│   ├── lotofacil_ml/             # mantido — lógica de treino/predict/backtest
│   └── lotofacil_lab/            # mantido — pipeline experimental clima+lua
├── legacy/                       # NOVO — código arquivado (não removido)
│   ├── ml/                       # pipeline LightGBM sequencial original
│   ├── coleta/                   # busca_sorteios.py original
│   ├── geracao/                  # gerador_jogos_lotofacil.py original
│   ├── validacao/                # validar_jogos_provaveis.py original
│   ├── analise/                  # scripts de análise estatística
│   ├── sugestao/                 # ML experimental antigo
│   └── scripts/                  # predict_3680.py, backtest_peso_ml.py, etc.
├── dados/
│   └── sample/                   # 100 draws mais recentes (commitados)
├── docs/                         # mantido + este spec
├── tests/                        # mantido
├── .gitignore                    # NOVO
├── pyproject.toml                # atualizado: entry_point = lotofacil → src.cli.app:app
├── requirements.txt              # mantido
└── README.md                     # atualizado com nova estrutura de comandos
```

---

## Comandos do CLI

### Grupo `dados`
```bash
lotofacil dados atualizar          # sync novos concursos da API → SQLite
lotofacil dados status             # último concurso, total draws, período coberto
```

### Grupo `modelo`
```bash
lotofacil modelo treinar           # treina ensemble (FrequencyModel + MLEnsemble + LSTM)
lotofacil modelo backtest          # walk-forward validation → saida/relatorio.html
lotofacil modelo historico         # histórico de previsões (últimas 20)
lotofacil modelo validar           # valida previsões pendentes contra resultados reais
```

### Comando `prever`
```bash
lotofacil prever                           # prediz 11 números (cascade: neural → ensemble → freq)
lotofacil prever --approach ml             # força abordagem específica (statistical|ml|neural|all)
lotofacil prever --concurso N              # concurso alvo específico
```

### Comando `portfolio`
```bash
lotofacil portfolio                        # portfólio para o próximo concurso (default: 2 jogos)
lotofacil portfolio --concurso N           # concurso específico
lotofacil portfolio --jogos 8              # quantidade de jogos
lotofacil portfolio validar --concurso N   # confere resultado de um portfólio gerado
```

### Grupo `lab`
```bash
lotofacil lab backfill-clima               # preenche histórico de clima (Open-Meteo Archive)
lotofacil lab lunar-check --data YYYY-MM-DD
lotofacil lab ablation                     # ablation study completo (n-test, retrain-every)
lotofacil lab treinar --config base+clima+lua
lotofacil lab prever --config base+clima+lua
```

---

## Integração das Funcionalidades

| Comando CLI | Código fonte (reutilizado sem reescrita) |
|---|---|
| `dados atualizar` | `src/lotofacil_ml/data/fetcher.py` + `database.py` |
| `dados status` | `src/lotofacil_ml/data/database.py` |
| `modelo treinar` | `src/lotofacil_ml/models/` (FrequencyModel, MLEnsembleModel, LSTMModel) |
| `modelo backtest` | `src/lotofacil_ml/backtest/` (BacktestEngine, FinancialSimulator) |
| `modelo historico` | `src/lotofacil_ml/data/database.py` |
| `modelo validar` | `src/lotofacil_ml/evaluation/` + `src/lotofacil_ml/data/database.py` |
| `prever` | `src/strategies/eleven_numbers/predictor.py` + cascade fallback |
| `portfolio` | lógica de `predict_portfolio.py` movida para `src/cli/portfolio.py` |
| `portfolio validar` | `src/lotofacil_ml/evaluation/` + draw loader |
| `lab *` | `src/lotofacil_lab/main.py` (re-exposto como subgrupo Typer) |

`src/main.py` e `src/lotofacil_ml/main.py` permanecem como módulos internos mas **não são mais o entry point público**.

---

## Output (padrão Rich em todos os comandos)

- Tabelas com paleta de cores consistente (`rich.table.Table`)
- `prever` → Panel com dezenas + métricas de qualidade (soma, P/I, moldura, primos, Fibonacci)
- `portfolio` → tabela tiered (CONSERVADOR / EQUILIBRADO / AGRESSIVO) com barra de qualidade e ROI estimado
- `modelo backtest` → progresso no terminal + HTML em `saida/relatorio.html`
- Erros em vermelho com mensagem clara, sem stacktrace para o usuário final

---

## GitHub Readiness

**`.gitignore` (a criar):**
```
venv/
.venv/
__pycache__/
*.pyc
*.egg-info/
src/lotofacil.db
src/models_saved/
src/lotofacil_lab/saved_models/
saida/
output/
dados/clima/
dados/*.csv
dados/processed/
ml/datasets/
ml/modelos/
portfolio/*.txt
```

**`pyproject.toml` — entry point a atualizar:**
```toml
[project.scripts]
lotofacil = "src.cli.app:app"
```

**`README.md`** — seção "Quick Start" atualizada com os novos comandos.

---

## Verificação (como testar após implementação)

```bash
# 1. Instalar
pip install -e .

# 2. Verificar help
lotofacil --help
lotofacil dados --help
lotofacil modelo --help
lotofacil portfolio --help
lotofacil lab --help

# 3. Fluxo completo
lotofacil dados atualizar
lotofacil dados status
lotofacil modelo treinar
lotofacil prever
lotofacil portfolio --jogos 4

# 4. Testes existentes devem continuar passando
pytest tests/ -v
pytest src/lotofacil_lab/tests/ -v
```

---

## O que NÃO faz parte deste design

- Reescrita da lógica de ML ou modelos
- Novos modelos ou features
- Interface web ou TUI
- Mudança nos formatos de dado (Draw JSON, SQLite schema)
