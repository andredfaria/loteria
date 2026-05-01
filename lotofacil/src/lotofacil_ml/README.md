# Lotofácil ML

Sistema de predição baseado em ML para a Lotofácil brasileira (15 números sorteados de 1–25).

## Instalação

```bash
cd /home/andre/Documentos/projetos/loteria/lotofacil
source .venv/bin/activate
pip install -r app/lotofacil_ml/requirements.txt
```

## Uso — CLI

Todos os comandos devem ser executados a partir de `app/lotofacil_ml/`:

```bash
cd app/lotofacil_ml

# 1. Carregar todos os sorteios do diretório dados/ local
python main.py update --all

# 2. Buscar apenas o último sorteio via API
python main.py update --latest

# 3. Treinar todos os modelos
python main.py train

# 4. Gerar predição para o próximo concurso
python main.py predict

# 5. Validar predições pendentes contra resultados reais
python main.py validate

# 6. Backtest walk-forward nos últimos 100 sorteios
python main.py backtest --n 100

# 7. Relatório de desempenho
python main.py report
python main.py report --output relatorio.txt  # exporta para arquivo

# 8. Iniciar agendador automático
python main.py schedule --start

# 9. Histórico de predições
python main.py history --limit 20
```

Use `--debug` em qualquer comando para ativar logging detalhado.

## Modelos

### FrequencyModel
Score ponderado de frequências recentes:
```
score = 0.5 × freq_30 + 0.3 × freq_100 + 0.2 × freq_all
```

### MLEnsembleModel
`MultiOutputClassifier` com `VotingClassifier(soft)` sobre:
- `RandomForestClassifier(n_estimators=200, max_depth=10)`
- `XGBClassifier`
- `LGBMClassifier`

Validação cruzada temporal com `TimeSeriesSplit(n_splits=5)`.

### LSTMModel
Rede LSTM com janelas de 50 sorteios:
```
LSTM(128, return_sequences=True) → Dropout(0.3)
  → LSTM(64) → Dropout(0.3)
    → Dense(25, sigmoid)
```
Requer TensorFlow ≥ 2.16. Se indisponível, o ensemble continua apenas com Frequency + ML (pesos renormalizados).

### EnsemblePredictor
Combinação ponderada:
| Modelo    | Peso |
|-----------|------|
| Frequency | 0.20 |
| ML        | 0.45 |
| LSTM      | 0.35 |

## Fluxo de Dados

```
dados/*.json  →  DatabaseManager (SQLite)  →  LotofacilPreprocessor
                                               ↓
                                    FrequencyModel + MLEnsembleModel + LSTMModel
                                               ↓
                                        EnsemblePredictor.predict_next_concurso()
```

## Testes

```bash
cd app/lotofacil_ml
pytest tests/ -v
```

## Agendamento Automático

O `LotofacilScheduler` executa automaticamente:

| Job                   | Quando                     |
|-----------------------|----------------------------|
| `update_data`         | Seg/Qua/Sex às 23h         |
| `retrain_models`      | Segunda-feira às 2h        |
| `validate_predictions`| Após `update_data`         |
| `generate_prediction` | Após `retrain_models`      |

---

> **Aviso estatístico**: Loteria é um jogo de azar. Nenhum sistema estatístico ou de ML pode prever resultados futuros com precisão acima do acaso. Este projeto é de natureza educacional e analítica. Aposte com responsabilidade.
