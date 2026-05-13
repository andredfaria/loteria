# Task 8.4 — Atualizar `README.md`, `CLAUDE.md`, `AGENTS.md`

**Onda:** 8 — Testes + docs
**Prioridade:** média
**Tempo estimado:** ~25 min
**Depende de:** 8.3

## Objetivo

Atualizar as 3 docs de orientação ao desenvolvedor para refletir a nova estrutura:

- `README.md` (raiz do `lotofacil/`) — instalação, comandos PT, estrutura
- `CLAUDE.md` (raiz do `lotofacil/`) — guia para Claude Code
- `AGENTS.md` (raiz do `lotofacil/`) — contexto técnico

Também atualizar o `CLAUDE.md` superior (em `loteria/`) se ele referencia paths antigos.

## Arquivos envolvidos

**Modificar:**
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `/home/andre/Documentos/projetos/loteria/CLAUDE.md` (verificar — referências a `src/coleta/`, `src/geracao/`, `ml/`)

## Dependências

- 8.3

## Critérios de aceite

- [ ] `README.md` documenta comandos PT atuais (`lotofacil dados atualizar --escopo`, `lotofacil prever --abordagem`, `lotofacil painel`)
- [ ] `README.md` mostra nova estrutura (`src/lotofacil/{dominio,servicos,infra,interface,experimentos}/`)
- [ ] `CLAUDE.md` mostra entry point único (`lotofacil` via Typer)
- [ ] `AGENTS.md` reflete pacote `lotofacil` (sem refs a `src/coleta/`, `ml/`)
- [ ] CLAUDE.md superior atualizado

## Passos detalhados

- [ ] **Passo 1:** Atualizar `README.md`

Substituir seção "Uso Rápido" para os comandos PT:

```markdown
## Uso Rápido

```bash
# Dados
lotofacil dados atualizar --escopo todos     # importa histórico completo
lotofacil dados atualizar                    # sincroniza novos sorteios
lotofacil dados status                       # último concurso, total

# Modelos
lotofacil modelo treinar                     # treina ensemble
lotofacil modelo backtest                    # walk-forward → saida/relatorios/
lotofacil modelo historico                   # histórico de predições
lotofacil modelo validar                     # valida contra resultados reais

# Predição
lotofacil prever                             # predição (cascade: neural → ensemble)
lotofacil prever --abordagem ml              # força abordagem

# Portfólio
lotofacil portfolio                          # portfólio para próximo concurso
lotofacil portfolio --jogos 8                # 8 jogos
lotofacil portfolio --concurso N             # concurso específico
lotofacil portfolio validar N                # valida portfólio gerado

# Painel web
lotofacil painel                             # localhost:5000

# Experimentos
lotofacil lab preencher-clima                # histórico climático
lotofacil lab checar-lua --data YYYY-MM-DD
lotofacil lab ablacao                        # ablation study
lotofacil lab treinar --config base+clima+lua
```
```

E atualizar seção "Estrutura":

```markdown
## Estrutura

```
lotofacil/
├── docs/
├── dados/                              # symlink → ~/lotofacil-dados/
│   ├── concursos/                      # JSONs da API CAIXA
│   ├── processado/
│   └── lotofacil.db                    # SQLite
├── saida/
│   ├── jogos/                          # portfolios + predições apostáveis
│   ├── predicoes/                      # relatórios analíticos
│   ├── modelos/                        # .keras, .joblib
│   ├── relatorios/                     # HTML, KPI, backtest
│   ├── experimentos/                   # outputs do lab
│   └── logs/
├── src/lotofacil/
│   ├── dominio/                        # Sorteio, Predicao, regras
│   ├── servicos/                       # use cases (11)
│   ├── infra/
│   │   ├── dados/                      # API CAIXA, SQLite
│   │   ├── atributos/                  # feature engineering
│   │   ├── modelos/                    # ML implementations
│   │   ├── estrategias/                # 11–15 dezenas
│   │   ├── avaliacao/                  # backtest, métricas
│   │   ├── geracao/                    # portfólio
│   │   └── agendador/                  # APScheduler
│   ├── interface/
│   │   ├── cli/                        # Typer
│   │   └── painel/                     # Flask + SSE
│   └── experimentos/                   # clima, lua, ablação
├── testes/
│   ├── unidade/
│   └── integracao/
└── tasks/                              # plano executado deste refactor
```
```

- [ ] **Passo 2:** Atualizar `CLAUDE.md` (raiz do lotofacil/)

Substituir seção "Common Commands":

```markdown
## Common Commands

```bash
pip install -e .                             # após clone

# Collect data
lotofacil dados atualizar                    # novos
lotofacil dados atualizar --escopo todos     # histórico completo

# Generate games
lotofacil prever                             # 11 dezenas
lotofacil portfolio --jogos 8                # portfólio

# ML pipeline
lotofacil modelo treinar
lotofacil modelo backtest
lotofacil modelo validar

# Tests
pytest                                       # tudo
pytest testes/unidade/dominio/               # subset

# Lab
lotofacil lab preencher-clima
lotofacil lab checar-lua --data 2026-05-13
lotofacil lab ablacao --n-test 100
```
```

E atualizar seção "Architecture" e "Path Convention" para refletir `src/lotofacil/` e `infra/config.py`.

- [ ] **Passo 3:** Atualizar `AGENTS.md`

Substituir seção "Estrutura e Responsabilidades":

```markdown
## Estrutura e Responsabilidades

```
src/lotofacil/
├── dominio/        entidades + regras (puro, sem IO)
├── servicos/       use cases (11)
├── infra/
│   ├── dados/      API CAIXA → dados/concursos/, SQLite
│   ├── atributos/  feature engineering (~123 features)
│   ├── modelos/    Frequência, Ensemble ML, LSTM
│   ├── estrategias/onze, doze, treze, quatorze, quinze dezenas
│   ├── avaliacao/  backtest, walk-forward, métricas
│   ├── geracao/    portfólio
│   └── agendador/  APScheduler
├── interface/
│   ├── cli/        Typer (lotofacil <cmd>)
│   └── painel/     Flask + SSE
└── experimentos/   lab (clima, lua, ablação)
```

## Convenção de Paths

Todos os módulos usam `from lotofacil.infra.config import DADOS_DIR, SAIDA_DIR, DB_PATH, ...` — nunca calculam Path inline.

## Entry Point Único

`pyproject.toml` registra apenas `lotofacil = "lotofacil.interface.cli.app:app"`. Tudo passa por essa CLI.
```

- [ ] **Passo 4:** Atualizar `loteria/CLAUDE.md` (do monorepo)

Verificar e ajustar:

```bash
cat /home/andre/Documentos/projetos/loteria/CLAUDE.md
```

Substituir refs a comandos antigos (`python src/coleta/busca_sorteios.py`, etc.) pelos novos (`lotofacil dados atualizar`).

- [ ] **Passo 5:** Smoke

```bash
# Validar que os exemplos do README funcionam
lotofacil dados status
lotofacil prever --abordagem ml
lotofacil portfolio --jogos 3
```

- [ ] **Passo 6:** Commit

```bash
git add README.md CLAUDE.md AGENTS.md /home/andre/Documentos/projetos/loteria/CLAUDE.md
git commit -m "docs: atualiza README, CLAUDE, AGENTS para a estrutura consolidada

- README.md: comandos PT atuais, nova estrutura src/lotofacil/
- CLAUDE.md: entry point único, arquitetura por camadas
- AGENTS.md: pacote lotofacil, sem refs a src/coleta/, ml/, lotofacil_ml
- loteria/CLAUDE.md: comandos do monorepo atualizados"
```
