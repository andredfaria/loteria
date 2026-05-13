# Task 5.6 — Atualizar `pyproject.toml` (entry point + packages.find)

**Onda:** 5 — Mover interface + renomear CLI
**Prioridade:** alta
**Tempo estimado:** ~10 min
**Depende de:** 5.5

## Objetivo

Atualizar `pyproject.toml` para refletir a nova layout do pacote (`src/lotofacil/`) e o novo entry point da CLI. Re-instalar o pacote em modo desenvolvimento.

## Mudanças

```toml
# pyproject.toml

[project.scripts]
# ANTES:
# lotofacil = "src.cli.app:app"
# DEPOIS:
lotofacil = "lotofacil.interface.cli.app:app"

[tool.setuptools.packages.find]
# ANTES:
# include = ["src*"]
# DEPOIS:
where = ["src"]
include = ["lotofacil*"]
```

## Arquivos envolvidos

**Modificar:**
- `pyproject.toml`

**Validar:**
- `conftest.py` (raiz) — pode continuar adicionando `src/` ao sys.path, mas com `pip install -e .` feito, deve ser redundante. Não tocar agora (onda 8 task 2 reavalia).

## Dependências

- 5.5

## Critérios de aceite

- [ ] `pip install -e .` executa sem erro
- [ ] `which lotofacil` aponta para o binário no venv
- [ ] `lotofacil --help` mostra comandos PT
- [ ] `python -c "import lotofacil; print(lotofacil.__file__)"` aponta para `src/lotofacil/__init__.py`

## Passos detalhados

- [ ] **Passo 1:** Editar `pyproject.toml`

Substituir:

```toml
[project.scripts]
lotofacil = "src.cli.app:app"
```

por:

```toml
[project.scripts]
lotofacil = "lotofacil.interface.cli.app:app"
```

E substituir:

```toml
[tool.setuptools.packages.find]
include = ["src*"]
```

por:

```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["lotofacil*"]
```

- [ ] **Passo 2:** Reinstalar o pacote

```bash
pip install -e .
```

Esperado: instalação sem erro. Pode aparecer warnings de deprecation do setuptools — OK.

- [ ] **Passo 3:** Validar entry point

```bash
which lotofacil
# Esperado: caminho dentro do venv

lotofacil --help
# Esperado: lista de comandos PT (dados, modelo, portfolio, lab, prever, painel)

lotofacil --version 2>/dev/null
# Pode não suportar; ignorar
```

- [ ] **Passo 4:** Validar import canônico

```bash
python -c "import lotofacil; print(lotofacil.__file__)"
# Esperado: .../src/lotofacil/__init__.py
```

- [ ] **Passo 5:** Smoke completo

```bash
lotofacil dados status
lotofacil prever --abordagem ml
lotofacil portfolio --jogos 3
lotofacil lab ablacao --n-test 5
```

- [ ] **Passo 6:** Testes

```bash
pytest
```

- [ ] **Passo 7:** Commit

```bash
git add pyproject.toml
git commit -m "build: atualiza pyproject.toml para nova layout

- [project.scripts] lotofacil = 'lotofacil.interface.cli.app:app'
- [tool.setuptools.packages.find] where = ['src'], include = ['lotofacil*']

Após este commit, 'pip install -e .' é obrigatório para o comando
'lotofacil' funcionar. README + CLAUDE.md atualizam na onda 8."
```
