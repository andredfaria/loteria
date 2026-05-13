# Task 3.2 — Mover `atributos/` (feature engineering)

**Onda:** 3 — Migrar infra
**Prioridade:** alta
**Tempo estimado:** ~20 min
**Depende de:** 3.1

## Objetivo

Mover o canonical de feature engineering — `src/lotofacil_ml/features/` — para `src/lotofacil/infra/atributos/`. Atualizar imports nos consumidores.

`src/features/` (a versão órfã) NÃO é canônica — fica para deleção na onda 5.

## Descrição técnica

`src/lotofacil_ml/features/` contém o `FeatureBuilder` que gera ~123 features por concurso. Esse é o canônico (mais completo, atualmente em produção).

## Arquivos envolvidos

**Mover:**

| De | Para |
|---|---|
| `src/lotofacil_ml/features/<arquivo>.py` | `src/lotofacil/infra/atributos/<arquivo>.py` |

**Renomear arquivos para PT:**

| Antes | Depois |
|---|---|
| `feature_builder.py` (provavelmente) | `construtor_atributos.py` |
| `feature_definitions.py` | `definicoes_atributos.py` |
| outros que existirem | manter contexto técnico, com nome PT |

**Renomear classes:**

| Antes | Depois |
|---|---|
| `FeatureBuilder` | `ConstrutorAtributos` |

**Modificar (atualizar imports):**

- `src/cli/modelo.py` — `from lotofacil_ml.features.*` → `from lotofacil.infra.atributos.*`
- `src/cli/portfolio.py` — idem
- `src/lotofacil_ml/main.py`, `src/lotofacil_ml/scheduler/*` — atualizar
- `src/lotofacil_ml/models/*` — atualizar imports internos para `lotofacil.infra.atributos`
- `src/lotofacil_lab/*` — atualizar refs a `lotofacil_ml.features`

## Dependências

- 3.1

## Critérios de aceite

- [ ] `from lotofacil.infra.atributos import ConstrutorAtributos` funciona
- [ ] `grep -rn "from lotofacil_ml.features" src/cli/ src/dashboard/` retorna 0
- [ ] `lotofacil modelo treinar` funciona (ou erra "DB vazio")
- [ ] `pytest` passa

## Passos detalhados

- [ ] **Passo 1:** Listar arquivos a mover

```bash
ls src/lotofacil_ml/features/
```

- [ ] **Passo 2:** `git mv` dos arquivos

```bash
# Exemplo (ajustar conforme arquivos reais):
git mv src/lotofacil_ml/features/feature_builder.py src/lotofacil/infra/atributos/construtor_atributos.py
git mv src/lotofacil_ml/features/feature_definitions.py src/lotofacil/infra/atributos/definicoes_atributos.py
# ... outros conforme aparecerem
git mv src/lotofacil_ml/features/__init__.py /tmp/__feat_init.py  # backup; vamos reescrever
```

- [ ] **Passo 3:** Renomear classes nos arquivos movidos

```bash
sed -i 's/class FeatureBuilder\b/class ConstrutorAtributos/g' src/lotofacil/infra/atributos/*.py
sed -i 's/\bFeatureBuilder\b/ConstrutorAtributos/g' src/lotofacil/infra/atributos/*.py
```

Conferir manualmente para não substituir em strings de log/comentários.

- [ ] **Passo 4:** Atualizar imports internos (entre arquivos dentro de `atributos/`)

```bash
sed -i 's|from lotofacil_ml\.features\.|from lotofacil.infra.atributos.|g' src/lotofacil/infra/atributos/*.py
sed -i 's|from lotofacil_ml\.data\.|from lotofacil.infra.dados.|g' src/lotofacil/infra/atributos/*.py
```

E entidades do domínio:

```bash
sed -i 's|from lotofacil_ml.core.models import Draw|from lotofacil.dominio.entidades import Sorteio as Draw|g' src/lotofacil/infra/atributos/*.py
```

(O alias `Draw` ainda funciona da onda 2.2; em onda 8 vamos limpar.)

- [ ] **Passo 5:** Reescrever `src/lotofacil/infra/atributos/__init__.py`

```python
"""Camada de engenharia de atributos (features) — canonical do projeto.

Gera ~123 features por concurso a partir do histórico de sorteios.
"""
from .construtor_atributos import ConstrutorAtributos

__all__ = ["ConstrutorAtributos"]
```

- [ ] **Passo 6:** Atualizar consumidores em CLI

Em `src/cli/modelo.py`:

```bash
sed -i 's|from lotofacil_ml\.features import FeatureBuilder|from lotofacil.infra.atributos import ConstrutorAtributos|g' src/cli/modelo.py
sed -i 's|\bFeatureBuilder\b|ConstrutorAtributos|g' src/cli/modelo.py
```

Repetir para `cli/portfolio.py` se referenciar.

- [ ] **Passo 7:** Validar imports

```bash
python -c "from lotofacil.infra.atributos import ConstrutorAtributos; print('OK')"
python -c "from cli.modelo import app; print('OK')"
```

- [ ] **Passo 8:** Verificar consumidores residuais

```bash
grep -rn "from lotofacil_ml.features\|FeatureBuilder" src/
```

Esperado: 0 em `cli/`, `dashboard/`. Pode haver em `lotofacil_ml/main.py` (deletado na onda 5) ou `lotofacil_lab/` (move na onda 6).

- [ ] **Passo 9:** Atualizar `lotofacil_lab/` para usar `lotofacil.infra.atributos` se importar

```bash
grep -ln "lotofacil_ml.features\|FeatureBuilder" src/lotofacil_lab/
# Atualizar cada arquivo
```

- [ ] **Passo 10:** Testes

```bash
pytest
```

- [ ] **Passo 11:** Smoke

```bash
lotofacil modelo treinar  # ou pelo menos `lotofacil dados status` se base vazia
```

- [ ] **Passo 12:** Commit

```bash
git add -A
git commit -m "refactor(infra): move lotofacil_ml/features → infra/atributos (PT)

- FeatureBuilder → ConstrutorAtributos
- Imports atualizados em cli/modelo.py, cli/portfolio.py
- src/features/ (versão órfã) intocada — deletar na onda 5"
```
