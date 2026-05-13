# Task 5.5 — Renomear comandos PT + adicionar `painel`

**Onda:** 5 — Mover interface + renomear CLI
**Prioridade:** alta
**Tempo estimado:** ~20 min
**Depende de:** 5.4

## Objetivo

Renomear comandos da CLI para PT:
- `lab ablation` → `lab ablacao`
- `lab lunar-check` → `lab checar-lua`
- `lab backfill-clima` → `lab preencher-clima`
- `lab compare` → `lab comparar`
- (futuro) `dashboard` → `painel` (adicionar agora)

Adicionar novo comando `lotofacil painel` que sobe o servidor Flask.

## Arquivos envolvidos

**Modificar:**
- `src/lotofacil/interface/cli/lab.py` (que delega para `lotofacil_lab.main`)
- Eventualmente `src/lotofacil_lab/main.py` para renomear os comandos internos (lab será movido inteiro na onda 6 — mas o renome dos comandos é cosmético aqui)

**Criar:**
- Comando `painel` em `src/lotofacil/interface/cli/app.py`

## Dependências

- 5.4

## Critérios de aceite

- [ ] `lotofacil lab ablacao --n-test 10` funciona; `lotofacil lab ablation` falha
- [ ] `lotofacil lab checar-lua --data 2026-05-13` funciona; `lab lunar-check` falha
- [ ] `lotofacil lab preencher-clima --ultimos 5` funciona
- [ ] `lotofacil lab comparar` funciona
- [ ] `lotofacil painel --host 0.0.0.0 --port 5000` sobe o servidor

## Passos detalhados

- [ ] **Passo 1:** Inspecionar `lotofacil_lab/main.py`

```bash
grep -n "@app.command\|@app.callback" src/lotofacil_lab/main.py
```

Identificar os comandos atuais (ablation, lunar-check, backfill-clima, compare, treinar, etc.).

- [ ] **Passo 2:** Renomear comandos em `lotofacil_lab/main.py`

Cada `@app.command("ablation")` vira `@app.command("ablacao")` (ou apenas usar o nome do método). Exemplo:

```python
# ANTES:
@app.command()
def ablation(n_test: int = ...):
    ...

# DEPOIS:
@app.command("ablacao")
def ablacao(n_test: int = ...):
    ...
```

Ou usar o nome explícito no decorator:

```python
@app.command(name="ablacao")
def rodar_ablation(n_test: int = ...):
    ...
```

Aplicar para:
- `ablation` → `ablacao`
- `lunar_check` (ou `lunar-check`) → `checar_lua` (ou `checar-lua`)
- `backfill_clima` (ou `backfill-clima`) → `preencher_clima` (ou `preencher-clima`)
- `compare` → `comparar`
- `treinar` (já PT — mantém)

> **Atenção:** Typer permite hyphen no nome do comando via `name="checar-lua"`. Manter hyphens é convenção.

- [ ] **Passo 3:** Adicionar `painel` em `interface/cli/app.py`

```python
@app.command()
def painel(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(5000, "--port"),
) -> None:
    """Inicia o painel web."""
    from lotofacil.interface.painel.servidor import app as flask_app
    console.print(f"[green]Iniciando painel em http://{host}:{port}[/green]")
    flask_app.run(host=host, port=port)
```

- [ ] **Passo 4:** Validar

```bash
python -m lotofacil.interface.cli.app lab --help
# Esperado: ablacao, checar-lua, preencher-clima, comparar, treinar

python -m lotofacil.interface.cli.app --help
# Esperado: prever, dados, modelo, portfolio, lab, painel
```

- [ ] **Passo 5:** Testes

```bash
pytest
```

- [ ] **Passo 6:** Smoke

```bash
python -m lotofacil.interface.cli.app lab ablacao --n-test 10
# Funciona

python -m lotofacil.interface.cli.app lab checar-lua --data 2026-05-13
# Funciona

python -m lotofacil.interface.cli.app lab ablation 2>&1 | head -5
# Esperado: "No such command 'ablation'"

# Painel
python -m lotofacil.interface.cli.app painel &
PID=$!
sleep 2
curl -s localhost:5000/api/status | head
kill $PID
```

- [ ] **Passo 7:** Commit

```bash
git add -A
git commit -m "refactor(cli): renomeia comandos PT + adiciona 'painel'

Lab:
- lab ablation → lab ablacao
- lab lunar-check → lab checar-lua
- lab backfill-clima → lab preencher-clima
- lab compare → lab comparar
- lab treinar (já PT)

Novo:
- lotofacil painel (substitui ideia de 'lotofacil dashboard' do PRD-dashboard)

Corte limpo: comandos antigos não funcionam mais."
```
