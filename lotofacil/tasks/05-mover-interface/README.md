# Onda 5 — Mover interface + renomear CLI

**Prioridade:** alta
**Risco:** médio
**Tasks:** 7
**Pré-requisitos:** Onda 4

## Objetivo

Mover `src/cli/` → `src/lotofacil/interface/cli/` e `src/dashboard/` → `src/lotofacil/interface/painel/`, renomear comandos e flags para PT (corte limpo), refatorar endpoints do painel para usar serviços diretamente, atualizar `pyproject.toml` para a nova layout, e deletar os resíduos órfãos das ondas anteriores.

## Renomeações CLI (corte limpo)

| Atual | Novo |
|---|---|
| `lotofacil dados atualizar --all` | `lotofacil dados atualizar --escopo todos` |
| `lotofacil dados atualizar --latest` | `lotofacil dados atualizar --escopo ultimo` |
| `lotofacil prever --approach all` | `lotofacil prever --abordagem todas` |
| `lotofacil prever --approach ml` | `lotofacil prever --abordagem ml` (valor mantém) |
| `lotofacil lab ablation` | `lotofacil lab ablacao` |
| `lotofacil lab lunar-check` | `lotofacil lab checar-lua` |
| `lotofacil lab backfill-clima` | `lotofacil lab preencher-clima` |
| `lotofacil lab compare` | `lotofacil lab comparar` |
| `lotofacil dashboard` | `lotofacil painel` |

Loanwords mantidos: `status`, `backtest`, `ablacao` (cognato), `treinar` (já PT), `historico` (já PT), `validar`, `portfolio` (cognato).

## Refatoração do painel

Endpoints **de leitura** passam a chamar `lotofacil.servicos.*` diretamente (sem subprocess):

| Endpoint | Antes | Depois |
|---|---|---|
| `GET /api/status` | leitura de arquivos + glob | `consultar_status_base()` |
| `GET /api/games` | glob de `saida/jogos/` | `listar_jogos_gerados()` |
| `GET /api/games/:f` | path traversal manual | `listar_jogos_gerados(filename=...)` |
| `GET /api/predictions` | glob + agrupamento | `listar_historico_predicoes()` |
| `GET /api/models/status` | glob de `.keras` | `listar_modelos_treinados()` |

Endpoints **de ação** (`POST /api/generate`) continuam usando `subprocess` para preservar streaming via SSE.

## `pyproject.toml` mudanças

```toml
[project.scripts]
lotofacil = "lotofacil.interface.cli.app:app"  # era "src.cli.app:app"

[tool.setuptools.packages.find]
where = ["src"]                                 # era include = ["src*"]
include = ["lotofacil*"]
```

Após mudança: `pip install -e .` deve ser re-executado.

## Resíduos a deletar nesta onda

Após mover cli e dashboard, e após CLI/painel passarem a usar `lotofacil.*` exclusivamente:

- `src/lotofacil_ml/` (vazio ou só com main.py/config.py legado)
- `src/strategies/` (vazio)
- `src/data/` (loader, database, fetcher restantes — órfãos duplicatas)
- `src/features/`, `src/models/`, `src/evaluation/` (órfãos v2.0)
- `src/core/` (conteúdo já portado na onda 2)
- `src/cli/` (vazia após move)
- `src/dashboard/` (vazia após move)

## Tasks

1. `01-mover-cli.md` — `src/cli/` → `interface/cli/`
2. `02-mover-painel.md` — `src/dashboard/` → `interface/painel/` + Flask static_folder
3. `03-painel-usa-servicos.md` — endpoints de leitura via serviços
4. `04-renomear-flags-pt.md` — `--all`, `--approach`, etc.
5. `05-renomear-comandos-pt.md` — `lab ablation`, `lab lunar-check`, `dashboard`, etc.
6. `06-atualizar-pyproject.md` — entry point + packages.find + `pip install -e .`
7. `07-deletar-orfaos.md` — `lotofacil_ml/`, `strategies/`, `data/`, `features/`, `models/`, `evaluation/`, `core/`, `cli/`, `dashboard/`

## Critérios de aceite (onda inteira)

- [ ] `pytest` passa
- [ ] `pip install -e .` instala sem erro
- [ ] `lotofacil --help` mostra novos comandos PT
- [ ] `lotofacil dados atualizar --escopo todos` funciona
- [ ] `lotofacil prever --abordagem ml` funciona
- [ ] `lotofacil lab ablacao --n-test 10` funciona
- [ ] `lotofacil painel &` sobe; `curl localhost:5000/api/status` retorna JSON
- [ ] `find src/ -maxdepth 2 -type d` mostra apenas `src/lotofacil/`
- [ ] **Flags antigas (--all, --approach, ablation, etc.) NÃO funcionam mais**

## Smoke test

```bash
pip install -e .                        # OK
lotofacil --help                        # mostra comandos PT
lotofacil dados status
lotofacil prever --abordagem ml
lotofacil portfolio --jogos 4
lotofacil lab ablacao --n-test 10
lotofacil painel &
PID=$!
sleep 2
curl -s localhost:5000/api/status | jq .
kill $PID
find src/ -maxdepth 2 -type d
```
