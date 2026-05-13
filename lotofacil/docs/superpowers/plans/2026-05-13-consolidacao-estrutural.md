# Consolidação Estrutural — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar o `lotofacil/` em uma codebase aderente ao PRD via consolidação estrutural (sem novas funcionalidades): eliminar duplicações, adotar 4 camadas explícitas (domínio/serviços/infra/interface), padronizar PT total.

**Architecture:** 8 ondas sequenciais de refactor, cada uma um commit atomico reversível, com critérios de aceite (`pytest` verde + smoke test de pelo menos um comando CLI). Wave 3 é a mais arriscada (move imports vivos); waves 7-8 são as mais visíveis (caminhos físicos + docs).

**Tech Stack:** Python 3.11+, Typer (CLI), Flask (painel), SQLite, pylunar, scikit-learn / LightGBM / XGBoost, TensorFlow (opcional), pytest, setuptools (src-layout).

**Spec de origem:** `docs/superpowers/specs/2026-05-12-consolidacao-estrutural-design.md`

---

## Organização das tasks

A pasta `tasks/` na raiz do projeto contém as tasks executáveis, organizadas por onda. Cada arquivo `.md` é uma task individual com objetivo, descrição técnica, arquivos envolvidos, dependências, critérios de aceite e prioridade.

```
tasks/
├── README.md                  # índice + execução
├── 01-limpeza-segura/
├── 02-esqueleto-dominio/
├── 03-migrar-infra/
├── 04-criar-servicos/
├── 05-mover-interface/
├── 06-experimentos/
├── 07-pastas-fisicas/
└── 08-testes-docs/
```

Total: **42 tasks** em 8 ondas.

---

## Resumo das ondas

| # | Onda | Tasks | Prioridade | Risco | Reversível |
|---|---|---|---|---|---|
| 1 | Limpeza segura | 3 | alta | baixo | sim |
| 2 | Esqueleto + domínio | 6 | alta | baixo | sim |
| 3 | Migrar infra | 5 | alta | **médio-alto** | parcial |
| 4 | Criar servicos/ | 6 | alta | médio | sim |
| 5 | Mover interface | 7 | alta | médio | parcial |
| 6 | Experimentos | 3 | média | baixo | sim |
| 7 | Pastas dados/saida | 7 | média | médio | parcial |
| 8 | Testes + docs | 5 | média | baixo | sim |

---

## Mapa de dependências entre ondas

```
1 (limpeza) ──▶ 2 (domínio) ──▶ 3 (infra) ──▶ 4 (servicos)
                                                   │
                                                   ▼
                                              5 (interface)
                                                   │
                          ┌────────────────────────┤
                          ▼                        ▼
                  6 (experimentos)          7 (pastas físicas)
                          │                        │
                          └──────────┬─────────────┘
                                     ▼
                                8 (testes + docs)
```

---

## Conjunto de testes e critérios "feito"

Cada onda termina com:

1. **`pytest`** passa (do diretório atual de testes — migra na onda 8)
2. **Smoke test** específico da onda (ver critério em cada README de onda)
3. **Commit atomico** com mensagem padronizada

Critério final do refactor (ao terminar a onda 8):

```bash
pytest                                              # passa
pip install -e .                                    # instala sem erro
lotofacil dados status                              # responde
lotofacil prever                                    # gera predição (ou diz "DB vazio" se vazio)
lotofacil portfolio --jogos 4                       # gera portfólio
lotofacil painel &                                  # sobe servidor
curl -s localhost:5000/api/status | jq .            # JSON válido
lotofacil lab ablacao --n-test 50                   # lab roda
```

E:
- Não há pasta `data/`, `output/`, `legacy/`, `legado/`, `ml/`, `src/main.py`, `src/sugestao/`, `src/core/`, `src/models/`, `src/evaluation/`, `src/features/`, `src/data/`, `src/strategies/`, `src/lotofacil_ml/`, `src/lotofacil_lab/`
- Comandos CLI usam flags/nomes PT (`--abordagem`, `lab ablacao`, `lab checar-lua`, `lab preencher-clima`, `painel`)
- `docs/architecture.md` descreve a arquitetura realizada
- `CLAUDE.md` / `AGENTS.md` / `README.md` alinhados

---

## Execução

Por task: ler o arquivo `.md` em `tasks/<onda>/<task>.md`, executar os passos detalhados, validar critérios, commit.

**Modos de execução suportados:**

1. **Subagent-Driven (recomendado):** dispatch um subagent por task, com review entre tasks. Use a skill `superpowers:subagent-driven-development`.
2. **Inline:** executar tasks em batch nesta sessão com checkpoints. Use a skill `superpowers:executing-plans`.

Mais detalhes em `tasks/README.md`.
