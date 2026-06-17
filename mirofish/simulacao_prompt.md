# 🧠 MiroFish — Simulação de Predição para Lotofácil

## Objetivo

Simular um enxame de agentes de IA (swarm intelligence) para predizer os 15 números do **próximo concurso da Lotofácil**. O enxame deve analisar o histórico completo (3683 concursos), aplicar engenharia de atributos, cruzar estratégias e consolidar uma predição final com 15 números entre 1 e 25.

---

## 1. Contexto do Problema

| Regra | Valor |
|-------|-------|
| Total de números possíveis | 25 (1 a 25) |
| Números sorteados por concurso | 15 |
| Total de concursos históricos | 3683 |
| Periodicidade | Segunda, Quarta, Sexta (21h BRT) |
| Custo por jogo | R$ 3,50 |
| Faixas de premiação | 11, 12, 13, 14 e 15 acertos |

---

## 2. Estrutura dos Dados de Entrada

### `historico_lotofacil_limpo` (3683 concursos)

``
{
  "concurso": 3685,
  "data": "14/05/2026",
  "dezenas": [1, 2, 4, 8, 10, 11, 14, 15, 17, 19, 20, 21, 23, 24, 25],
  "estatisticas": {
    "pares": 7,
    "impares": 8,
    "soma_total": 214
  }
}
```

**Campos:**
- `concurso`: ID numérico sequencial do sorteio
- `data`: Data no formato DD/MM/AAAA
- `dezenas`: Lista de 15 inteiros sorteados (ordenados crescente)
- `estatisticas.pares`: Quantos números pares (0–15)
- `estatisticas.impares`: Quantos números ímpares (0–15) — sempre `15 - pares`
- `estatisticas.soma_total`: Soma dos 15 números

---

## 3. Feature Engineering Disponível

Todas as funções abaixo usam **apenas dados anteriores** ao concurso alvo (sem data leakage).

### 3.1 Atributos Base

| Feature | Descrição | Janelas |
|---------|-----------|---------|
| `freq_k(n)` | Frequência de cada número nas últimas `k` extrações | k=5, 10, 20 |
| `atraso(n)` | Quantos sorteios desde a última aparição (cap: 20) | — |
| `soma_mean/median/std` | Média/mediana/desvio da soma dos 15 números | k=5, 10, 20 |
| `pares_mean/impares_mean` | Média de pares e ímpares na janela | k=5, 10, 20 |
| `repeticao_mean` | Média de repetições entre concursos consecutivos | k=5, 10, 20 |
| `consecutivos_mean` | Média de pares consecutivos (ex: 7-8) | k=5, 10, 20 |
| `std_frequencias` | Desvio padrão das frequências entre números | — |
| `ratio_moldura_miolo` | Razão entre números na moldura vs. miolo | — |

### 3.2 Atributos Avançados

| Feature | Descrição |
|---------|-----------|
| `coocorrencia_score` | Co-ocorrência: quantas vezes cada número apareceu junto com outros (janela 30) |
| `trend_score` | Tendência: `freq_k5 - freq_k20` (positivo = aquecendo, negativo = esfriando) |
| `volatilidade_score` | Volatilidade: desvio padrão da frequência em sub-janelas dentro de 50 concursos |
| `faixa_dominante` | Faixa (1–5) com mais números no sorteio anterior |
| `par_quente_score` | Quantos dos top-10 mais frequentes têm atraso ≤ 3 |

### 3.3 Feature Vector Final (ML)

O `FeatureBuilder` gera **~184 features** por concurso incluindo todas as acima, usado para treinar o ensemble ML (RF + XGB + LGBM).

---

## 4. Modelos Existentes no Sistema

### 4.1 FrequencyModel
- Pondera frequências em janelas: k10 (50%), k30 (30%), histórico total (20%)
- Normaliza para [0, 1] e retorna probabilidade por número

### 4.2 FrequencyEnsembleModel
- Combina múltiplas janelas ponderadas: 5 (30%), 15 (25%), 30 (20%), 50 (15%), 100 (10%)

### 4.3 ProbabilisticModel
- Score = α × freq_normalizada + β × delay_normalizada
- α=0.6, β=0.4, janela=50
- `delay_score = 1 / (1 + atraso)` — números atrasados pontuam mais

### 4.4 MLEnsembleModel (RF + XGBoost + LightGBM)
- MultiOutputClassifier com soft-voting
- RF: 200 estimadores, max_depth=10, min_samples_leaf=5
- XGB: 200 estimadores, max_depth=6, lr=0.05
- LGBM: 200 estimadores, max_depth=6, lr=0.05
- Features: ~184 dimensões do FeatureBuilder

### 4.5 LSTMModel
- Arquitetura: LSTM(128) → Dropout(0.3) → LSTM(128) → Dropout(0.3) → Dense(25, sigmoid)
- Janela: 50 concursos consecutivos
- Treinado com binary_crossentropy + FocalLoss (γ=2.0, α=0.75)
- LR schedule: 1e-3 → 5e-4 → 2.5e-4 → 1.25e-4

### 4.6 TransformerModel
- Arquitetura: TransformerEncoder com 2 blocos, 4 cabeças, model_dim=64
- Janela: 50 concursos, treinado com FocalLoss

### 4.7 AutoencoderModel
- Encoder: 64 → 32 → 16 → bottleneck(8)
- Mapeia concurso anterior → concurso atual via bottleneck

### 4.8 EnsemblePredictor
- Combinação ponderada: Frequency (20%) + ML (50%) + Probabilistic (30%)

---

## 5. Estratégia de Predição (15 Números)

### 5.1 Abordagem Ensemble + SA
1. Ensemble pesa Neural (60%) + Frequência (40%) para obter probabilidades por número
2. Simulated Annealing com 5 restarts, 8000 iterações cada
3. Função objetivo: `combined_score = neural_score × 0.6 + filter_score_norm × 0.4`
4. Temperatura inicial: 3.0–5.0, cooling rate: 0.995–0.997

### 5.2 Filtros Estatísticos (Hierarquia)

| Nível | Filtro | Faixa Ideal | Peso | Ocorrência Histórica |
|-------|--------|-------------|------|---------------------|
| 1 | Soma total | 171–220 | 10.0 | ~84% dos concursos |
| 2 | Repetições do sorteio anterior | 8–10 | 8.0 | ~70% |
| 2 | Pares/Ímpares | 7–8 pares | 5.0 | ~56% |
| 3 | Moldura (1-5, 21-25 + bordas) | 9–10 | 5.0 | ~55% |
| 3 | Números primos | 4–7 | 3.0 | ~70% |
| 3 | Fibonacci | 3–5 | 3.0 | ~65% |
| 3 | Pares consecutivos | ≥2 | 3.0 | ~80% |

**Definições:**
- **Moldura**: {1,2,3,4,5,6,10,11,15,16,20,21,22,23,24,25}
- **Primos**: {2,3,5,7,11,13,17,19,23}
- **Fibonacci**: {1,2,3,5,8,13,21}

### 5.3 Heurísticas Complementares
- **Top-11 + fill-4**: Selecionar top-11 por probabilidade + preencher 4 otimizando filtros
- **Ciclo lunar**: Fase da lua no momento do sorteio (21h BRT, São Paulo)
- **Clima**: Condições climáticas no momento do sorteio (temperatura, pressão, umidade)

---

## 6. Métricas de Avaliação

| Métrica | Definição |
|---------|-----------|
| `mean_hits` | Média de acertos por concurso (esperado: ~11+) |
| `hit_distribution` | Distribuição de acertos (0–15) |
| `rate_ge(N)` | % de concursos com ≥N acertos (ex: rate_ge_11) |
| `ROI` | Retorno sobre investimento ((receita - custo) / custo) |
| `Sharpe` | Sharpe ratio da curva de equity |
| `Max Drawdown` | Maior queda percentual da equity |
| `p-value vs. aleatório` | Significância estatística vs. RandomBaseline |

**Baselines para comparação:**
- **Random**: 15 números aleatórios (mean_hits esperado ≈ 9.0)
- **Frequência histórica**: Top-15 mais frequentes
- **Delay**: Top-15 mais atrasados

---

## 7. Últimos 10 Concursos (para contexto local)

| Concurso | Data | Soma | Pares | Ímpares |
|----------|------|------|-------|---------|
| 3676 | 04/05/2026 | 229 | 8 | 7 |
| 3677 | 05/05/2026 | 190 | 9 | 6 |
| 3678 | 06/05/2026 | 174 | 9 | 6 |
| 3679 | 07/05/2026 | 194 | 7 | 8 |
| 3681 | 09/05/2026 | 184 | 7 | 8 |
| 3682 | 11/05/2026 | 176 | 7 | 8 |
| 3683 | 12/05/2026 | 185 | 8 | 7 |
| 3684 | 13/05/2026 | 188 | 5 | 10 |
| 3685 | 14/05/2026 | 214 | 7 | 8 |

---

## 8. Instruções para o Enxame MiroFish

### Agentes Especializados Recomendados

1. **Agente Frequencista**: Analisa frequências recentes (k=5, 10, 30, 100) + tendências (trend_score). Responde: *quais números estão "quentes" e "frios"?*

2. **Agente Atraso**: Foca em números com maior delay (atraso). Responde: *quais números estão "devendo" aparecer?*

3. **Agente Co-ocorrência**: Analisa pares e grupos que costumam sair juntos. Responde: *quais números tendem a aparecer simultaneamente?*

4. **Agente Filtros**: Valida candidatos contra os 7 filtros estatísticos. Responde: *este conjunto de 15 números é plausível?*

5. **Agente Sazonal**: Analisa ciclo lunar + clima. Responde: *há influência sazonal no resultado?*

6. **Agente Ensemble**: Combina todas as abordagens (frequência, ML, neural, probabilística). Responde: *qual a probabilidade consolidada de cada número?*

7. **Agente Otimizador**: Executa Simulated Annealing para maximizar o combined_score. Responde: *qual a melhor combinação de 15 números?*

### Fluxo de Simulação Sugerido

```
FASE 1 — Análise Individual
  Cada agente analisa o histórico e produz sua lista de 15 números + justificativa

