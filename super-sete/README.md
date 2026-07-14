# Super Sete — Análise Estatística

Sistema de coleta e análise estatística para a Super Sete (7 colunas, cada uma com um dígito de 0–9).

> **Aviso:** Ferramenta de estudo estatístico. Loteria é jogo de azar — cada sorteio é um evento aleatório independente.

---

## Instalação

```bash
git clone https://github.com/andredfaria/loteria.git
cd loteria/super-sete
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
```

Requer Python ≥ 3.11.

---

## CLI — Uso Rápido

```bash
supersete dados atualizar       # sincroniza concursos da API (bulk) → SQLite + JSON
supersete dados status          # total, último concurso, dígitos
```

---

## Scripts Legados

Os scripts originais continuam funcionando independentemente:

```bash
python analise_estatistica.py                    # score composto por coluna
python analise_estatistica.py --arquivo dados/   #指定 diretório personalizado
python gerar_3_jogos.py                          # gera 3 jogos com estratégias diferentes
```

---

## Arquitetura

```
src/supersete/
├── dominio/           # Entidades (Sorteio: 7 dígitos 0-9), regras, exceções
├── infra/
│   ├── config.py      # Paths, API_SUPERSETE, timeout/retry
│   └── dados/         # api_caixa.py (fetcher bulk + incremental), banco.py (SQLite), leitor.py
└── interface/cli/     # Typer CLI (supersete dados)
```

### Regras do jogo

| Propriedade | Valor |
|-------------|-------|
| Colunas | 7 |
| Dígitos por coluna | 0–9 |
| Total de combinações | 10⁷ = 10.000.000 |
| Probabilidade (7/7) | 1 em 10 milhões |

### API

`https://loteriascaixa-api.herokuapp.com/api/supersete`

| Endpoint | Uso |
|----------|-----|
| `GET /api/supersete` | Bulk — todos os concursos |
| `GET /api/supersete/latest` | Último concurso |
| `GET /api/supersete/{n}` | Concurso específico |

---

## Testes

```bash
source venv/bin/activate
pytest                        # todos os testes (40)
pytest testes/unidade/ -v    # testes unitários
pytest testes/integracao/ -v  # testes de integração
```

---

## Licença

MIT — veja [../LICENSE](../LICENSE).
