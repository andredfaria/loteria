# Quina — Análise Estatística e Predição

Sistema de coleta, análise estatística, predição e geração de jogos para a Quina (5 números sorteados de 1–80).

> **Aviso:** Ferramenta de estudo estatístico. Loteria é jogo de azar — cada sorteio é um evento aleatório independente.

---

## Instalação

```bash
git clone https://github.com/andredfaria/loteria.git
cd loteria/quina
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
```

Requer Python ≥ 3.11.

---

## CLI — Uso Rápido

```bash
quina dados atualizar            # sincroniza concursos da API → SQLite + JSON
quina dados status               # total, último concurso, dezenas

quina modelo treinar             # walk-forward backtest (3 estratégias)
quina modelo leaderboard         # lista resultados de backtest

quina jogos gerar                # gera N jogos com estratégia escolhida
quina jogos fechamento           # fechamento (covering design)

quina portfolio gerar            # portfólio com restrição de orçamento
quina prever prever              # predição ensemble para o próximo concurso
```

---

## Dashboard Web

Flask + Gunicorn na porta **5000**.

```bash
gunicorn quina.interface.painel.server:app --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 600
```

### Rotas da API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/status` | Último concurso e totais |
| `GET` | `/api/frequencia` | Frequência por número |
| `GET` | `/api/atraso` | Atraso por número |
| `POST` | `/api/atualizar` | Sincroniza novos concursos |

---

## Arquitetura

```
src/quina/
├── dominio/           # Entidades (Sorteio), regras (80 nums, 5 por sorteio), exceções
├── infra/
│   ├── config.py      # Paths, constantes, API config
│   ├── dados/         # api_caixa.py (fetcher), banco.py (SQLite), leitor.py
│   ├── atributos/     # Feature engineering: base, advanced, builder
│   └── modelos/       # ML: FrequencyModel, Probabilistic, RF+XGB+LGBM Ensemble
├── servicos/          # 9 casos de uso: backtest, fechamento, portfolio, treinar, etc.
│   └── estrategias/   # Filtros estatísticos, scoring, frequência+atraso
└── interface/
    ├── cli/           # Typer CLI (quina dados, modelo, jogos, portfolio, prever)
    └── painel/        # Flask dashboard (server.py)
```

---

## Deploy com Docker

```dockerfile
# quina/Dockerfile (produção)
FROM python:3.12-slim
COPY pyproject.toml README.md ./
RUN pip install -e ".[dev]"
COPY src/ src/
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "quina.interface.painel.server:app", "--bind", "0.0.0.0:5000", ...]
```

| Campo | Valor |
|-------|-------|
| **Build Context** | `quina` |
| **Dockerfile Path** | `Dockerfile` |
| **Port** | `5000` |

---

## Testes

```bash
source venv/bin/activate
pytest                        # todos os testes
pytest testes/unidade/ -v    # testes unitários
pytest testes/integracao/ -v  # testes de integração
```

---

## Licença

MIT — veja [../LICENSE](../LICENSE).
