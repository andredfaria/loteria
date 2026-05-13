# Onda 1 — Limpeza segura

**Prioridade:** alta
**Risco:** baixo
**Tasks:** 3
**Pré-requisitos:** nenhum

## Objetivo

Remover código arquivado, artefatos órfãos e duplicatas físicas — **sem** mover ou renomear nada do código vivo. Reduzir o ruído antes do refactor de fato.

## Escopo

| Categoria | Itens |
|---|---|
| Arquivos antigos | `legacy/` (8 subpastas), `legado/` (preservando docs úteis em `docs/`), `ml/` (pipeline de scripts standalone) |
| Órfãos óbvios | `src/sugestao/` (vazio), `src/main.py` (entry point não registrado), `src/lotofacil.db` (duplicata) |
| Artefatos de build | `portfolio_*.txt`, `portfolio_*.json` na raiz, `lotofacil_prediction.egg-info/`, `__pycache__/` |

## O que NÃO deletar nesta onda

- `src/core/`, `src/data/`, `src/features/`, `src/models/`, `src/evaluation/` — apesar de órfãos após `src/main.py` sair, ainda há partes referenciadas (`src/data/loader.py` por `cli/app.py prever`; `src/evaluation/comparison.py` é canônico único). Estes saem na **onda 5** após migração.
- `dados/`, `data/`, `output/`, `saida/`, `src/dashboard/`, `src/cli/`, `src/lotofacil_ml/`, `src/lotofacil_lab/`, `src/strategies/` — todos vivos.

## Tasks

1. `01-deletar-arquivados.md` — remover `legacy/`, `legado/` (preservando 2 docs), `ml/`
2. `02-deletar-orfaos.md` — remover `src/sugestao/`, `src/main.py`, `src/lotofacil.db`
3. `03-limpar-raiz.md` — remover artefatos da raiz (`portfolio_*.{txt,json}`, `egg-info/`, `__pycache__/`)

## Critérios de aceite (onda inteira)

- [ ] `pytest` passa idêntico ao antes
- [ ] `git status` mostra apenas deleções
- [ ] `lotofacil dados status` ainda funciona (não dependia dos arquivos removidos)
- [ ] Tamanho do repositório diminui (verificar com `du -sh .git`)

## Smoke test

```bash
pytest
lotofacil dados status
```
