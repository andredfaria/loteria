# Task 5.2 — Mover `src/dashboard/` → `interface/painel/`

**Onda:** 5 — Mover interface + renomear CLI
**Prioridade:** alta
**Tempo estimado:** ~20 min
**Depende de:** 5.1

## Objetivo

Mover o Flask app + frontend de `src/dashboard/` para `src/lotofacil/interface/painel/`. Ajustar `Flask(static_folder=...)`. Renomear `server.py` → `servidor.py`, `commands.py` → `comandos.py`.

## Arquivos envolvidos

**Mover:**

| De | Para |
|---|---|
| `src/dashboard/__init__.py` | `src/lotofacil/interface/painel/__init__.py` |
| `src/dashboard/server.py` | `src/lotofacil/interface/painel/servidor.py` |
| `src/dashboard/commands.py` | `src/lotofacil/interface/painel/comandos.py` |
| `src/dashboard/static/dashboard.html` | `src/lotofacil/interface/painel/static/painel.html` |
| (outros static, se houver) | mantém estrutura |
| `src/dashboard/tests/test_server.py` | `src/lotofacil/interface/painel/tests/test_servidor.py` |

**Renames de funções/classes:**

| Antes | Depois |
|---|---|
| `_run_command` | `_executar_comando` |
| `_last_concurso_info` | `_info_ultimo_concurso` |
| `_list_game_files` | `_listar_jogos` (será depreciada na task 5.3 — substituída por serviço) |
| `_scan_models` | `_escanear_modelos` (depreciada na task 5.3) |
| `_strip_ansi` | mantém |
| classe principal Flask app | mantém |

**Modificar:**
- `Flask(static_folder=...)` em `servidor.py` — apontar para nova localização
- Imports internos

## Dependências

- 5.1

## Critérios de aceite

- [ ] `find src/dashboard 2>&1 | grep -i "no such"`
- [ ] `python -c "from lotofacil.interface.painel.servidor import app"` funciona
- [ ] Servidor sobe com `python -m lotofacil.interface.painel.servidor`
- [ ] `curl localhost:5000/` retorna o HTML do painel
- [ ] `pytest src/lotofacil/interface/painel/tests/` passa

## Passos detalhados

- [ ] **Passo 1:** Mover arquivos

```bash
git mv src/dashboard/__init__.py src/lotofacil/interface/painel/__init__.py
git mv src/dashboard/server.py src/lotofacil/interface/painel/servidor.py
git mv src/dashboard/commands.py src/lotofacil/interface/painel/comandos.py

# Estrutura static
mkdir -p src/lotofacil/interface/painel/static
git mv src/dashboard/static/dashboard.html src/lotofacil/interface/painel/static/painel.html
# Outros assets se houver
git mv src/dashboard/static/*.css src/lotofacil/interface/painel/static/ 2>/dev/null
git mv src/dashboard/static/*.js src/lotofacil/interface/painel/static/ 2>/dev/null

# Tests
mkdir -p src/lotofacil/interface/painel/tests
git mv src/dashboard/tests/__init__.py src/lotofacil/interface/painel/tests/__init__.py 2>/dev/null
git mv src/dashboard/tests/test_server.py src/lotofacil/interface/painel/tests/test_servidor.py

# Limpar
[ -d src/dashboard/static ] && rmdir src/dashboard/static
[ -d src/dashboard/tests ] && rmdir src/dashboard/tests
[ -d src/dashboard ] && rmdir src/dashboard
```

- [ ] **Passo 2:** Atualizar `servidor.py` — Flask static_folder + nome do HTML

```python
# Substituir:
app = Flask(__name__, static_folder="static", static_url_path="/static")

# Por:
from pathlib import Path
_STATIC = Path(__file__).parent / "static"
app = Flask(__name__, static_folder=str(_STATIC), static_url_path="/static")

# E onde lê "dashboard.html":
# return send_from_directory(_STATIC, "dashboard.html")
# Substituir por:
return send_from_directory(_STATIC, "painel.html")
```

- [ ] **Passo 3:** Renomear funções helper

```bash
sed -i \
  -e 's/\b_run_command\b/_executar_comando/g' \
  -e 's/\b_last_concurso_info\b/_info_ultimo_concurso/g' \
  -e 's/\b_list_game_files\b/_listar_jogos/g' \
  -e 's/\b_scan_models\b/_escanear_modelos/g' \
  src/lotofacil/interface/painel/servidor.py src/lotofacil/interface/painel/tests/test_servidor.py
```

- [ ] **Passo 4:** Atualizar imports em `servidor.py`

```bash
sed -i \
  -e 's|from dashboard\.|from lotofacil.interface.painel.|g' \
  -e 's|from \.commands|from .comandos|g' \
  src/lotofacil/interface/painel/servidor.py
```

- [ ] **Passo 5:** Atualizar test_servidor.py

```bash
sed -i \
  -e 's|from dashboard\.server|from lotofacil.interface.painel.servidor|g' \
  -e 's|from \.\.server|from lotofacil.interface.painel.servidor|g' \
  src/lotofacil/interface/painel/tests/test_servidor.py
```

- [ ] **Passo 6:** Atualizar comando `painel` (a ser criado em `interface/cli/app.py` na task 5.5)

Por ora não cria, mas anotar: o `lotofacil dashboard` antigo (mencionado em PRD-dashboard) vira `lotofacil painel`. Implementação como comando Typer:

```python
@app.command()
def painel(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(5000, "--port"),
) -> None:
    """Inicia o painel web."""
    from lotofacil.interface.painel.servidor import app as flask_app
    flask_app.run(host=host, port=port)
```

(Será adicionado na task 5.5 — renomeacao de comandos.)

- [ ] **Passo 7:** Validar imports

```bash
python -c "from lotofacil.interface.painel.servidor import app; print('OK')"
```

- [ ] **Passo 8:** Smoke do servidor

```bash
python -m lotofacil.interface.painel.servidor &
PID=$!
sleep 2
curl -s localhost:5000/ | head -20    # deve mostrar HTML
curl -s localhost:5000/api/status | head -5   # JSON
kill $PID
```

- [ ] **Passo 9:** Testes

```bash
pytest src/lotofacil/interface/painel/tests/
pytest    # suite completa
```

- [ ] **Passo 10:** Commit

```bash
git add -A
git commit -m "refactor(interface): move src/dashboard → interface/painel

Renames:
- server.py → servidor.py
- commands.py → comandos.py
- static/dashboard.html → static/painel.html
- _run_command → _executar_comando
- _last_concurso_info → _info_ultimo_concurso
- _list_game_files → _listar_jogos
- _scan_models → _escanear_modelos

Flask static_folder apontado para nova localização."
```
