# Task 6.2 — Atualizar imports do lab

**Onda:** 6 — Experimentos
**Prioridade:** média
**Tempo estimado:** ~25 min
**Depende de:** 6.1

## Objetivo

Substituir todos os `from lotofacil_lab.*` por `from lotofacil.experimentos.*` em todo o código. Também substituir refs ao core antigo (`lotofacil_ml.config`, `core.models`, etc.) pelo core consolidado (`lotofacil.infra.config`, `lotofacil.dominio.entidades`).

## Arquivos envolvidos

**Modificar (todos os .py em experimentos e cli/lab.py):**
- `src/lotofacil/experimentos/**/*.py`
- `src/lotofacil/interface/cli/lab.py`

## Dependências

- 6.1

## Critérios de aceite

- [ ] `grep -rn "from lotofacil_lab\|import lotofacil_lab" src/` retorna 0
- [ ] `grep -rn "from lotofacil_ml\|import lotofacil_ml" src/` retorna 0 (qualquer resíduo dos sub-pacotes movidos)
- [ ] `grep -rn "from core\.\|from data\.\|from strategies\." src/lotofacil/experimentos/` retorna 0
- [ ] `lotofacil lab ablacao --n-test 5` funciona
- [ ] `pytest src/lotofacil/experimentos/tests/` passa

## Passos detalhados

- [ ] **Passo 1:** Mapear imports a atualizar

```bash
grep -rn "from lotofacil_lab\|import lotofacil_lab" src/ 2>/dev/null
grep -rn "from lotofacil_ml\|from core\.\|from data\.\|from strategies\." src/lotofacil/experimentos/ 2>/dev/null
```

- [ ] **Passo 2:** Substituir `lotofacil_lab.*` em batch

```bash
# Substituir lotofacil_lab.X por lotofacil.experimentos.X em todos os .py
find src/lotofacil/experimentos -name "*.py" -exec sed -i \
  -e 's|from lotofacil_lab\.coleta|from lotofacil.experimentos.coleta|g' \
  -e 's|from lotofacil_lab\.data|from lotofacil.experimentos.dados|g' \
  -e 's|from lotofacil_lab\.features|from lotofacil.experimentos.atributos|g' \
  -e 's|from lotofacil_lab\.models|from lotofacil.experimentos.modelos|g' \
  -e 's|from lotofacil_lab\.evaluation|from lotofacil.experimentos.avaliacao|g' \
  -e 's|from lotofacil_lab\.experiments|from lotofacil.experimentos.uso|g' \
  -e 's|from lotofacil_lab\.config|from lotofacil.experimentos.config|g' \
  -e 's|from lotofacil_lab\.main|from lotofacil.experimentos.main|g' \
  -e 's|from lotofacil_lab\b|from lotofacil.experimentos|g' \
  -e 's|import lotofacil_lab\b|import lotofacil.experimentos|g' \
  {} +
```

- [ ] **Passo 3:** Substituir refs ao core antigo

```bash
find src/lotofacil/experimentos -name "*.py" -exec sed -i \
  -e 's|from lotofacil_ml\.config|from lotofacil.infra.config|g' \
  -e 's|from lotofacil_ml\.data|from lotofacil.infra.dados|g' \
  -e 's|from lotofacil_ml\.features|from lotofacil.infra.atributos|g' \
  -e 's|from lotofacil_ml\.models|from lotofacil.infra.modelos|g' \
  -e 's|from lotofacil_ml\.evaluation|from lotofacil.infra.avaliacao|g' \
  -e 's|from core\.models|from lotofacil.dominio.entidades|g' \
  -e 's|from data\.|from lotofacil.infra.dados.|g' \
  -e 's|from strategies\.|from lotofacil.infra.estrategias.|g' \
  -e 's|\bDraw\b|Sorteio|g' \
  -e 's|\bPrediction\b|Predicao|g' \
  {} +
```

(Note: `Draw`/`Prediction` ainda existem como alias mas vamos para o nome final.)

- [ ] **Passo 4:** Atualizar `interface/cli/lab.py`

```python
# ANTES:
from lotofacil_lab.main import app

# DEPOIS:
from lotofacil.experimentos.main import app
```

```bash
sed -i 's|from lotofacil_lab\.main|from lotofacil.experimentos.main|g' src/lotofacil/interface/cli/lab.py
```

- [ ] **Passo 5:** Verificar substituições

```bash
grep -rn "lotofacil_lab\|lotofacil_ml" src/ 2>/dev/null
# Esperado: 0
```

Se aparecer algo em comentários/docstrings, é ok não atualizar.

- [ ] **Passo 6:** Validar imports

```bash
python -c "from lotofacil.experimentos.main import app"
python -c "from lotofacil.interface.cli.lab import app"
```

- [ ] **Passo 7:** Testes

```bash
pytest src/lotofacil/experimentos/tests/
pytest    # suite completa
```

- [ ] **Passo 8:** Smoke

```bash
lotofacil lab --help
lotofacil lab ablacao --n-test 5
lotofacil lab checar-lua --data 2026-05-13
lotofacil lab preencher-clima --ultimos 5
```

- [ ] **Passo 9:** Commit

```bash
git add -A
git commit -m "refactor(experimentos): atualiza imports após move

- lotofacil_lab.* → lotofacil.experimentos.*
- lotofacil_ml.config → lotofacil.infra.config
- core.models (Draw/Prediction) → dominio.entidades (Sorteio/Predicao)
- data/, features/, models/ órfãos → lotofacil.infra.*
- interface/cli/lab.py atualizado

Experimentos agora consomem o core consolidado."
```
