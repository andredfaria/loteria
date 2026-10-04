# Estratégia 11 Números

## Objetivo

Prever 11 números da Lotofácil com a maior probabilidade de conter 11 ou mais acertos.

## Racional

- Acertar 15 números é estatisticamente improvável (1 em 3.268.760)
- Acertar 11 números é muito mais acessível (prêmio fixo de R$ 7,00)
- Prever 11 números reduz o espaço de busca de C(25,15) para C(25,11) = 4.457.400
- O foco é maximizar a taxa de acertos em 11+

## Abordagens

### Statistical

Combina 4 sinais:

| Sinal | Peso | Descrição |
|-------|------|-----------|
| Frequência | 40% | Média ponderada de janelas 10, 30, 100 |
| Atraso | 25% | Inverso do gap desde última aparição |
| Tendência | 20% | freq_5 - freq_20 (números "quentes") |
| Co-ocorrência | 15% | Números que aparecem juntos frequentemente |

### ML (Ensemble)

Pipeline:
1. FeatureBuilder gera ~123 features por concurso
2. 3 classificadores: LightGBM, RandomForest, XGBoost
3. Cada classificador prevê probabilidade de cada número (0-25)
4. Média das probabilidades dos 3 modelos

Features incluem:
- Frequências em janelas (5, 10, 20, 30, 100)
- Atraso de cada número
- Estatísticas de soma, pares, ímpares
- Repetição média, consecutivos
- Co-ocorrência, tendência, volatilidade
- Faixa dominante, par quente

### Neural (LSTM + Attention)

Arquitetura:

```
Input: 50 sorteios × 75 features (binária + freq + atraso)
    ↓
Dropout(0.2)
    ↓
LSTM(128, return_sequences=True)
    ↓
MultiHeadAttention(128, heads=4) + LayerNorm
    ↓
LSTM(128, return_sequences=True)
    ↓
MultiHeadAttention(64, heads=1) + LayerNorm
    ↓
LSTM(64, return_sequences=False)
    ↓
Dropout(0.3)
    ↓
Dense(64, relu) + BatchNorm + Dropout(0.4)
    ↓
Dense(25, sigmoid) → probabilidade de cada número
```

- Janela de 50 sorteios
- 75 features por sorteio: 25 binárias + 25 frequência + 25 atraso
- Focal Loss (gamma=2.0, alpha=0.75) para lidar com desbalanceamento
- Validação temporal (últimos 20% dos dados)
- Early stopping com paciência de 10 epochs
- ReduceLROnPlateau para ajuste de learning rate
- Treina em ~20 epochs com 3670 sorteios

### Ensemble

Combinação ponderada:
- Statistical: 30%
- ML: 45%
- Neural: 25%

Se uma abordagem falhar, o peso é redistribuído proporcionalmente.

## Avaliação

### Métricas principais

- **Hit rate 11+**: % de previsões com 11+ acertos
- **Hit médio**: média de acertos por previsão
- **ROI**: retorno sobre investimento simulado

### Backtest

Walk-forward validation:
- Treina em janela de 300 sorteios
- Prediz o próximo
- Desliza e retreina a cada 50 sorteios
