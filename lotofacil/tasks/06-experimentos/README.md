# Onda 6 — Experimentos

**Prioridade:** média
**Risco:** baixo
**Tasks:** 3
**Pré-requisitos:** Onda 5

## Objetivo

Mover o pacote experimental (lab) de `src/lotofacil_lab/` para `src/lotofacil/experimentos/`, atualizar todos os imports internos e externos, e garantir que ele consuma o core consolidado em `src/lotofacil/infra/*`.

`experimentos/` continua **isolado**: pode importar de `dominio/`, `infra/` e `servicos/`, mas nunca o contrário.

## Estrutura final

```
src/lotofacil/experimentos/
├── __init__.py
├── coleta/                # backfill clima
├── dados/                 # loaders clima, lua, draws wrapper
├── atributos/             # blocos modulares (base, temporal, climate, lunar, ...)
├── modelos/               # baseline_random, baseline_frequency, neural_modular
├── avaliacao/             # walkforward, metrics, permutation_importance
├── uso/                   # use cases do lab (rodar_ablacao, treinar_lab, ...)
└── tests/ (apenas até a onda 8; depois move para testes/unidade/experimentos/)
```

## Imports a atualizar

- Dentro do `experimentos/`: substituir todos os `from lotofacil_lab.*` por `from lotofacil.experimentos.*`
- Substituir referências a `lotofacil_ml.config` por `lotofacil.infra.config` (já movido na onda 3)
- Atualizar `interface/cli/lab.py` se ainda referenciar `lotofacil_lab.main`

## Renames internos (PT)

A maioria dos arquivos do lab já tem nome PT/EN misto. Renomeações da onda 5 já lidam com comandos. Aqui só renomes de arquivos:

- `lotofacil_lab/coleta/backfill_clima_archive.py` → `experimentos/coleta/preencher_clima_archive.py`
- `lotofacil_lab/data/draws_loader.py` → `experimentos/dados/leitor_sorteios.py`
- `lotofacil_lab/data/climate_loader.py` → `experimentos/dados/clima.py`
- `lotofacil_lab/data/lunar_loader.py` → `experimentos/dados/lua.py`
- `lotofacil_lab/data/feature_flags.py` → `experimentos/dados/flags_atributos.py`
- `lotofacil_lab/experiments/runner.py` → `experimentos/uso/rodar_ablacao.py`
- `lotofacil_lab/experiments/ablation_grid.py` → `experimentos/uso/grade_ablacao.py`
- `lotofacil_lab/experiments/report.py` → `experimentos/uso/relatorio.py`

`main.py` interno some — comandos do lab são acionados por `interface/cli/lab.py` (já existe).

## Tasks

1. `01-mover-lab.md` — `git mv src/lotofacil_lab/ src/lotofacil/experimentos/` + ajustar `__init__.py` e estrutura
2. `02-atualizar-imports.md` — substituir `lotofacil_lab.*` por `lotofacil.experimentos.*`, e `lotofacil_ml.config` por `lotofacil.infra.config`
3. `03-renomear-arquivos-pt.md` — renomes da tabela acima + ajuste de imports

## Critérios de aceite (onda inteira)

- [ ] `pytest src/lotofacil/experimentos/tests/` passa
- [ ] `lotofacil lab ablacao --n-test 10` funciona
- [ ] `lotofacil lab checar-lua --data 2026-05-13` retorna fase lunar
- [ ] `lotofacil lab preencher-clima --ultimos 5` funciona (sem erro de import)
- [ ] **Nenhum** `from lotofacil_lab` no projeto inteiro (`grep -rn "lotofacil_lab" src/`)
- [ ] `find src/ -name "lotofacil_lab*"` retorna vazio

## Smoke test

```bash
pytest src/lotofacil/experimentos/tests/
lotofacil lab ablacao --n-test 10
lotofacil lab checar-lua --data 2026-05-13
grep -rn "lotofacil_lab" src/    # 0 resultados
```
