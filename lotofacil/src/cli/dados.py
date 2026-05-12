"""dados subcommands — data update and status."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import typer
from rich.console import Console

app = typer.Typer(help="Gerenciamento de dados — coleta e status.")
console = Console()

_DADOS_DIR = Path(__file__).resolve().parent.parent.parent / "dados"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _to_iso(data_str: str) -> str:
    """DD/MM/YYYY ou YYYY-MM-DD → YYYY-MM-DD. Retorna '' em caso de erro."""
    s = (data_str or "").strip()
    if "/" in s:
        try:
            return datetime.strptime(s, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            return ""
    return s


def _load_draw_index() -> list[tuple[int, str]]:
    """Retorna [(concurso, iso_date), ...] ordenado, lendo dados/concurso_*.json."""
    result = []
    for f in _DADOS_DIR.glob("concurso_*.json"):
        try:
            raw = json.loads(f.read_text())
            c = int(raw["concurso"])
            d = _to_iso(raw.get("data", ""))
            if d:
                result.append((c, d))
        except Exception:
            pass
    return sorted(result)


def _lua_exists(date_iso: str) -> bool:
    return (_DADOS_DIR / "lua" / f"{date_iso}.json").exists()


def _clima_exists(concurso: int) -> bool:
    clima_dir = _DADOS_DIR / "clima"
    return clima_dir.exists() and bool(list(clima_dir.glob(f"clima_concurso{concurso}-*.json")))


# ─── Commands ─────────────────────────────────────────────────────────────────

@app.command()
def atualizar(
    all: bool = typer.Option(False, "--all", help="Carrega todos os draws dos arquivos locais"),
    latest: bool = typer.Option(False, "--latest", help="Busca apenas o sorteio mais recente da API"),
) -> None:
    """Sincroniza concursos e complementa dados de lua e clima concurso a concurso."""
    from lotofacil_ml.data.database import DatabaseManager
    from lotofacil_ml.data.fetcher import LotofacilFetcher

    db = DatabaseManager()
    fetcher = LotofacilFetcher(db)

    if all:
        console.print("[cyan]Carregando todos os dados locais...[/cyan]")
        draws = fetcher.fetch_all_results()
        console.print(f"[green]✓ {len(draws)} concursos importados[/green]")
    elif latest:
        console.print("[cyan]Buscando sorteio mais recente da API...[/cyan]")
        draw = fetcher.fetch_latest()
        if draw:
            console.print(f"[green]✓ Concurso {draw['concurso']} ({draw['data']})[/green]")
        else:
            console.print("[red]Não foi possível buscar o sorteio mais recente.[/red]")
            raise typer.Exit(1)
    else:
        console.print("[cyan]Sincronizando novos sorteios...[/cyan]")
        n = fetcher.sync_new_draws()
        console.print(f"[green]✓ {n} novo(s) sorteio(s) sincronizado(s)[/green]")

    _complementar_todos(console)


# ─── Complementação concurso a concurso ───────────────────────────────────────

def _complementar_todos(console: Console) -> None:
    """Complementa lua e clima para todos os concursos sem esses dados."""
    draws = _load_draw_index()
    if not draws:
        console.print("[yellow]Nenhum dado encontrado em dados/[/yellow]")
        return

    missing_lua = [(c, d) for c, d in draws if not _lua_exists(d)]
    missing_clima = [(c, d) for c, d in draws if not _clima_exists(c)]

    if not missing_lua and not missing_clima:
        console.print("[dim]Lua e clima: completos para todos os concursos.[/dim]")
        return

    console.print(
        f"[dim]Total: {len(draws)} concursos | "
        f"Lua faltando: {len(missing_lua)} | "
        f"Clima faltando: {len(missing_clima)}[/dim]"
    )

    _fill_lua(missing_lua, console)
    _fill_clima(missing_clima, console)


def _fill_lua(missing: list[tuple[int, str]], console: Console) -> None:
    """Calcula fase lunar (offline, pylunar) para cada concurso sem dado."""
    if not missing:
        console.print("[dim]Lua: completa.[/dim]")
        return

    try:
        from lotofacil_lab.data.lunar_loader import compute_lunar_features
    except ImportError:
        console.print("[yellow]⚠ Lua: módulo lotofacil_lab não disponível[/yellow]")
        return

    console.print(f"[cyan]Calculando lua para {len(missing)} concurso(s)...[/cyan]")
    done = 0
    for concurso, date_iso in missing:
        try:
            feats = compute_lunar_features(date_iso)
            phase = float(feats[0])
            if phase < 0.125 or phase >= 0.875:
                fase = "Nova"
            elif phase < 0.375:
                fase = "Crescente"
            elif phase < 0.625:
                fase = "Cheia"
            else:
                fase = "Minguante"
            done += 1
            console.print(f"  Concurso {concurso} ({date_iso}): lua ✓  {fase}")
        except Exception as exc:
            console.print(f"  [yellow]Concurso {concurso}: lua ✗ — {exc}[/yellow]")

    console.print(f"[green]✓ Lua: {done}/{len(missing)} concursos calculados[/green]")


def _fill_clima(missing: list[tuple[int, str]], console: Console) -> None:
    """Busca dados climáticos via Open-Meteo Archive API, em lotes."""
    if not missing:
        console.print("[dim]Clima: completo.[/dim]")
        return

    try:
        from lotofacil_lab.coleta.backfill_clima_archive import (
            _fetch_archive_batch,
            _split_hourly_by_day,
            _processar_resumo_extended,
            _save_climate,
        )
        from lotofacil_lab.config import ARCHIVE_BATCH_DAYS, ARCHIVE_DELAY_SECONDS
    except ImportError:
        console.print("[yellow]⚠ Clima: módulo lotofacil_lab não disponível[/yellow]")
        return

    console.print(f"[cyan]Buscando clima para {len(missing)} concurso(s)...[/cyan]")
    done = 0
    i = 0

    while i < len(missing):
        batch = missing[i : i + ARCHIVE_BATCH_DAYS]
        start_date = batch[0][1]
        end_date = batch[-1][1]

        try:
            resp = _fetch_archive_batch(start_date, end_date)
            daily = _split_hourly_by_day(resp.get("hourly", {}))

            for concurso, iso_date in batch:
                day_h = daily.get(iso_date)
                if day_h:
                    resumo = _processar_resumo_extended(day_h)
                    _save_climate(concurso, iso_date, resumo, day_h)
                    done += 1
                    temp = resumo.get("temp_sorteio")
                    temp_str = f"{temp}°C" if temp is not None else "?°C"
                    precip = resumo.get("precipitacao_sorteio")
                    precip_str = f" / {precip}%" if precip is not None else ""
                    console.print(
                        f"  Concurso {concurso} ({iso_date}): clima ✓  {temp_str}{precip_str}"
                    )
                else:
                    console.print(
                        f"  [dim]Concurso {concurso} ({iso_date}): sem dados no arquivo[/dim]"
                    )

        except Exception as exc:
            console.print(
                f"  [yellow]Lote {start_date} → {end_date}: erro — {exc}[/yellow]"
            )

        i += len(batch)
        if i < len(missing):
            time.sleep(ARCHIVE_DELAY_SECONDS)

    console.print(f"[green]✓ Clima: {done}/{len(missing)} concursos atualizados[/green]")


@app.command()
def status() -> None:
    """Mostra o último concurso, total de draws e período coberto."""
    from lotofacil_ml.data.database import DatabaseManager

    db = DatabaseManager()
    count = db.count_concursos()
    latest = db.get_latest_concurso()

    console.print("[bold]Status do banco de dados[/bold]")
    console.print(f"Total de concursos: [cyan]{count}[/cyan]")
    if latest:
        console.print(
            f"Mais recente: Concurso [cyan]{latest['concurso']}[/cyan] ({latest['data']})"
        )
    else:
        console.print("[yellow]Sem dados. Execute: lotofacil dados atualizar --all[/yellow]")
