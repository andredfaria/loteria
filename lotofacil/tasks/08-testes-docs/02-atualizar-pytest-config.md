# Task 8.2 — Atualizar `pytest` config

**Onda:** 8 — Testes + docs
**Prioridade:** média
**Tempo estimado:** ~5 min
**Depende de:** 8.1

## Objetivo

Atualizar `pyproject.toml` `[tool.pytest.ini_options]` para apontar para `testes/`. Simplificar ou remover `conftest.py` da raiz se redundante (pacote agora é importável por nome via `pip install -e .`).

## Arquivos envolvidos

**Modificar:**
- `pyproject.toml`
- `conftest.py` (raiz) — provavelmente remover

## Dependências

- 8.1

## Critérios de aceite

- [ ] `pytest` (sem args) do root descobre tudo em `testes/`
- [ ] `pytest testes/unidade/dominio/` funciona
- [ ] `pytest -k entidade` funciona

## Passos detalhados

- [ ] **Passo 1:** Atualizar `pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["testes"]
# Opcional: também adicionar pythonpath para compatibilidade
# pythonpath = ["src"]
```

Antes provavelmente era `testpaths = ["tests", "src/lotofacil_lab/tests"]`.

- [ ] **Passo 2:** Avaliar `conftest.py` da raiz

Conteúdo atual (verificado na onda 0):

```python
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
```

Após `pip install -e .` (feito na task 5.6), o pacote `lotofacil` é importável por nome. O `conftest.py` faz `sys.path.insert(0, "src")` que torna importável `lotofacil`, `lotofacil_ml`, etc. — mas `lotofacil_ml` não existe mais (deletado na onda 5.7) e `lotofacil` já é importável via `pip install -e .`.

Logo: `conftest.py` é redundante. Deletar:

```bash
git rm conftest.py
```

- [ ] **Passo 3:** Validar

```bash
pytest                           # auto-descobre testes/
pytest testes/unidade/dominio/   # subset
pytest -k "test_entidade"        # por keyword
```

- [ ] **Passo 4:** Verificar que nenhum teste falha por causa do conftest removido

Se algum teste depende de `sys.path` (importa algo sem prefix `lotofacil.`), corrigir:

```bash
grep -rn "^from \(dominio\|infra\|servicos\|interface\|experimentos\)\." testes/
```

Cada resultado deve ser substituído por `from lotofacil.X.Y import Z`.

- [ ] **Passo 5:** Commit

```bash
git add pyproject.toml
git rm conftest.py
git commit -m "test: pytest descobre testes/ — remove conftest.py redundante

- [tool.pytest.ini_options] testpaths = ['testes']
- conftest.py removido: pacote 'lotofacil' já é importável via pip install -e .

`pytest` (sem args) do root agora descobre tudo em testes/."
```
