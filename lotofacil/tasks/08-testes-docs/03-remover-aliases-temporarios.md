# Task 8.3 — Remover aliases temporários `Draw`, `Prediction`

**Onda:** 8 — Testes + docs
**Prioridade:** média
**Tempo estimado:** ~10 min
**Depende de:** 8.2

## Objetivo

Remover os aliases `Draw = Sorteio` e `Prediction = Predicao` adicionados na onda 2 task 2 para compatibilidade durante a migração. Garantir que nenhum código ainda usa os nomes antigos.

## Arquivos envolvidos

**Modificar:**
- `src/lotofacil/dominio/entidades.py` — remover últimas linhas com aliases

**Verificar (e corrigir se preciso):**
- Todo o código em `src/lotofacil/` e `testes/`

## Dependências

- 8.2

## Critérios de aceite

- [ ] `grep -rn "\bDraw\b\|\bPrediction\b" src/lotofacil/ testes/` retorna 0 (apenas docstrings/comentários permitidos)
- [ ] `from lotofacil.dominio.entidades import Draw` levanta `ImportError`
- [ ] `pytest` passa

## Passos detalhados

- [ ] **Passo 1:** Auditar usos restantes

```bash
grep -rn "\bDraw\b" src/lotofacil/ testes/ | grep -v __pycache__
grep -rn "\bPrediction\b" src/lotofacil/ testes/ | grep -v __pycache__
```

Esperado: idealmente 0. Se houver, são usos remanescentes que precisam virar `Sorteio` e `Predicao`:

```bash
# Substituir em todos os arquivos
find src/lotofacil testes -name "*.py" -exec sed -i \
  -e 's|\bDraw\b|Sorteio|g' \
  -e 's|\bPrediction\b|Predicao|g' \
  {} +
```

> **Cuidado:** `\bDraw\b` pode bater em nomes mais longos. Conferir manualmente:
>
> ```bash
> grep -rn "Sorteio" src/lotofacil/dominio/entidades.py
> # Esperado: classe Sorteio, sem "Sorteioble" ou erros
> ```

- [ ] **Passo 2:** Remover aliases em `dominio/entidades.py`

Localizar e deletar:

```python
# Aliases temporários — código antigo (cli/app.py, lotofacil_ml/, dashboard/)
# importa Draw e Prediction. Estes aliases permitem migração gradual.
# REMOVER NA ONDA 8 task 03 (depois que todos os usos migrarem).
Draw = Sorteio
Prediction = Predicao
```

- [ ] **Passo 3:** Validar imports

```bash
python -c "from lotofacil.dominio.entidades import Sorteio, Predicao, Portfolio; print('OK')"
python -c "from lotofacil.dominio.entidades import Draw" 2>&1 | head -3
# Esperado: ImportError
```

- [ ] **Passo 4:** Rodar testes

```bash
pytest
```

Se algum teste falha por causa de `Draw`/`Prediction`, atualizar para `Sorteio`/`Predicao`.

- [ ] **Passo 5:** Atualizar `test_entidades.py` se ainda tem o test de aliases

```python
# Em testes/unidade/dominio/test_entidades.py:
# Apagar a classe TestAliasesTemporarios
```

- [ ] **Passo 6:** Commit

```bash
git add -A
git commit -m "refactor(dominio): remove aliases temporários Draw/Prediction

Aliases adicionados na onda 2 (task 2) para permitir migração gradual.
Todos os usos foram convertidos para Sorteio/Predicao ao longo das
ondas 3-7. Limpeza final."
```
