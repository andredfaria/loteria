# Lotofácil Prediction System v2.0

Sistema modular de predição para a Lotofácil (15 números de 1–25) com Machine Learning, redes neurais e modelos estatísticos.

> **Aviso:** Ferramenta de estudo estatístico. Loteria é jogo de azar — cada sorteio é um evento aleatório independente.

---

## Instalação

```bash
python -m venv venv && source venv/bin/activate
pip install -e .
```

> TensorFlow é opcional. Sem ele, modelos LSTM/Transformer são ignorados.

---

## Uso Rápido

```bash
# Coletar sorteios
python src/main.py collect --latest
python src/main.py collect --sync

# Processar dados
python src/main.py process

# Ver status
python src/main.py status

# Predição de 11 números
python src/main.py predict
python src/main.py predict --approach ml
python src/main.py predict --approach statistical
python src/main.py predict --approach neural

# Treinar modelo neural
python src/main.py train-neural

# Backtest
python src/main.py backtest
python src/main.py backtest --window 200

# Comparar abordagens
python src/main.py compare
```

---

## Estrutura

```
lotofacil/
├── docs/              # Documentação
├── data/              # Dados centralizados
│   ├── raw/concursos/ # JSONs brutos
│   ├── processed/     # Dados processados
│   └── lotofacil.db   # SQLite
├── src/
│   ├── core/          # Config, modelos, regras
│   ├── data/          # Fetcher, database, loader
│   ├── features/      # Feature engineering
│   ├── strategies/    # Estratégias plugáveis
│   │   ├── eleven_numbers/  # Predição de 11 números
│   │   │   ├── approaches/  # statistical, ml, neural
│   │   │   ├── predictor.py
│   │   │   └── evaluator.py
│   │   └── future/          # 12, 13, 14 números
│   ├── models/        # Modelos ML reutilizáveis
│   ├── evaluation/    # Métricas, backtest
│   └── main.py        # CLI unificada
├── scripts/           # collect.py, process.py
├── tests/
└── output/            # Predictions, reports, models
```

---

## Estratégias

### 11 Números (atual)

Prediz 11 números com maior probabilidade de conter 11+ acertos.

| Abordagem | Descrição |
|-----------|-----------|
| `statistical` | Frequência + atraso + tendência + co-ocorrência |
| `ml` | Ensemble LightGBM + RandomForest + XGBoost |
| `neural` | LSTM (2 camadas, janela de 50 sorteios) |
| `all` | Ensemble ponderado das 3 abordagens |

### Próximas

- **12 números** (`strategies/future/twelve_numbers/`)
- **13 números** (`strategies/future/thirteen_numbers/`)
- **14 números** (`strategies/future/fourteen_numbers/`)

---

## API

```
https://loteriascaixa-api.herokuapp.com/api/lotofacil/<concurso>
```

---

## Licença

MIT — veja [../LICENSE](../LICENSE).
