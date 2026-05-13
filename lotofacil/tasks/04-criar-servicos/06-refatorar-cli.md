# Task 4.6 — Refatorar `cli/*.py` para usar serviços

**Onda:** 4 — Criar `servicos/`
**Prioridade:** alta
**Tempo estimado:** ~40 min
**Depende de:** 4.5 (todos os serviços criados)

## Objetivo

Refatorar `src/cli/dados.py`, `src/cli/modelo.py`, `src/cli/portfolio.py`, `src/cli/app.py` para serem thin wrappers: apenas parseiam argumentos do Typer, chamam o serviço correspondente, e formatam a saída com rich/console. Sem lógica de orquestração no CLI.

## Descrição técnica

Cada handler Typer fica reduzido a ~10-20 linhas:

```python
@app.command()
def atualizar(escopo: str = typer.Option("novos", "--escopo")):
    """Sincroniza a base local com a API CAIXA."""
    try:
        resultado = atualizar_base(escopo=escopo)
    except LotofacilError as e:
        console.print(f"[red]Erro:[/red] {e}")
        raise typer.Exit(1)

    console.print(Panel(
        f"[green]✅ {resultado.total_novos} sorteios adicionados[/green]\n"
        f"Último concurso: [yellow]{resultado.ultimo_concurso}[/yellow]"
    ))
```

CLI hoje captura exceções genéricas e printa direto — vamos centralizar isso capturando `LotofacilError` no topo de cada comando.

## Arquivos envolvidos

**Modificar:**
- `src/cli/dados.py` — todos os handlers
- `src/cli/modelo.py` — todos os handlers
- `src/cli/portfolio.py` — todos os handlers (lógica grande de geração já foi pra infra+servicos na 4.4)
- `src/cli/app.py` — comando `prever`

**Não tocar:**
- `src/cli/lab.py` — chama `lotofacil_lab.main`; refactor do lab é onda 6

## Dependências

- 4.1 a 4.5 (todos os 11 serviços criados)

## Critérios de aceite

- [ ] Cada handler Typer ≤ 25 linhas
- [ ] `grep -rn "fetcher\|database\|DatabaseManager\|FeatureBuilder\|ConstrutorAtributos" src/cli/` retorna 0 (CLI não importa direto de infra)
- [ ] Todos os comandos CLI continuam funcionando como antes
- [ ] `pytest` passa
- [ ] `lotofacil dados status`, `lotofacil prever`, `lotofacil modelo treinar`, `lotofacil portfolio --jogos 4` funcionam

## Passos detalhados

- [ ] **Passo 1:** Refatorar `src/cli/dados.py`

Substituir a implementação atual (que faz fetch + DB direto) por chamadas a `atualizar_base` e `consultar_status_base`:

```python
"""CLI: comandos `lotofacil dados *`."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from lotofacil.dominio.excecoes import LotofacilError
from lotofacil.servicos.atualizar_base import atualizar_base
from lotofacil.servicos.consultar_status_base import consultar_status_base

app = typer.Typer(help="Coleta e gerenciamento de dados históricos.")
console = Console()


@app.command()
def atualizar(
    escopo: str = typer.Option("novos", "--escopo", help="todos | novos | ultimo"),
) -> None:
    """Sincroniza a base local com a API CAIXA."""
    try:
        resultado = atualizar_base(escopo=escopo)
    except LotofacilError as e:
        console.print(f"[red]Erro:[/red] {e}")
        raise typer.Exit(1)

    console.print(Panel(
        f"[green]✅ {resultado.total_novos} sorteios adicionados[/green]\n"
        f"Último concurso: [yellow]{resultado.ultimo_concurso}[/yellow]",
        title="Atualização concluída",
    ))


@app.command()
def status() -> None:
    """Mostra status da base local."""
    s = consultar_status_base()
    if s.ultimo_concurso is None:
        console.print("[yellow]Base vazia.[/yellow] Execute `lotofacil dados atualizar --escopo todos`.")
        return
    console.print(Panel(
        f"Total: [cyan]{s.total_sorteios}[/cyan] sorteios\n"
        f"Último concurso: [yellow]{s.ultimo_concurso}[/yellow]\n"
        f"Data: {s.ultimo_data}",
        title="Base local",
    ))
```

- [ ] **Passo 2:** Refatorar `src/cli/modelo.py`

```python
"""CLI: comandos `lotofacil modelo *`."""
from __future__ import annotations

import typer
from rich.console import Console

from lotofacil.dominio.excecoes import LotofacilError
from lotofacil.servicos.treinar_modelos import treinar_modelos
from lotofacil.servicos.rodar_backtest import rodar_backtest
from lotofacil.servicos.validar_predicoes import validar_predicoes
from lotofacil.servicos.listar_historico_predicoes import listar_historico_predicoes

app = typer.Typer(help="Treinamento e validação de modelos.")
console = Console()


@app.command()
def treinar() -> None:
    """Treina os modelos (Frequência + Ensemble ML + LSTM)."""
    try:
        resultado = treinar_modelos()
    except LotofacilError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    for nome, caminho in resultado.modelos_salvos.items():
        console.print(f"  [green]✅[/green] {nome:15} → {caminho}")


@app.command()
def backtest(
    estrategia: str = typer.Option("onze_dezenas", "--estrategia"),
    janela: int = typer.Option(50, "--janela"),
) -> None:
    """Executa backtest walk-forward."""
    try:
        r = rodar_backtest(estrategia_nome=estrategia, janela=janela)
    except LotofacilError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    console.print(f"Acerto médio: [cyan]{r.acerto_medio:.2f}[/cyan]")
    console.print(f"Janelas: {len(r.janelas)}")


@app.command()
def validar(concurso: int | None = typer.Option(None)) -> None:
    """Valida predições salvas contra resultados reais."""
    try:
        r = validar_predicoes(concurso=concurso)
    except LotofacilError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    console.print(f"Validadas: {r.total_validadas} | Acerto médio: {r.acerto_medio:.2f}")
    for d in r.detalhes:
        console.print(f"  c{d.concurso} ({d.abordagem}): {d.acertos} acertos")


@app.command()
def historico(limite: int = typer.Option(20)) -> None:
    """Lista histórico de predições."""
    grupos = listar_historico_predicoes(limite=limite)
    for g in grupos:
        console.print(f"[yellow]c{g.concurso}[/yellow]")
        for a in g.abordagens:
            console.print(f"  {a['abordagem']:10} {a['dezenas']}")
```

