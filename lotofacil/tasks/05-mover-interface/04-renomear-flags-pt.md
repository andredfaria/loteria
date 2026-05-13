# Task 5.4 — Renomear flags PT (corte limpo, sem shim)

**Onda:** 5 — Mover interface + renomear CLI
**Prioridade:** alta
**Tempo estimado:** ~15 min
**Depende de:** 5.3

## Objetivo

Renomear flags da CLI para PT. Corte limpo — flags antigas deixam de funcionar (decisão da Seção 5.3 do spec).

## Mudanças

| Atual | Novo | Comando afetado |
|---|---|---|
| `--all` | `--escopo todos` | `dados atualizar` (sub-opção dentro de `--escopo`) |
| `--latest` | `--escopo ultimo` | `dados atualizar` |
| `--approach` | `--abordagem` | `prever` |
| (interno) `approach` | `abordagem` | passada para `gerar_predicao()` |

Flags já PT que ficam: `--concurso`, `--jogos`, `--janela`, `--host`, `--port`.

Loanwords como `--escopo`, `--abordagem` são as escolhidas.

## Arquivos envolvidos

**Modificar:**
- `src/lotofacil/interface/cli/app.py` (comando `prever`)
- `src/lotofacil/interface/cli/dados.py` (comando `atualizar`)
- `src/lotofacil/interface/cli/modelo.py` (verificar se há flags EN restantes)
- `src/lotofacil/interface/cli/portfolio.py` (verificar)

## Dependências

- 5.3

## Critérios de aceite

- [ ] `lotofacil dados atualizar --escopo todos` funciona
- [ ] `lotofacil dados atualizar --all` **FALHA** com mensagem clara do Typer
- [ ] `lotofacil prever --abordagem ml` funciona
- [ ] `lotofacil prever --approach ml` **FALHA**
- [ ] `pytest` passa

## Passos detalhados

- [ ] **Passo 1:** Inventariar flags EN restantes

```bash
grep -rn "typer.Option.*--" src/lotofacil/interface/cli/ | grep -E "all|latest|approach|jogos|concurso|host|port"
```

Anotar flags EN que ainda precisam mudar.

- [ ] **Passo 2:** Atualizar `dados.py` — comando `atualizar`

```python
# ANTES (provavelmente):
@app.command()
def atualizar(
    all: bool = typer.Option(False, "--all"),
    latest: bool = typer.Option(False, "--latest"),
    sync: bool = typer.Option(False, "--sync"),
):
    if all:
        atualizar_base(escopo="todos")
    elif latest:
        atualizar_base(escopo="ultimo")
    ...

# DEPOIS:
@app.command()
def atualizar(
    escopo: str = typer.Option("novos", "--escopo", help="todos | novos | ultimo"),
):
    """Sincroniza a base local com a API CAIXA."""
    resultado = atualizar_base(escopo=escopo)
    ...
```

(Confirma o que ficou após task 4.6 — esta já pode ter mudado para `--escopo`.)

- [ ] **Passo 3:** Atualizar `app.py` — comando `prever`

```python
@app.command()
def prever(
    abordagem: str = typer.Option("todas", "--abordagem", "-a"),  # era --approach
    concurso: int | None = typer.Option(None, "--concurso", "-c"),
):
    """Prediz 11 números para o próximo concurso."""
    ...
```

E na chamada do serviço:

```python
pred = gerar_predicao(abordagem=abordagem, ...)  # parâmetro PT
```

- [ ] **Passo 4:** Conferir `modelo.py` e `portfolio.py` — flags EN remanescentes?

```bash
grep -n "typer.Option" src/lotofacil/interface/cli/modelo.py src/lotofacil/interface/cli/portfolio.py
```

Se houver `--all`, `--approach`, etc., renomear. Provavelmente já estão limpos pós-4.6.

- [ ] **Passo 5:** Atualizar serviços internamente — parâmetro `approach` → `abordagem`

Se algum serviço ainda usa `approach=` como parâmetro (ex.: `gerar_predicao(approach="ml")`), renomear para `abordagem=`. Já deveria estar em PT desde a onda 4.

```bash
grep -rn "def .*approach\b" src/lotofacil/
```

Esperado: 0. Senão, renomear.

- [ ] **Passo 6:** Validar

```bash
python -m lotofacil.interface.cli.app dados atualizar --help
# Esperado: --escopo (não --all, --latest)

python -m lotofacil.interface.cli.app prever --help
# Esperado: --abordagem (não --approach)
```

- [ ] **Passo 7:** Testes

```bash
pytest
```

- [ ] **Passo 8:** Smoke

```bash
python -m lotofacil.interface.cli.app dados atualizar --escopo novos
python -m lotofacil.interface.cli.app prever --abordagem ml
python -m lotofacil.interface.cli.app prever --abordagem todas
```

Esperado: comandos executam sem erro.

```bash
python -m lotofacil.interface.cli.app dados atualizar --all 2>&1 | head -5
# Esperado: "No such option: --all" (Typer)
```

- [ ] **Passo 9:** Commit

```bash
git add -A
git commit -m "refactor(cli): renomeia flags para PT (corte limpo, sem shim)

- dados atualizar: --all|--latest → --escopo {todos,novos,ultimo}
- prever: --approach → --abordagem
- parâmetro interno approach= → abordagem= nos serviços

Decisão da Seção 5.3 do spec: scripts usando flags antigas quebram.
Sem deprecation warning (projeto de uso pessoal — corte vale o atrito)."
```
