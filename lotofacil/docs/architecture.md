# Arquitetura — Lotofácil Prediction System v2.0

## Visão Geral

Sistema modular para predição de números da Lotofácil com foco em estratégia de 11 números, usando ML, redes neurais e modelos estatísticos.

## Princípios

| Princípio | Descrição |
|-----------|-----------|
| Dados centralizados | `data/` é a única fonte de verdade — SQLite + JSON |
| Estratégias plugáveis | Interface `BaseStrategy` — cada estratégia herda e implementa |
| Features reutilizáveis | `src/features/` serve todas as estratégias |
| Modelos agnósticos | `src/models/` não sabem sobre estratégias |
| Avaliação padronizada | Mesmas métricas para todas as estratégias |
| CLI única | Um entry point: `python src/main.py <comando>` |

## Camadas

```
┌─────────────────────────────────────────┐
│              CLI (main.py)              │
├─────────────────────────────────────────┤
│           Strategies Layer              │
│  eleven_numbers → approaches: stat/ml/n │
├─────────────────────────────────────────┤
│          Models + Features              │
│  Frequency / Ensemble / Neural / Feats  │
├─────────────────────────────────────────┤
│            Data Layer                   │
│  Fetcher / Database / Loader / Process  │
├─────────────────────────────────────────┤
│            Storage                      │
│  data/raw/  data/processed/  lotofacil.db│
└─────────────────────────────────────────┘
```

## Fluxo de Dados

```
API Caixa → fetcher → SQLite + raw JSON
                              ↓
                         loader → Draw[]
                              ↓
                       preprocessor → X, y
                              ↓
                        features → vetores
                              ↓
                    strategies → predictions
                              ↓
                     evaluation → métricas
```

## Estratégia 11 Números

O objetivo é prever 11 números (em vez de 15) que contenham o máximo de acertos possíveis.

### Abordagens

1. **Statistical** — Combina frequência ponderada, atraso (gap desde última aparição), tendência (freq_5 - freq_20) e co-ocorrência
2. **ML** — FeatureBuilder gera ~123 features por concurso; ensemble de LightGBM + RF + XGBoost classifica cada número (0/1)
3. **Neural** — LSTM de 2 camadas com janela de 50 sorteios, prevendo probabilidade de cada número
4. **Ensemble (all)** — Combina as 3 com pesos: stat 30%, ml 45%, neural 25%

## Extensibilidade

### Adicionar nova estratégia

1. Criar pasta em `src/strategies/<nome>/`
2. Implementar `BaseStrategy` (predict, predict_batch, name, target_count, approaches)
3. Registrar em `src/main.py`

### Adicionar nova abordagem

1. Criar arquivo em `src/strategies/<nome>/approaches/`
2. Implementar interface: `fit(draws)`, `predict_proba()`, `name`
3. Registrar no predictor da estratégia
