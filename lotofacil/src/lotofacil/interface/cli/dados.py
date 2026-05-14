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

import requests
import typer
from rich.console import Console

app = typer.Typer(help="Gerenciamento de dados — coleta e status.")
console = Console()

_DADOS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "dados"
_API_BASE  = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"


# ─── Helpers de arquivo ────────────────────────────────────────────────────────

def _to_iso(data_str: str) -> str:
    """DD/MM/YYYY ou YYYY-MM-DD → YYYY-MM-DD. Retorna '' em erro."""
    s = (data_str or "").strip()
    if "/" in s:
        try:
            return datetime.strptime(s, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            return ""
    return s


def _load_draw_index() -> list[tuple[int, str]]:
    """Lê dados/concurso_*.json → [(concurso, iso_date), ...] ordenado."""
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


def _json_exists(concurso: int) -> bool:
    return (_DADOS_DIR / f"concurso_{concurso}.json").exists()


def _lua_exists(date_iso: str) -> bool:
    return (_DADOS_DIR / "lua" / f"{date_iso}.json").exists()


def _clima_exists(concurso: int) -> bool:
    d = _DADOS_DIR / "clima"
    return d.exists() and bool(list(d.glob(f"clima_concurso{concurso}-*.json")))


# ─── API de sorteios ──────────────────────────────────────────────────────────

def _fetch_draw(endpoint: str) -> tuple[int, str, dict] | None:
    """Busca um sorteio da API. endpoint = número ou 'latest'.
    Retorna (concurso, iso_date, raw_dict) ou None.
    """
    url = f"{_API_BASE}/{endpoint}"
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=20,
                             headers={"User-Agent": "lotofacil-dados/1.0"})
            r.raise_for_status()
            raw = r.json()
            concurso = int(raw["concurso"])
            dezenas  = [int(n) for n in raw["dezenas"]]
            date_iso = _to_iso(raw.get("data", ""))
            if len(dezenas) == 15 and date_iso:
                return concurso, date_iso, raw
        except Exception:
            if attempt < 2:
                time.sleep(2)
    return None


def _save_draw_json(concurso: int, raw: dict) -> None:
    """Salva dados/concurso_N.json (não sobrescreve se já existir)."""
    _DADOS_DIR.mkdir(parents=True, exist_ok=True)
    path = _DADOS_DIR / f"concurso_{concurso}.json"
    if not path.exists():
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=2))


# ─── Commands ─────────────────────────────────────────────────────────────────

@app.command()
def atualizar(
    escopo: str = typer.Option("novos", "--escopo", "-e", help="Escopo: novos, todos, ultimo"),
) -> None:
    """Busca dados, lua e clima de cada sorteio, concurso a concurso."""

    # ── Sincronizar dados de sorteio ──────────────────────────────────────────
    if escopo == "ultimo":
        console.print("[cyan]Buscando último sorteio da API...[/cyan]")
        result = _fetch_draw("latest")
        if not result:
            console.print("[red]✗ Não foi possível contatar a API.[/red]")
            raise typer.Exit(1)
        concurso, date_iso, raw = result
        _save_draw_json(concurso, raw)
        console.print(f"Concurso {concurso} ({date_iso}): dados ✓")

    else:
        # Descobre quantos concursos existem localmente
        draws_local = _load_draw_index()
        local_max   = draws_local[-1][0] if draws_local else 0

        # Busca o último da API
        console.print("[cyan]Verificando concursos novos na API...[/cyan]")
        latest_result = _fetch_draw("latest")
        if not latest_result:
            console.print("[red]✗ Não foi possível contatar a API.[/red]")
            raise typer.Exit(1)
        api_max, _, _ = latest_result

        # Determina qual intervalo buscar
        if escopo == "todos":
            start = 1
            console.print(f"[cyan]Verificando concursos 1 → {api_max}...[/cyan]")
        else:
            start = local_max + 1

        fetched = 0
        for num in range(start, api_max + 1):
            if _json_exists(num):
                continue           # já temos, pula
            result = _fetch_draw(num)
            if result:
                c, d, raw = result
                _save_draw_json(c, raw)
                console.print(f"Concurso {c} ({d}): dados ✓")
                fetched += 1
            else:
                console.print(f"  [yellow]Concurso {num}: não encontrado na API[/yellow]")

        if fetched:
            console.print(f"[green]✓ {fetched} concurso(s) baixado(s)[/green]")
        else:
            console.print("[dim]Dados: já atualizados[/dim]")

    # ── Recarrega índice (inclui novos) ───────────────────────────────────────
    draws = _load_draw_index()

    # ── Lua e clima: preenche o que falta ─────────────────────────────────────
    miss_lua   = [(c, d) for c, d in draws if not _lua_exists(d)]
    miss_clima = [(c, d) for c, d in draws if not _clima_exists(c)]

    if not miss_lua and not miss_clima:
        console.print("[dim]Lua e clima: completos para todos os concursos.[/dim]")
        return

    console.print(
        f"[dim]Total: {len(draws)} concursos | "
        f"Lua faltando: {len(miss_lua)} | "
        f"Clima faltando: {len(miss_clima)}[/dim]"
    )
    _sync_lua(miss_lua, console)
    _sync_clima(miss_clima, console)