FASE 2 — Debate
  Agentes discutem divergências, apontam fraquezas nas escolhas uns dos outros

FASE 3 — Consenso
  Votação ponderada: cada agente contribui com peso baseado na confiança
  Consolidação: top-15 por consenso OU SA com scores combinados

FASE 4 — Validação Final
  Verificar contra os 7 filtros estatísticos
  Verificar se a predição foge do padrão histórico (>2 desvios da média)
  Ajuste fino via troca de 1-2 números
```

### Formato da Resposta Final

``
{
  "concurso_alvo": 3686,
  "proximo_sorteio": "15/05/2026",
  "predicao": [1, 2, 4, 8, 10, 11, 14, 15, 17, 19, 20, 21, 23, 24, 25],
  "estatisticas": {
    "pares": 7,
    "impares": 8,
    "soma_total": 214,
    "repetidos_anterior": 9,
    "moldura": 10,
    "primos": 5,
    "fibonacci": 4,
    "consecutivos": 3
  },
  "agentes": {
    "frequencista": [lista de 15],
    "atraso": [lista de 15],
    "coocorrencia": [lista de 15],
    "ensemble": [lista de 15],
    "consenso_final": [lista de 15]
  },
  "confianca": 0.72,
  "justificativa": "Consenso entre 4 de 5 agentes. Números 3, 7, 22 substituídos por 4, 8, 24 no SA optimization. Soma 214 dentro da faixa 171-220 (84% histórico). 9 repetições do concurso 3685, alinhado com a média de 8-10 (70% histórico)."
}
```

---

## 9. Dados Completos

Os 3683 concursos históricos completos estão no arquivo `historico_lotofacil_limpo` neste mesmo diretório, no formato descrito na seção 2.
