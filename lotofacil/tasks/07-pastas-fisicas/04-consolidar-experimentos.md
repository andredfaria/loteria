# Task 7.4 — Consolidar `saida/experimentos/`

**Onda:** 7 — Pastas físicas
**Prioridade:** média
**Tempo estimado:** ~10 min
**Depende de:** 7.3

## Objetivo

Mover outputs do lab (`src/lotofacil_lab/output/`, `src/lotofacil_lab/saved_models/`) para `saida/experimentos/`. Atualizar imports em `experimentos/config.py` se necessário.

## Arquivos envolvidos

**Mover:**

| De | Para |
|---|---|
| `src/lotofacil_lab/output/*` | `saida/experimentos/` |
| `src/lotofacil_lab/saved_models/*` | `saida/experimentos/modelos/` |

**Deletar (vazias após mover):**
- `src/lotofacil_lab/output/`
- `src/lotofacil_lab/saved_models/`
- `src/lotofacil_lab/` (totalmente vazio agora — todas as outras subpastas foram movidas na onda 6.1)

## Dependências

- 7.3

## Critérios de aceite

- [ ] `ls saida/experimentos/` lista outputs do lab
- [ ] `ls saida/experimentos/modelos/` lista modelos do lab
- [ ] `src/lotofacil_lab/` não existe mais
- [ ] `lotofacil lab ablacao --n-test 5` funciona e gera output em `saida/experimentos/`
- [ ] `pytest src/lotofacil/experimentos/tests/` passa

## Passos detalhados

- [ ] **Passo 1:** Inspecionar fontes

```bash
ls -la src/lotofacil_lab/output/ 2>/dev/null
ls -la src/lotofacil_lab/saved_models/ 2>/dev/null
```

- [ ] **Passo 2:** Garantir destinos

```bash
mkdir -p saida/experimentos/modelos
```

- [ ] **Passo 3:** Mover

```bash
# output/ (relatórios de ablation, etc.)
for f in src/lotofacil_lab/output/*; do
    [ -f "$f" ] && git mv "$f" "saida/experimentos/$(basename "$f")"
    [ -d "$f" ] && git mv "$f" "saida/experimentos/$(basename "$f")"
done

# saved_models/
for f in src/lotofacil_lab/saved_models/*; do
    [ -f "$f" ] && git mv "$f" "saida/experimentos/modelos/$(basename "$f")"
done

# Limpar pastas vazias
[ -d src/lotofacil_lab/output ] && rmdir src/lotofacil_lab/output
[ -d src/lotofacil_lab/saved_models ] && rmdir src/lotofacil_lab/saved_models
[ -d src/lotofacil_lab ] && rmdir src/lotofacil_lab
```

- [ ] **Passo 4:** Atualizar `experimentos/config.py` se aponta para os paths antigos

```bash
grep -n "output\|saved_models" src/lotofacil/experimentos/config.py
```

Substituir refs a `lotofacil_lab/output/` por `EXPERIMENTOS_SAIDA_DIR` (importado de `lotofacil.infra.config`):

```python
# ANTES:
LAB_OUTPUT_DIR = PROJECT_ROOT / "src" / "lotofacil_lab" / "output"
SAVED_MODELS_DIR = PROJECT_ROOT / "src" / "lotofacil_lab" / "saved_models"

# DEPOIS:
from lotofacil.infra.config import EXPERIMENTOS_SAIDA_DIR
LAB_OUTPUT_DIR = EXPERIMENTOS_SAIDA_DIR
SAVED_MODELS_DIR = EXPERIMENTOS_SAIDA_DIR / "modelos"
```

- [ ] **Passo 5:** Validar

```bash
ls saida/experimentos/
ls saida/experimentos/modelos/
ls src/lotofacil_lab 2>&1 | grep -i "no such"
```

- [ ] **Passo 6:** Smoke

```bash
lotofacil lab ablacao --n-test 5
# Esperado: gera output em saida/experimentos/
ls saida/experimentos/
```

- [ ] **Passo 7:** Testes

```bash
pytest
```

- [ ] **Passo 8:** Commit

```bash
git add -A
git commit -m "chore(experimentos): consolida outputs do lab em saida/experimentos/

- src/lotofacil_lab/output/* → saida/experimentos/
- src/lotofacil_lab/saved_models/* → saida/experimentos/modelos/
- src/lotofacil_lab/ deletada (vazia após onda 6 + esta task)

experimentos/config.py atualizado para usar EXPERIMENTOS_SAIDA_DIR
de lotofacil.infra.config (single source of truth)."
```
