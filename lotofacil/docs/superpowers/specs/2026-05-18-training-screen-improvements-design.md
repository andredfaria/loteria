# Design: Training Screen & Dashboard Improvements

**Date:** 2026-05-18  
**Status:** Implemented  
**Scope:** `lotofacil/src/lotofacil/interface/painel/`

---

## 1. Problem Statement

The Lotofácil dashboard's Modelos (training) tab lacked several practical features:

1. Models in `running` status could not be deleted — the user had to wait or manually cancel first.
2. Generated games (apostas) existed only as JSON files on disk with no in-app history or consultation.
3. The backtest quality section showed only mean hits and p-value, without hit distribution or baseline comparison.

Secondary goals emerged during implementation: improve the full dashboard (Dados, Validação, Coleta) and complete the training workflow with filtering, sorting, search, and UX polish.

---

## 2. Architecture

### Stack
- **Backend:** Flask (`server.py`) + SQLite via `TreinoRegistry` (`treino_registry.py`)
- **Frontend:** Single-file vanilla JS/HTML (`static/dashboard.html`) — no build step, no framework
- **Data:** `treinos.db` (SQLite) for training sessions, job output, and generated games

### Layer boundaries
```
dashboard.html (UI)
  └─ /api/* (Flask routes in server.py)
       └─ TreinoRegistry (treino_registry.py) ── treinos.db
       └─ BancoDados (banco.py) ── lotofacil.db (draws)
       └─ LotofacilMetrics (metricas.py) ── quality computation
```

---

## 3. Features Implemented

### 3.1 Delete Running Models

**Problem:** `DELETE /api/treinos/<id>` returned 409 when status was `running`.

**Solution:**
- `server.py`: removed 409 block; when `running`, scans `_procs` dict for a key containing `treino_id` (pattern: `treino_<ts>_<id>`), calls `proc.terminate()`, updates status to `cancelled`, then deletes normally.
- `dashboard.html`: `canDelete` condition removed; button shows "🗑 Cancelar e Apagar" for running models; confirm dialog text adapts.

**Files:** `server.py:api_treino_deletar`, `dashboard.html:deleteModelo`

---

### 3.2 Generated Games History

**New table:** `jogos_gerados` in `treinos.db`

```sql
CREATE TABLE IF NOT EXISTS jogos_gerados (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    treino_id  TEXT NOT NULL,
    treino_nome TEXT NOT NULL,
    concurso   INTEGER NOT NULL,
    jogos      TEXT NOT NULL,   -- JSON array of arrays
    criado_em  TEXT NOT NULL
);
```

**New registry methods:** `salvar_jogo()`, `listar_jogos(limit)`

**New route:** `GET /api/jogos-gerados` — lists all saved games enriched with `dezenas_reais` and `acertos_por_jogo` when the draw has occurred (queries `lotofacil.db`).

**New sub-tab "🗂 Histórico"** in Modelos:
- Filter by model (dropdown, client-side, no refetch)
- Stats bar: generations, total games, mean hits, best hit
- Copy button (⎘) per game row → clipboard as `1-3-7-…`
- Export CSV (client-side Blob download)
- Real-result badges: green/yellow/red `X/15 ✓` when draw is known; matching balls highlighted with green outline

**Files:** `treino_registry.py`, `server.py:api_jogos_gerados`, `dashboard.html:renderPredHistorico`

---

### 3.3 Expanded Backtest Cards

**Backend change:** `_build_quality_payload()` now calls `LotofacilMetrics.distribution_of_hits(results)` and includes `hit_distribution: {11: N, 12: N, …, 15: N}` in each model's payload.

**Frontend changes per card:**
- Hit distribution: CSS bars for faixas 11–15 with count × and proportional widths
- vs Baseline badge: `+X%` coloured green/red + classification label (Excelente/Bom/Atenção/Ruim)
- Sample size `n=` shown
- Backtest window control: `input[type=number]` + ↻ button, 10–500 draws, re-fetches only quality data

**Files:** `server.py:_build_quality_payload`, `dashboard.html:renderModLista`

---

### 3.4 Treinos Table — Full UX

| Feature | Implementation |
|---------|---------------|
| Sortable columns | `_predState.listaSort` + `_sortLista(key)` — Nome, Val Loss, Épocas, Data, Status |
| Status filter badges | Clickable chips showing count per status; `_filtroLista()` |
| Name search | Live text filter `_buscaLista(val)` — cursor preserved via `requestAnimationFrame` |
| Training duration | `criado_em → concluido_em` diff shown below date (e.g. "⏱ 3m 42s") |
| Bulk delete failed | "🗑 limpar falhas" button deletes all `failed`/`cancelled` in parallel |
| Row expand | Click ▼/▲ on name → inline sub-row with params, extra metrics, filename, timestamps |
| Export config | "⎘ Copiar config JSON" in expanded row — copies `{nome, tipo_config, parametros}` |
| Rename | ✏ icon → `prompt()` → `PATCH /api/treinos/<id>` → `registry.renomear()` |
| Pagination | 10 per page, "Ver mais N de M" button; resets on filter/sort/search change |
| Sub-tab badge | "📋 Lista (7)" updated after every `loadModelosAndRender` |