- [ ] **Passo 3:** Refatorar `src/cli/portfolio.py`

Reduzir de ~400 linhas para ~50 (toda lógica combinatorial está em `infra/geracao` e orquestração em `servicos`):

```python
"""CLI: comandos `lotofacil portfolio`."""
from __future__ import annotations

import typer
from rich.console import Console

from lotofacil.dominio.excecoes import LotofacilError
from lotofacil.servicos.gerar_portfolio import gerar_portfolio
from lotofacil.servicos.validar_portfolio import validar_portfolio

app = typer.Typer(help="Geração e validação de portfólios de jogos.")
console = Console()


@app.callback(invoke_without_command=True)
def gerar(
    ctx: typer.Context,
    jogos: int = typer.Option(5, "--jogos"),
    concurso: int | None = typer.Option(None, "--concurso"),
    abordagem: str = typer.Option("ensemble", "--abordagem"),
) -> None:
    """Gera portfólio de N jogos."""
    if ctx.invoked_subcommand is not None:
        return
    try:
        r = gerar_portfolio(n_jogos=jogos, concurso_alvo=concurso, abordagem=abordagem)
    except LotofacilError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]✅[/green] Portfolio para concurso {r.portfolio.concurso_alvo}: {r.arquivo}")


@app.command("validar")
def validar(concurso: int) -> None:
    """Valida portfólio gerado contra sorteio real."""
    try:
        r = validar_portfolio(concurso=concurso)
    except LotofacilError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    console.print(f"Total prêmio: R$ {r.total_premio:.2f} | ROI: {r.roi:+.2%}")
    for j in r.jogos:
        marker = "🎯" if j.acertos >= 11 else "  "
        console.print(f"  {marker} jogo {j.indice}: {j.acertos} acertos (R$ {j.premio:.2f})")
```

- [ ] **Passo 4:** Refatorar `src/cli/app.py` comando `prever`

```python
@app.command()
def prever(
    abordagem: str = typer.Option("todas", "--abordagem", "-a"),  # já PT
    concurso: int | None = typer.Option(None, "--concurso", "-c"),
) -> None:
    """Prediz 11 números para o próximo concurso."""
    from lotofacil.dominio.excecoes import LotofacilError
    from lotofacil.servicos.gerar_predicao import gerar_predicao

    try:
        pred = gerar_predicao(abordagem=abordagem, concurso_alvo=concurso)
    except LotofacilError as e:
        console.print(f"[red]Erro:[/red] {e}")
        raise typer.Exit(1)

    dezenas_str = "  ".join(f"{n:02d}" for n in sorted(pred.dezenas))
    console.print(Panel(
        f"[bold cyan]Predição — Concurso {pred.concurso_alvo}[/bold cyan]\n\n"
        f"[yellow]{dezenas_str}[/yellow]\n\n"
        f"Abordagem: [dim]{pred.abordagem}[/dim]\n"
        f"Confiança: [green]{pred.confianca_media:.4f}[/green]",
        box=box.DOUBLE_EDGE,
    ))
```

(O alias `--approach` em vez de `--abordagem` será cortado na onda 5; agora já vamos com PT.)

- [ ] **Passo 5:** Verificar que CLI não importa mais infra direto

```bash
grep -rn "from lotofacil\.infra\." src/cli/
# Esperado: 0 — CLI só importa de servicos e dominio
grep -rn "DatabaseManager\|ConstrutorAtributos\|ColetorAPI\|ModeloFrequencia" src/cli/
# 0 esperado
```

- [ ] **Passo 6:** Testes

```bash
pytest
```

- [ ] **Passo 7:** Smoke completo

```bash
lotofacil dados status
lotofacil dados atualizar --escopo ultimo
lotofacil prever
lotofacil prever --abordagem ml
lotofacil portfolio --jogos 4
lotofacil modelo treinar
lotofacil modelo backtest --janela 30
lotofacil modelo historico
lotofacil modelo validar
```

- [ ] **Passo 8:** Commit

```bash
git add src/cli/
git commit -m "refactor(cli): handlers viram thin wrappers chamando serviços

- cli/dados.py: usa atualizar_base, consultar_status_base
- cli/modelo.py: usa treinar_modelos, rodar_backtest, validar_predicoes, listar_historico_predicoes
- cli/portfolio.py: usa gerar_portfolio, validar_portfolio (de ~400 para ~50 linhas)
- cli/app.py prever: usa gerar_predicao (flag --abordagem PT já adotada)

Sem imports diretos de infra. LotofacilError capturado no topo de cada
comando para formatação humanizada.

Última task da onda 4. CLI agora desacoplada da infra."
```