# ─── Lua ──────────────────────────────────────────────────────────────────────

def _sync_lua(missing: list[tuple[int, str]], console: Console) -> None:
    """Calcula fase lunar (pylunar, offline) para cada data sem cache."""
    if not missing:
        console.print("[dim]Lua: completa.[/dim]")
        return

    try:
        from lotofacil.experimentos.data.lunar_loader import compute_lunar_features
    except ImportError:
        console.print("[yellow]⚠ Lua: lotofacil_lab não disponível[/yellow]")
        return

    lua_dir = _DADOS_DIR / "lua"
    lua_dir.mkdir(parents=True, exist_ok=True)

    _FEATURE_NAMES = ["phase", "phase_sin", "phase_cos", "illumination", "age_norm", "is_new", "is_full"]

    console.print(f"[cyan]Calculando lua para {len(missing)} concurso(s)...[/cyan]")
    done = 0
    for concurso, date_iso in missing:
        try:
            feats = compute_lunar_features(date_iso)
            phase = float(feats[0])
            if   phase < 0.125 or phase >= 0.875: fase = "Nova"
            elif phase < 0.375:                   fase = "Crescente"
            elif phase < 0.625:                   fase = "Cheia"
            else:                                 fase = "Minguante"

            features = {name: float(feats[i]) for i, name in enumerate(_FEATURE_NAMES)}
            (lua_dir / f"{date_iso}.json").write_text(
                json.dumps({"date": date_iso, "features": features}, indent=2, ensure_ascii=False)
            )
            done += 1
            console.print(f"  Concurso {concurso} ({date_iso}): lua ✓  {fase}")
        except Exception as exc:
            console.print(f"  [yellow]Concurso {concurso}: lua ✗ — {exc}[/yellow]")

    console.print(f"[green]✓ Lua: {done}/{len(missing)} calculados[/green]")


# ─── Clima ────────────────────────────────────────────────────────────────────

def _sync_clima(missing: list[tuple[int, str]], console: Console) -> None:
    """Busca clima via Open-Meteo Archive em lotes de 30, reporta por concurso."""
    if not missing:
        console.print("[dim]Clima: completo.[/dim]")
        return

    try:
        from lotofacil.experimentos.coleta.backfill_clima_archive import (
            _fetch_archive_batch,
            _split_hourly_by_day,
            _processar_resumo_extended,
            _save_climate,
        )
        from lotofacil.experimentos.config import ARCHIVE_BATCH_DAYS, ARCHIVE_DELAY_SECONDS
    except ImportError:
        console.print("[yellow]⚠ Clima: lotofacil_lab não disponível[/yellow]")
        return

    console.print(f"[cyan]Buscando clima para {len(missing)} concurso(s)...[/cyan]")
    done = 0
    i = 0

    while i < len(missing):
        batch       = missing[i : i + ARCHIVE_BATCH_DAYS]
        start_date  = batch[0][1]
        end_date    = batch[-1][1]

        try:
            resp  = _fetch_archive_batch(start_date, end_date)
            daily = _split_hourly_by_day(resp.get("hourly", {}))

            for concurso, iso_date in batch:
                day_h = daily.get(iso_date)
                if not day_h:
                    console.print(
                        f"  [dim]Concurso {concurso} ({iso_date}): sem dados no arquivo[/dim]"
                    )
                    continue
                resumo = _processar_resumo_extended(day_h)
                _save_climate(concurso, iso_date, resumo, day_h)
                done += 1
                temp   = resumo.get("temp_sorteio")
                precip = resumo.get("precipitacao_sorteio")
                info   = f"{temp}°C" if temp is not None else "?°C"
                if precip is not None:
                    info += f" / {precip}%"
                console.print(f"  Concurso {concurso} ({iso_date}): clima ✓  {info}")

        except Exception as exc:
            console.print(
                f"  [yellow]Lote {start_date}→{end_date}: erro — {exc}[/yellow]"
            )

        i += len(batch)
        if i < len(missing):
            time.sleep(ARCHIVE_DELAY_SECONDS)

    console.print(f"[green]✓ Clima: {done}/{len(missing)} concursos atualizados[/green]")


# ─── Status ───────────────────────────────────────────────────────────────────

@app.command()
def status() -> None:
    """Mostra total de concursos, cobertura de lua e clima."""
    draws = _load_draw_index()
    if not draws:
        console.print("[yellow]Nenhum concurso encontrado em dados/[/yellow]")
        console.print("Execute: [cyan]lotofacil dados atualizar --escopo todos[/cyan]")
        return

    total    = len(draws)
    lua_ok   = sum(1 for _, d in draws if _lua_exists(d))
    clima_ok = sum(1 for c, _ in draws if _clima_exists(c))
    c_last, d_last = draws[-1]

    console.print("[bold]Status dos dados[/bold]")
    console.print(
        f"Concursos: [cyan]{total}[/cyan]  |  "
        f"Último: [cyan]{c_last}[/cyan] ({d_last})"
    )
    lua_color   = "green" if lua_ok   == total else "yellow"
    clima_color = "green" if clima_ok == total else "yellow"
    console.print(f"Lua:   [{lua_color}]{lua_ok}/{total}[/{lua_color}]")
    console.print(f"Clima: [{clima_color}]{clima_ok}/{total}[/{clima_color}]")
