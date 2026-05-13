# Task 5.1 — Mover `src/cli/` → `interface/cli/`

**Onda:** 5 — Mover interface + renomear CLI
**Prioridade:** alta
**Tempo estimado:** ~15 min
**Depende de:** 4.6

## Objetivo

Mover a CLI inteira de `src/cli/` para `src/lotofacil/interface/cli/`. Esta task **não** muda nomes de comandos (isso é a task 5.5) nem flags (task 5.4) — só localização física.

## Arquivos envolvidos

**Mover (git mv):**

| De | Para |
|---|---|
| `src/cli/__init__.py` | `src/lotofacil/interface/cli/__init__.py` |
| `src/cli/app.py` | `src/lotofacil/interface/cli/app.py` |
| `src/cli/dados.py` | `src/lotofacil/interface/cli/dados.py` |
| `src/cli/modelo.py` | `src/lotofacil/interface/cli/modelo.py` |
| `src/cli/portfolio.py` | `src/lotofacil/interface/cli/portfolio.py` |
| `src/cli/lab.py` | `src/lotofacil/interface/cli/lab.py` |

**Modificar:**
- `src/lotofacil/interface/cli/app.py`: atualizar imports internos (`from cli.X` → `from lotofacil.interface.cli.X`)
- `src/lotofacil/interface/cli/app.py`: remover o `sys.path.insert(0, _SRC)` (não precisa mais — pacote registrado)

**Não atualizar agora:** `pyproject.toml` (task 5.6)

## Dependências

- 4.6

## Critérios de aceite

- [ ] `find src/cli 2>&1 | grep -i "no such"`
- [ ] `find src/lotofacil/interface/cli -name "*.py" | wc -l` retorna 6
- [ ] `python -c "from lotofacil.interface.cli.app import app"` funciona
- [ ] Após `pip install -e .` (task 5.6 ainda não rodou), o comando `lotofacil` antigo ainda funciona via `src.cli.app:app` enquanto pyproject não muda — **mas** `python -c "from cli.app import app"` quebra. Smoke confirma.

## Passos detalhados

- [ ] **Passo 1:** Mover arquivos com git mv

```bash
git mv src/cli/__init__.py src/lotofacil/interface/cli/__init__.py
git mv src/cli/app.py src/lotofacil/interface/cli/app.py
git mv src/cli/dados.py src/lotofacil/interface/cli/dados.py
git mv src/cli/modelo.py src/lotofacil/interface/cli/modelo.py
git mv src/cli/portfolio.py src/lotofacil/interface/cli/portfolio.py
git mv src/cli/lab.py src/lotofacil/interface/cli/lab.py

# Deletar pasta vazia
rmdir src/cli 2>/dev/null
```

- [ ] **Passo 2:** Atualizar `app.py` — remover sys.path manipulation, ajustar `_register_subapps`

```python
# ANTES (no topo de app.py):
_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# DEPOIS: remover essas linhas (pacote agora é nomeado)
```

E no `_register_subapps`:

```python
def _register_subapps() -> None:
    from lotofacil.interface.cli.dados import app as dados_app
    from lotofacil.interface.cli.modelo import app as modelo_app
    from lotofacil.interface.cli.portfolio import app as portfolio_app
    from lotofacil.interface.cli.lab import app as lab_app

    app.add_typer(dados_app, name="dados")
    app.add_typer(modelo_app, name="modelo")
    app.add_typer(portfolio_app, name="portfolio")
    app.add_typer(lab_app, name="lab", help="Pipeline experimental — clima, lua, ablação.")
```

(Substitui `from cli.dados import app` por `from lotofacil.interface.cli.dados import app`, etc.)

- [ ] **Passo 3:** Validar imports

```bash
python -c "from lotofacil.interface.cli.app import app; print('OK')"
python -c "from lotofacil.interface.cli.dados import app as a; print('OK')"
python -c "from lotofacil.interface.cli.modelo import app as a; print('OK')"
python -c "from lotofacil.interface.cli.portfolio import app as a; print('OK')"
python -c "from lotofacil.interface.cli.lab import app as a; print('OK')"
```

- [ ] **Passo 4:** Testes

```bash
pytest
```

- [ ] **Passo 5:** Smoke

O comando `lotofacil` registrado em pyproject.toml ainda aponta para `src.cli.app:app`, que agora não existe. Ele vai falhar até a task 5.6 atualizar.

Para testar nesta task, usar invocação direta:

```bash
python -m lotofacil.interface.cli.app dados status
python -m lotofacil.interface.cli.app prever
```

- [ ] **Passo 6:** Commit

```bash
git add -A
git commit -m "refactor(interface): move src/cli → interface/cli

Move físico apenas — sem mudança de comandos ou flags.

- Imports internos ajustados para 'from lotofacil.interface.cli.X'
- sys.path.insert removido (pacote agora é importável por nome)

Comando 'lotofacil' (registrado em pyproject) só voltará a funcionar
após task 5.6 (atualizar pyproject.toml). Por ora testar via:
  python -m lotofacil.interface.cli.app <cmd>"
```
