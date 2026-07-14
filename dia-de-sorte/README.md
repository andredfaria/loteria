# Dia de Sorte — Análise Estatística

Sistema de coleta, análise estatística e geração de jogos para o Dia de Sorte (7 números de 1–31 + Mês da Sorte).

> **Aviso:** Ferramenta de estudo estatístico. Loteria é jogo de azar — cada sorteio é um evento aleatório independente.

---

## Instalação

```bash
git clone https://github.com/andredfaria/loteria.git
cd loteria/dia-de-sorte
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
```

Requer Python ≥ 3.11.

---

## CLI — Uso Rápido

```bash
diadesorte dados atualizar      # sincroniza concursos da API (bulk) → SQLite + JSON
diadesorte dados status         # total, último concurso, dezenas, mês da sorte
```

---

## Scripts Legados

Os scripts originais continuam funcionando independentemente:

```bash
python analisar_diadesorte.py --dados dados/ --estrategia mista --jogos 5
python analisar_diadesorte.py --dados dados/ --estrategia equilibrada --sem-metricas
```

---

## Arquitetura

```
src/diadesorte/
├── dominio/           # Entidades (Sorteio com validação 1-31 + mes_sorte), regras, exceções
├── infra/
│   ├── config.py      # Paths, API_DIADESORTE, timeout/retry
│   └── dados/         # api_caixa.py (fetcher bulk + incremental), banco.py (SQLite), leitor.py
└── interface/cli/     # Typer CLI (diadesorte dados)
```

### Dados

A API `https://loteriascaixa-api.herokuapp.com/api/diadesorte` oferece 3 endpoints:

| Endpoint | Uso |
|----------|-----|
| `GET /api/diadesorte` | Bulk — baixa todos os concursos em 1 request (~1.2MB) |
| `GET /api/diadesorte/latest` | Último concurso |
| `GET /api/diadesorte/{n}` | Concurso específico |

---

## Estratégias de Jogo (scripts)

O `analisar_diadesorte.py` implementa 4 estratégias com score 0-100:

- **frequentes** — pesos maiores para números mais sorteados
- **atrasados** — pesos maiores para números há mais tempo ausentes
- **mista** — combina frequentes + atrasados com limites configuráveis
- **equilibrada** — rejection sampling forçando paridade (2-5 pares) e faixa (2-5 baixos)

Documentação detalhada em [`docs/`](docs/).

---

## Testes

```bash
source venv/bin/activate
pytest                        # todos os testes (69)
pytest testes/unidade/ -v    # testes unitários
pytest testes/integracao/ -v  # testes de integração
```

---

## Licença

MIT — veja [../LICENSE](../LICENSE).
