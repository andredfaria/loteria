# Onda 8 — Testes + docs

**Prioridade:** média
**Risco:** baixo
**Tasks:** 5
**Pré-requisitos:** Onda 7

## Objetivo

Consolidar todos os testes em `testes/` no root, alinhada com a nova arquitetura por camadas. Remover aliases temporários (`Draw = Sorteio`). Atualizar toda a documentação (`README.md`, `CLAUDE.md`, `AGENTS.md`, `docs/architecture.md`, `docs/PRD-dashboard.md`).

## Estrutura final de testes

```
testes/
├── __init__.py
├── unidade/
│   ├── __init__.py
│   ├── dominio/                # puro, sem mocks
│   │   ├── test_entidades.py
│   │   ├── test_regras.py
│   │   └── test_excecoes.py
│   ├── infra/                  # cada infra com fakes do contrato
│   │   ├── dados/
│   │   ├── atributos/
│   │   ├── modelos/
│   │   ├── estrategias/
│   │   └── avaliacao/
│   ├── servicos/               # use cases com fakes
│   └── experimentos/           # lab
└── integracao/
    ├── cli/                    # smoke tests via CliRunner do Typer
    └── painel/                 # endpoints via test client do Flask
```

## Migrações

| De | Para |
|---|---|
| `tests/test_strategies/` (raiz) | `testes/unidade/infra/estrategias/` |
| `src/lotofacil_ml/tests/` (na onda 3 virou `src/lotofacil/infra/.../tests/`) | `testes/unidade/infra/<sub>/` |
| `src/lotofacil_lab/tests/` (na onda 6 virou `experimentos/tests/`) | `testes/unidade/experimentos/` |
| `src/dashboard/tests/` (na onda 5 virou `interface/painel/tests/`) | `testes/integracao/painel/` |
| `src/sugestao/tests/` (deletado na onda 1) | — |

## Atualização de `pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["testes"]
pythonpath = ["src"]                      # ou continua com conftest.py
```

## `conftest.py` da raiz

Pode ser removido (setuptools já registra `lotofacil` como pacote via `pip install -e .` na onda 5) ou simplificado:

```python
# conftest.py — pode ser deletado se pip install -e . estiver feito
# Atualmente: sys.path.insert(0, "src")
```

## Remoção de aliases temporários

Em `src/lotofacil/dominio/entidades.py`, remover:

```python
# REMOVER:
Draw = Sorteio
Prediction = Predicao
```

Antes de remover, garantir que NENHUM código ainda usa `Draw`/`Prediction`:

```bash
grep -rn "import Draw\|import Prediction\|from.*Draw\|from.*Prediction" src/ testes/
```

Se aparecer algum resultado, é bug — atualizar para `Sorteio`/`Predicao`.

## Documentação a atualizar

| Arquivo | Mudanças principais |
|---|---|
| `README.md` | Comandos PT, nova estrutura, instalação via `pip install -e .` |
| `CLAUDE.md` (root da loteria) | Paths novos, convenção PT, comando único `lotofacil` |
| `CLAUDE.md` (lotofacil/) | Diretórios novos, ref a config consolidada |
| `AGENTS.md` | Substituir refs a `src/coleta/`, `src/geracao/`, `ml/` pela árvore nova |
| `docs/architecture.md` | Substituir diagrama "v2.0" pelo de camadas + capacidades |
| `docs/PRD-dashboard.md` | Atualizar seção "arquitetura do sistema" (endpoints idênticos, mas estrutura interna nova) |

## Tasks

1. `01-consolidar-testes.md` — mover testes para `testes/{unidade,integracao}/`
2. `02-atualizar-pytest-config.md` — `pyproject.toml [tool.pytest.ini_options]` + (opcional) remover `conftest.py`
3. `03-remover-aliases-temporarios.md` — `Draw=Sorteio`, `Prediction=Predicao`
4. `04-atualizar-docs-codigo.md` — `README.md`, `CLAUDE.md`, `AGENTS.md`
5. `05-atualizar-docs-arquitetura.md` — `docs/architecture.md`, `docs/PRD-dashboard.md`

## Critérios de aceite (onda inteira)

- [ ] `pytest` rodando do root descobre todos os testes (sem `PYTHONPATH=src`)
- [ ] Nenhum `Draw` / `Prediction` em `src/` ou `testes/` (use `grep -rn`)
- [ ] `README.md` documenta os comandos PT atuais
- [ ] `docs/architecture.md` reflete a arquitetura realizada
- [ ] `CLAUDE.md` aponta para `src/lotofacil/` como raiz do código
- [ ] `find . -maxdepth 3 -type d -name "tests" -not -path "./.venv/*" -not -path "./venv/*"` retorna apenas `./testes` (e suas subpastas)

## Smoke test

```bash
pytest                              # passa, descobre tudo
grep -rn "Draw\b\|Prediction\b" src/ testes/   # 0 resultados (só Sorteio/Predicao)
find . -maxdepth 3 -type d -name "tests" -not -path "./.venv/*" -not -path "./venv/*"
lotofacil dados status              # ainda funciona
lotofacil prever                    # ainda funciona
```

## Critério final do refactor inteiro

Após onda 8, executar checklist completo:

```bash
pytest
pip install -e .
lotofacil dados status
lotofacil prever
lotofacil portfolio --jogos 4
lotofacil painel &
curl -s localhost:5000/api/status | jq .
kill %1
lotofacil lab ablacao --n-test 50
```

Tudo deve passar/funcionar. ✅
