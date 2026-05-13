# Task 1.2 — Deletar órfãos óbvios

**Onda:** 1 — Limpeza segura
**Prioridade:** alta
**Tempo estimado:** ~5 min
**Depende de:** 1.1

## Objetivo

Remover três órfãos diretos: `src/sugestao/` (pacote vazio, só `__init__.py` e cache de teste), `src/main.py` (entry point não registrado em `pyproject.toml`, segundo CLI competindo com `src/cli/app.py`), e `src/lotofacil.db` (duplicata do banco em `data/lotofacil.db`).

## Descrição técnica

- `src/sugestao/` não contém código Python (`find src/sugestao -name "*.py"` retorna vazio).
- `src/main.py` consome `src/core/`, `src/data/`, `src/evaluation/`, `src/models/`, `src/features/` — uma sub-árvore órfã. Ao remover `main.py`, essa sub-árvore vira inutilizada (será deletada na onda 5 após movermos os pedaços que ainda têm consumidores vivos: `src/data/loader.py`, `src/data/preprocessor.py`, `src/evaluation/comparison.py`, `src/strategies/*`).
- `src/lotofacil.db` é um SQLite duplicado; o canônico é `data/lotofacil.db`.

## Arquivos envolvidos

**Deletar:**
- `src/sugestao/` (incluindo `__pycache__`, `tests/`)
- `src/main.py`
- `src/lotofacil.db`

**Não tocar (esta onda):**
- `src/core/`, `src/data/`, `src/evaluation/`, `src/models/`, `src/features/` — apesar de órfãos após main.py sair, têm pedaços canônicos a mover (onda 3) ou consumidores vivos (`cli/app.py prever` usa `data/loader.py` e `strategies/`).

## Dependências

- Task 1.1 (legacy/legado/ml deletados)

## Critérios de aceite

- [ ] `ls src/sugestao 2>&1 | grep -i "no such"`
- [ ] `ls src/main.py 2>&1 | grep -i "no such"`
- [ ] `ls src/lotofacil.db 2>&1 | grep -i "no such"`
- [ ] `pyproject.toml [project.scripts]` continua apontando para `src.cli.app:app` (não tocado nesta task)
- [ ] `pytest` passa
- [ ] `lotofacil dados status` funciona

## Passos detalhados

- [ ] **Passo 1:** Verificar que nada importa do que vamos remover

```bash
grep -rn "from sugestao\|import sugestao\|from src.sugestao" src/ tests/ 2>/dev/null
grep -rn "from main\|import main" src/ tests/ 2>/dev/null | grep -v __pycache__
```

Esperado: 0 resultados.

- [ ] **Passo 2:** Verificar que `pyproject.toml` aponta só para cli/app

```bash
grep "src.main\|src.cli" pyproject.toml
```

Esperado: apenas `lotofacil = "src.cli.app:app"`. Sem `src.main`.

- [ ] **Passo 3:** Deletar `src/sugestao/`

```bash
git rm -rf src/sugestao/
```

- [ ] **Passo 4:** Deletar `src/main.py`

```bash
git rm src/main.py
```

- [ ] **Passo 5:** Deletar `src/lotofacil.db`

```bash
git rm src/lotofacil.db 2>/dev/null || rm -f src/lotofacil.db
```

(Pode não estar no git se gitignored — fallback para `rm` direto.)

- [ ] **Passo 6:** Verificar estado

```bash
ls src/ | grep -E "sugestao|main.py|lotofacil.db"   # 0 resultados
```

- [ ] **Passo 7:** Testes + smoke

```bash
pytest
lotofacil dados status
```

- [ ] **Passo 8:** Commit

```bash
git commit -m "chore: remove órfãos (src/sugestao, src/main.py, src/lotofacil.db)

- src/sugestao/ era vazio (sem .py)
- src/main.py era entry point não registrado em pyproject.toml
- src/lotofacil.db duplicava data/lotofacil.db

Subdiretorios órfãos restantes (src/core, src/features, src/models,
src/evaluation) saem na onda 5 após movimentação dos pedaços canônicos.

Parte da onda 1 do refactor de consolidação estrutural."
```