---

### 3.5 Gerar Tab — Enhancements

| Feature | Implementation |
|---------|---------------|
| Best model button | "🏆 Melhor modelo" selects model with highest `mean_hits` from loaded quality data |
| Last real draw | Shown below generated games using `_predState.lastDraw` (dezenas from `/api/status`) |
| Frequency heatmap | 25 squares 1–25, opacity ∝ frequency across generated games; most frequent = bold white |
| Recent generations | After generating, shows last 2 prior generations compactly below results |

---

### 3.6 Comparar Tab

Extended comparison table includes: **Hits médios** (delta highlighted), **vs Baseline** (colour-coded), **p-value** — all matched from `_predState.qualidade` by `treino_id` substring in approach name.

---

### 3.7 Training Modal — ETA

`_treinoEpochLog: [{epoch, ts}]` sliding window of last 5 epoch timings. ETA displayed as "Epoch 12/40 · 30% · ETA 4min" once ≥2 samples exist.

---

### 3.8 Other Modelos Improvements

- Background training notification toast when training ends while user is on a different tab
- "atualizado Xs atrás" indicator in header, ticked by existing polling interval
- `_predState.lastUpdatedAt` tracks last successful `loadModelosAndRender`

---

### 3.9 Dados Tab — Frequency Chart

**New endpoint:** `GET /api/dados/frequencia` — scans all `concurso_*.json` files, returns `{frequency: {1:N,…,25:N}, total_draws, expected_avg}`.

**Frontend:** Vertical bar chart above the draws table. Colour coding:
- Green: numbers in top 10% by frequency (hot)
- Red: numbers in bottom 10% (cold)
- Accent: average range

---

### 3.10 Validação Tab — Window Control

`STATE.validacaoLastN` (default 120). Input + "↻ Recalcular" button in action bar. Calls `_recalcValidacao()` which re-fetches quality, trend, leaderboard, and alerts with new window.

---

### 3.11 Coleta Tab — Status Panel

`_renderColetaStats()` appended after command buttons. Shows: total draws, last concurso number, date, dezenas balls. Fetches `/api/status` (which now includes dezenas via `_get_draw_dezenas`).

---

## 4. Data Flow

```
User clicks "Gerar Jogos"
  → POST /api/treinos/<id>/gerar
  → NeuralModular.predict_proba() → top-N numbers per game
  → persist to filesystem (predicao_lab_*.json)
  → persist to registry (jogos_gerados table)
  → return {jogos, concurso, treino_nome}
  → frontend: renderJogos() + _loadGerarRecentes()
  → frequency heatmap computed client-side

User opens Histórico
  → GET /api/jogos-gerados
  → server enriches each row with dezenas_reais + acertos_por_jogo
     from lotofacil.db (cached per concurso in request)
  → frontend: _renderHistoricoPanel() with stats, filter, CSV, badges
```

---

## 5. API Surface (new/changed)

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/jogos-gerados` | List generated games with real results |
| GET | `/api/dados/frequencia` | Number frequency across all draws |
| PATCH | `/api/treinos/<id>` | Rename a training session |
| GET | `/api/models/quality?last_n=N` | Quality payload now includes `hit_distribution` |
| GET | `/api/status` | Now includes `dezenas` of last concurso |
| DELETE | `/api/treinos/<id>` | Now cancels running jobs before deleting |

---

## 6. Schema Changes

`treino_registry.py` — new table `jogos_gerados`, new methods `salvar_jogo`, `listar_jogos`, `renomear`. Migration is automatic (CREATE TABLE IF NOT EXISTS on init).

---

## 7. Testing

All 118 existing tests pass. New registry methods verified with inline smoke tests. New Flask routes smoke-tested via `app.test_client()`.

No new test files added — the changes are primarily UI logic; the backend additions (save_jogo, renomear, frequencia) are thin wrappers over SQLite.

---

## 8. Remaining Work

- [ ] Dados: jump-to-concurso input + export CSV for current page
- [ ] Validação: dismissable alerts, CSS-bar sparkline (replace ASCII)
- [ ] Coleta: auto-refresh stats panel after command completes
- [ ] Modelos: keyboard shortcuts (1–5 for sub-tabs, Escape for modal)
- [ ] Global: dynamic page title reflecting active tab
