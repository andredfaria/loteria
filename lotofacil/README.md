# Lotofácil Prediction System v2.0

Sistema modular de predição para a Lotofácil (15 números de 1–25) com Machine Learning, redes neurais e modelos estatísticos.

> **Aviso:** Ferramenta de estudo estatístico. Loteria é jogo de azar — cada sorteio é um evento aleatório independente.

---

## Instalação

```bash
git clone https://github.com/andredfaria/loteria.git
cd loteria/lotofacil
python -m venv venv && source venv/bin/activate
pip install -e .
```

> TensorFlow é opcional. Sem ele, modelos LSTM/Transformer são ignorados.

---

## Uso Rápido

```bash
# Dados
lotofacil dados atualizar --all   # importa histórico completo de dados/
lotofacil dados atualizar         # sincroniza novos sorteios da API
lotofacil dados status            # último concurso, total de draws

# Modelos
lotofacil modelo treinar          # treina ensemble (Frequency + ML + LSTM)
lotofacil modelo backtest         # walk-forward → saida/relatorio.html
lotofacil modelo historico        # histórico de predições
lotofacil modelo validar          # valida predições contra resultados reais

# Predição
lotofacil prever                  # prediz 11 números (cascade: neural → ensemble)
lotofacil prever --approach ml    # força abordagem específica

# Portfólio
lotofacil portfolio               # gera portfólio para o próximo concurso
lotofacil portfolio --jogos 8     # portfólio com 8 jogos
lotofacil portfolio --concurso N  # concurso específico
lotofacil portfolio validar N     # valida portfólio gerado para concurso N

# Experimentos (clima + lua + ablação)
lotofacil lab backfill-clima      # preenche histórico climático (Open-Meteo)
lotofacil lab lunar-check --data YYYY-MM-DD
lotofacil lab ablation            # ablation study completo
lotofacil lab treinar --config base+clima+lua
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
│   ├── cli/           # CLI unificada (entry point: lotofacil)
│   │   ├── app.py     # root Typer app + comando prever
│   │   ├── dados.py   # lotofacil dados atualizar / status
│   │   ├── modelo.py  # lotofacil modelo treinar / backtest / historico / validar
│   │   ├── portfolio.py # lotofacil portfolio [validar]
│   │   └── lab.py     # lotofacil lab (experimentos)
│   ├── core/          # Config, modelos, regras
│   ├── data/          # Fetcher, database, loader
│   ├── features/      # Feature engineering
│   ├── strategies/    # Estratégias plugáveis
│   │   └── eleven_numbers/  # statistical, ml, neural
│   ├── lotofacil_ml/  # Pipeline de produção (Frequency + ML + LSTM)
│   ├── lotofacil_lab/ # Pipeline experimental (clima, lua, ablação)
│   ├── models/        # Modelos ML reutilizáveis
│   └── evaluation/    # Métricas, backtest
├── legacy/            # Código arquivado (scripts e módulos antigos)
├── dados/sample/      # 100 sorteios mais recentes (committed)
├── tests/
└── docs/              # Arquitetura, relatórios técnicos, spec
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
