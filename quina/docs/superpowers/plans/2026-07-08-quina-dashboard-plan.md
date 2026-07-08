# Quina — Dashboard Mínimo + Deploy EasyPanel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal, data-only Flask dashboard for the Quina project (status, frequência, atraso, botão "Atualizar dados") and ship a `Dockerfile` + `entrypoint.sh` ready for an independent EasyPanel service.

**Architecture:** New `quina/src/quina/interface/painel/` package (Flask `server.py` + `static/dashboard.html`), following the same layered convention as `quina/interface/cli/`. No new backend capability beyond what Phase 1 (Fundação) already built — every route reads from `DatabaseManager` (Task 5 of the Fundação plan) or triggers `QuinaFetcher.sync_new_draws()` (Task 7 of the Fundação plan). No auth, no ML/backtest/portfolio content — those don't exist yet.

**Tech Stack:** Flask 3, gunicorn (production WSGI server), vanilla HTML/CSS/JS (no frontend framework, no CDN dependency). Python 3.12, same venv as the rest of `quina/`.

## Global Constraints

- No authentication — sorteio data is public information, nothing sensitive.
- No content from later roadmap phases (predições, modelos, backtest, portfólio, alertas, leaderboard) — this dashboard only shows what Phase 1 already collects.
- All routes must handle an empty database (0 concursos) gracefully — return zeroed/empty structures, never a 500 for that case.
- `quina/` stays fully independent — no imports from or into `lotofacil`.
- Follow the existing test-double pattern from `quina/testes/integracao/test_cli_dados.py`: `monkeypatch.setattr(module, "DatabaseManager", partial(DatabaseManager, db_path=...))` — patch names imported into the module under test, not the original class.
- Deploy target is a **separate** EasyPanel service from the existing lotofacil one — own Dockerfile, own build context (`quina`), own port (`5000`), own persistent volume (`/app/dados`).

---

## Task 1: Flask Scaffold + `/api/status`

**Files:**
- Modify: `quina/pyproject.toml` (add `flask`, `gunicorn` to `dependencies`)
- Create: `quina/src/quina/interface/painel/__init__.py`
- Create: `quina/src/quina/interface/painel/server.py`
- Test: `quina/testes/integracao/test_server.py`

**Interfaces:**
- Consumes: `DatabaseManager` from `quina.infra.dados.banco` (already exists — `count_concursos() -> int`, `get_latest_concurso() -> Optional[dict]`).
- Produces: Flask app object `quina.interface.painel.server.app`; route `GET /api/status` returning `{"total_concursos": int, "ultimo_concurso": {"concurso": int, "data": str, "dezenas": [int]} | None}`.

- [ ] **Step 1: Add Flask and gunicorn to dependencies**

Edit `quina/pyproject.toml` — in the `dependencies` list, add two lines after `"rich>=13.0.0",`:

```toml
dependencies = [
    "requests>=2.31.0",
    "tenacity>=8.2.0",
    "pydantic>=2.0.0",
    "typer>=0.9.0",
    "rich>=13.0.0",
    "flask>=3.0.0",
    "gunicorn>=22.0.0",
]
```

- [ ] **Step 2: Create the package directory**

```bash
mkdir -p quina/src/quina/interface/painel/static
touch quina/src/quina/interface/painel/__init__.py
```

- [ ] **Step 3: Write the failing test**

File: `quina/testes/integracao/test_server.py`

```python
"""Tests for the Quina dashboard Flask server."""
from functools import partial

import pytest

from quina.infra.dados.banco import DatabaseManager
from quina.interface.painel import server as painel_server


def _patch_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(painel_server, "DatabaseManager", partial(DatabaseManager, db_path=db_path))
    return db_path


@pytest.fixture
def client():
    painel_server.app.config["TESTING"] = True
    return painel_server.app.test_client()


class TestApiStatus:
    def test_status_empty(self, client, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        resp = client.get("/api/status")

        assert resp.status_code == 200
        assert resp.get_json() == {"total_concursos": 0, "ultimo_concurso": None}

    def test_status_with_data(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])

        resp = client.get("/api/status")
        data = resp.get_json()

        assert data["total_concursos"] == 1
        assert data["ultimo_concurso"]["concurso"] == 7059
        assert data["ultimo_concurso"]["data"] == "07/07/2026"
        assert data["ultimo_concurso"]["dezenas"] == [27, 47, 57, 70, 78]
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd quina && source venv/bin/activate && pip install -e ".[dev]" && pytest testes/integracao/test_server.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quina.interface.painel.server'`

- [ ] **Step 5: Write the implementation**

File: `quina/src/quina/interface/painel/server.py`

```python
"""Flask dashboard for Quina — minimal data-only view."""
from __future__ import annotations

from flask import Flask, jsonify

from quina.infra.dados.banco import DatabaseManager

app = Flask(__name__)


@app.route("/api/status")
def api_status():
    db = DatabaseManager()
    return jsonify({
        "total_concursos": db.count_concursos(),
        "ultimo_concurso": db.get_latest_concurso(),
    })
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest testes/integracao/test_server.py -v`
Expected: PASS — both tests in `TestApiStatus` green.

- [ ] **Step 7: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add quina/pyproject.toml quina/src/quina/interface/painel/__init__.py quina/src/quina/interface/painel/server.py quina/testes/integracao/test_server.py
git commit -m "$(cat <<'EOF'
feat(quina): add Flask dashboard scaffold with /api/status

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `/api/frequencia` and `/api/atraso`

**Files:**
- Modify: `quina/src/quina/interface/painel/server.py`
- Modify: `quina/testes/integracao/test_server.py`

**Interfaces:**
- Consumes: `TOTAL_NUMEROS` (=80) from `quina.dominio.regras`; `DatabaseManager.get_all_concursos() -> List[dict]` (already exists, ordered ascending by `concurso`).
- Produces: `GET /api/frequencia` → `{"frequencia": {"1": int, ..., "80": int}, "total_concursos": int}`; `GET /api/atraso` → `{"atraso": {"1": {"atraso": int, "ultimo_concurso": int|None}, ..., "80": {...}}, "total_concursos": int}`.

- [ ] **Step 1: Write the failing tests**

Append to `quina/testes/integracao/test_server.py`:

```python
def _seed_three_concursos(db):
    db.upsert_concurso(7057, "04/07/2026", [34, 38, 47, 63, 75])
    db.upsert_concurso(7058, "06/07/2026", [8, 26, 27, 66, 79])
    db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])


class TestApiFrequencia:
    def test_frequencia_empty(self, client, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        resp = client.get("/api/frequencia")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["total_concursos"] == 0
        assert data["frequencia"]["1"] == 0
        assert data["frequencia"]["80"] == 0
        assert len(data["frequencia"]) == 80

    def test_frequencia_with_data(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_three_concursos(DatabaseManager(db_path=db_path))

        resp = client.get("/api/frequencia")
        data = resp.get_json()

        assert data["total_concursos"] == 3
        assert data["frequencia"]["27"] == 2   # concursos 7058 e 7059
        assert data["frequencia"]["47"] == 2   # concursos 7057 e 7059
        assert data["frequencia"]["34"] == 1
        assert data["frequencia"]["1"] == 0    # nunca sorteado


class TestApiAtraso:
    def test_atraso_empty(self, client, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        resp = client.get("/api/atraso")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["total_concursos"] == 0
        assert data["atraso"]["1"] == {"atraso": 0, "ultimo_concurso": None}

    def test_atraso_with_data(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_three_concursos(DatabaseManager(db_path=db_path))

        resp = client.get("/api/atraso")
        data = resp.get_json()

        assert data["total_concursos"] == 3
        # 27 e 47 saíram no último concurso (7059) -> atraso 0
        assert data["atraso"]["27"] == {"atraso": 0, "ultimo_concurso": 7059}
        assert data["atraso"]["47"] == {"atraso": 0, "ultimo_concurso": 7059}
        # 8 saiu só no concurso 7058 (índice 1 de 3) -> atraso 1
        assert data["atraso"]["8"] == {"atraso": 1, "ultimo_concurso": 7058}
        # 34 saiu só no concurso 7057 (índice 0 de 3) -> atraso 2
        assert data["atraso"]["34"] == {"atraso": 2, "ultimo_concurso": 7057}
        # 1 nunca saiu -> atraso == total_concursos, sem último concurso
        assert data["atraso"]["1"] == {"atraso": 3, "ultimo_concurso": None}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_server.py -v -k "Frequencia or Atraso"`
Expected: FAIL with `404 NOT FOUND` (routes don't exist yet) — assertions on `resp.status_code == 200` fail.

- [ ] **Step 3: Write the implementation**

In `quina/src/quina/interface/painel/server.py`, add the import and two routes:

```python
from quina.dominio.regras import TOTAL_NUMEROS
```

(add this import alongside the existing `DatabaseManager` import at the top)

```python
@app.route("/api/frequencia")
def api_frequencia():
    db = DatabaseManager()
    concursos = db.get_all_concursos()
    frequencia = {str(n): 0 for n in range(1, TOTAL_NUMEROS + 1)}
    for c in concursos:
        for n in c["dezenas"]:
            frequencia[str(n)] += 1
    return jsonify({"frequencia": frequencia, "total_concursos": len(concursos)})


@app.route("/api/atraso")
def api_atraso():
    db = DatabaseManager()
    concursos = db.get_all_concursos()  # ordered ascending by concurso
    total = len(concursos)
    ultimo_indice: dict[int, int] = {}
    for i, c in enumerate(concursos):
        for n in c["dezenas"]:
            ultimo_indice[n] = i

    atraso = {}
    for n in range(1, TOTAL_NUMEROS + 1):
        if n in ultimo_indice:
            idx = ultimo_indice[n]
            atraso[str(n)] = {
                "atraso": total - 1 - idx,
                "ultimo_concurso": concursos[idx]["concurso"],
            }
        else:
            atraso[str(n)] = {"atraso": total, "ultimo_concurso": None}

    return jsonify({"atraso": atraso, "total_concursos": total})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest testes/integracao/test_server.py -v`
Expected: PASS — all tests, including `TestApiStatus` from Task 1, green (6 tests total).

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add quina/src/quina/interface/painel/server.py quina/testes/integracao/test_server.py
git commit -m "$(cat <<'EOF'
feat(quina): add /api/frequencia and /api/atraso routes

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `POST /api/atualizar`

**Files:**
- Modify: `quina/src/quina/interface/painel/server.py`
- Modify: `quina/testes/integracao/test_server.py`

**Interfaces:**
- Consumes: `QuinaFetcher` from `quina.infra.dados.api_caixa` (already exists — `sync_new_draws() -> int`).
- Produces: `POST /api/atualizar` → `{"novos": int}` (200) on success, `{"error": str}` (500) on exception.

- [ ] **Step 1: Write the failing tests**

Append to `quina/testes/integracao/test_server.py`:

```python
class TestApiAtualizar:
    def test_atualizar_success(self, client, monkeypatch):
        class FakeFetcher:
            def __init__(self, *args, **kwargs):
                pass

            def sync_new_draws(self):
                return 3

        monkeypatch.setattr(painel_server, "QuinaFetcher", FakeFetcher)

        resp = client.post("/api/atualizar")

        assert resp.status_code == 200
        assert resp.get_json() == {"novos": 3}

    def test_atualizar_failure(self, client, monkeypatch):
        class FakeFetcher:
            def __init__(self, *args, **kwargs):
                pass

            def sync_new_draws(self):
                raise RuntimeError("API indisponível")

        monkeypatch.setattr(painel_server, "QuinaFetcher", FakeFetcher)

        resp = client.post("/api/atualizar")

        assert resp.status_code == 500
        assert "API indisponível" in resp.get_json()["error"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_server.py -v -k Atualizar`
Expected: FAIL — `404 NOT FOUND` (route doesn't exist), or `AttributeError`/`ImportError` since `painel_server.QuinaFetcher` doesn't exist as a name yet.

- [ ] **Step 3: Write the implementation**

Add the import and route to `quina/src/quina/interface/painel/server.py`:

```python
from quina.infra.dados.api_caixa import QuinaFetcher
```

(add alongside the other imports at the top)

```python
@app.route("/api/atualizar", methods=["POST"])
def api_atualizar():
    try:
        fetcher = QuinaFetcher()
        novos = fetcher.sync_new_draws()
        return jsonify({"novos": novos})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest testes/integracao/test_server.py -v`
Expected: PASS — all tests green (8 tests total).

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add quina/src/quina/interface/painel/server.py quina/testes/integracao/test_server.py
git commit -m "$(cat <<'EOF'
feat(quina): add POST /api/atualizar route

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Frontend — `/` Route and `dashboard.html`

**Files:**
- Modify: `quina/src/quina/interface/painel/server.py`
- Create: `quina/src/quina/interface/painel/static/dashboard.html`
- Modify: `quina/testes/integracao/test_server.py`

**Interfaces:**
- Produces: `GET /` → serves `static/dashboard.html` (200, `Content-Type: text/html`).
- The page calls `GET /api/status`, `GET /api/frequencia`, `GET /api/atraso` on load, and `POST /api/atualizar` on button click, using vanilla `fetch()` — no build step, no external CDN.

- [ ] **Step 1: Write the failing test**

Append to `quina/testes/integracao/test_server.py`:

```python
class TestIndex:
    def test_index_serves_html(self, client):
        resp = client.get("/")

        assert resp.status_code == 200
        assert resp.content_type.startswith("text/html")
        assert b"Quina" in resp.data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_server.py -v -k Index`
Expected: FAIL with `404 NOT FOUND`.

- [ ] **Step 3: Write the implementation**

Add to `quina/src/quina/interface/painel/server.py` — imports first:

```python
from pathlib import Path

from flask import send_from_directory
```

(merge `send_from_directory` into the existing `from flask import Flask, jsonify` line, and add the `Path`/`STATIC_DIR` lines near the top, after `app = Flask(__name__)`)

```python
STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "dashboard.html")
```

File: `quina/src/quina/interface/painel/static/dashboard.html`

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Quina — Painel de Dados</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #0f1115;
    --card: #1a1d24;
    --border: #2a2e37;
    --text: #e8eaed;
    --muted: #9aa0a8;
    --accent: #4f8cff;
    --accent-2: #22c55e;
    --danger: #ef4444;
  }
  @media (prefers-color-scheme: light) {
    :root {
      --bg: #f5f6f8;
      --card: #ffffff;
      --border: #e2e5ea;
      --text: #16181d;
      --muted: #5b6270;
      --accent: #2563eb;
      --accent-2: #16a34a;
      --danger: #dc2626;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 24px;
  }
  h1 { font-size: 1.4rem; margin: 0 0 20px; }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    max-width: 1100px;
    margin: 0 auto;
  }
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 18px;
  }
  .card h2 { font-size: 0.95rem; color: var(--muted); margin: 0 0 12px; text-transform: uppercase; letter-spacing: 0.04em; }
  .stat { font-size: 1.8rem; font-weight: 600; }
  .dezenas { display: flex; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
  .bola {
    width: 32px; height: 32px; border-radius: 50%;
    background: var(--accent); color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.85rem; font-weight: 600;
  }
  button {
    background: var(--accent); color: #fff; border: none;
    padding: 10px 16px; border-radius: 8px; font-size: 0.9rem;
    cursor: pointer; margin-top: 12px;
  }
  button:disabled { opacity: 0.6; cursor: default; }
  .erro { color: var(--danger); font-size: 0.85rem; margin-top: 8px; }
  .freq-grid { display: grid; grid-template-columns: repeat(10, 1fr); gap: 4px; font-size: 0.72rem; }
  .freq-cell { text-align: center; padding: 4px 2px; border-radius: 4px; background: var(--border); }
  table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  th, td { text-align: left; padding: 4px 6px; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 500; }
</style>
</head>
<body>
  <h1>Quina — Painel de Dados</h1>
  <div class="grid">
    <div class="card">
      <h2>Status</h2>
      <div id="status-total" class="stat">—</div>
      <div id="status-muted" style="color:var(--muted); font-size:0.85rem;">concursos coletados</div>
      <div id="status-dezenas" class="dezenas"></div>
      <button id="btn-atualizar">Atualizar dados</button>
      <div id="status-erro" class="erro"></div>
    </div>
    <div class="card">
      <h2>Frequência (1–80)</h2>
      <div id="freq-grid" class="freq-grid"></div>
      <div id="freq-erro" class="erro"></div>
    </div>
    <div class="card">
      <h2>Maiores atrasos</h2>
      <table>
        <thead><tr><th>Número</th><th>Atraso</th><th>Último concurso</th></tr></thead>
        <tbody id="atraso-body"></tbody>
      </table>
      <div id="atraso-erro" class="erro"></div>
    </div>
  </div>

<script>
async function carregarStatus() {
  const el = document.getElementById("status-erro");
  el.textContent = "";
  try {
    const resp = await fetch("/api/status");
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const data = await resp.json();
    document.getElementById("status-total").textContent = data.total_concursos;
    const dezenasEl = document.getElementById("status-dezenas");
    dezenasEl.innerHTML = "";
    if (data.ultimo_concurso) {
      for (const n of data.ultimo_concurso.dezenas) {
        const b = document.createElement("div");
        b.className = "bola";
        b.textContent = n;
        dezenasEl.appendChild(b);
      }
      document.getElementById("status-muted").textContent =
        `concurso ${data.ultimo_concurso.concurso} — ${data.ultimo_concurso.data}`;
    }
  } catch (e) {
    el.textContent = "Erro ao carregar status: " + e.message;
  }
}

async function carregarFrequencia() {
  const el = document.getElementById("freq-erro");
  el.textContent = "";
  try {
    const resp = await fetch("/api/frequencia");
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const data = await resp.json();
    const grid = document.getElementById("freq-grid");
    grid.innerHTML = "";
    for (let n = 1; n <= 80; n++) {
      const cell = document.createElement("div");
      cell.className = "freq-cell";
      cell.textContent = n + ":" + data.frequencia[String(n)];
      grid.appendChild(cell);
    }
  } catch (e) {
    el.textContent = "Erro ao carregar frequência: " + e.message;
  }
}

async function carregarAtraso() {
  const el = document.getElementById("atraso-erro");
  el.textContent = "";
  try {
    const resp = await fetch("/api/atraso");
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const data = await resp.json();
    const rows = Object.entries(data.atraso)
      .map(([n, v]) => ({ n: Number(n), ...v }))
      .sort((a, b) => b.atraso - a.atraso)
      .slice(0, 15);
    const body = document.getElementById("atraso-body");
    body.innerHTML = "";
    for (const r of rows) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${r.n}</td><td>${r.atraso}</td><td>${r.ultimo_concurso ?? "—"}</td>`;
      body.appendChild(tr);
    }
  } catch (e) {
    el.textContent = "Erro ao carregar atraso: " + e.message;
  }
}

async function carregarTudo() {
  await Promise.all([carregarStatus(), carregarFrequencia(), carregarAtraso()]);
}

document.getElementById("btn-atualizar").addEventListener("click", async () => {
  const btn = document.getElementById("btn-atualizar");
  const el = document.getElementById("status-erro");
  btn.disabled = true;
  btn.textContent = "Atualizando...";
  el.textContent = "";
  try {
    const resp = await fetch("/api/atualizar", { method: "POST" });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "HTTP " + resp.status);
    await carregarTudo();
  } catch (e) {
    el.textContent = "Erro ao atualizar: " + e.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Atualizar dados";
  }
});

carregarTudo();
</script>
</body>
</html>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest testes/integracao/test_server.py -v`
Expected: PASS — all tests green (9 tests total).

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add quina/src/quina/interface/painel/server.py quina/src/quina/interface/painel/static/dashboard.html quina/testes/integracao/test_server.py
git commit -m "$(cat <<'EOF'
feat(quina): add dashboard frontend (status, frequência, atraso, atualizar)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Dockerfile, entrypoint.sh, and Verification

**Files:**
- Create: `quina/Dockerfile`
- Create: `quina/entrypoint.sh`

**Interfaces:** none — this task packages the already-tested application for deployment; no application code changes.

- [ ] **Step 1: Write `entrypoint.sh`**

File: `quina/entrypoint.sh`

```bash
#!/bin/bash
set -e

mkdir -p /app/dados /app/saida

if ! ls /app/dados/concurso_*.json > /dev/null 2>&1; then
    echo "[entrypoint] Dados vazios. Use o botão 'Atualizar dados' no painel ou rode 'quina dados atualizar'."
fi

exec "$@"
```

```bash
chmod +x quina/entrypoint.sh
```

- [ ] **Step 2: Write `Dockerfile`**

File: `quina/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e .

RUN mkdir -p dados saida

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV PYTHONPATH="/app/src:${PYTHONPATH}"

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/status')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "quina.interface.painel.server:app", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "1", \
     "--threads", "4", \
     "--timeout", "600", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

- [ ] **Step 3: Build the image**

```bash
cd "$(git rev-parse --show-toplevel)/quina"
docker build -t quina-dashboard:local .
```

Expected: build completes with `Successfully tagged quina-dashboard:local` (or the buildkit equivalent final "naming to docker.io/library/quina-dashboard:local done").

- [ ] **Step 4: Run the container with a temporary data volume**

```bash
docker run -d --name quina-dashboard-test -p 18080:5000 \
  -v quina-dashboard-test-dados:/app/dados \
  quina-dashboard:local
sleep 3
docker logs quina-dashboard-test
```

Expected logs include `[entrypoint] Dados vazios...` and gunicorn's "Listening at: http://0.0.0.0:5000" line.

- [ ] **Step 5: Verify the endpoints respond**

```bash
curl -s http://localhost:18080/api/status
curl -s http://localhost:18080/ | grep -o "<title>.*</title>"
curl -s -X POST http://localhost:18080/api/atualizar
```

Expected: `/api/status` returns `{"total_concursos":0,"ultimo_concurso":null}`; `/` contains `<title>Quina — Painel de Dados</title>`; `/api/atualizar` triggers a real sync against the live Caixa API and returns `{"novos": N}` with N being the full historical count (this will take a while — the DB starts empty and there's no seed data in the container, so `sync_new_draws()` backfills from concurso 1). If a quick smoke test is preferred instead of waiting for the full backfill, skip the `/api/atualizar` call and just confirm `/api/status` and `/` respond correctly.

- [ ] **Step 6: Tear down the test container**

```bash
docker stop quina-dashboard-test
docker rm quina-dashboard-test
docker volume rm quina-dashboard-test-dados
```

- [ ] **Step 7: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add quina/Dockerfile quina/entrypoint.sh
git commit -m "$(cat <<'EOF'
build(quina): add Dockerfile and entrypoint for EasyPanel deploy

Mirrors lotofacil/Dockerfile's structure, without the gcc/libgomp1
build deps (no ML libraries in quina yet). Verified locally: image
builds, container serves / and /api/status correctly.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 8: Document the EasyPanel configuration**

No file change — this is operator guidance for whoever configures the EasyPanel service:

| Campo | Valor |
|-------|-------|
| Build Context | `quina` |
| Dockerfile Path | `Dockerfile` |
| Porta | `5000` |
| Volume | montar em `/app/dados` (persiste `quina.db` + `concurso_*.json` entre deploys) |

First deploy: the database starts empty. Click "Atualizar dados" in the dashboard (or run `quina dados atualizar` inside the container) to backfill the full draw history from the Caixa API.

---

## Self-Review Notes

- **Spec coverage:** every route in `docs/superpowers/specs/2026-07-08-quina-dashboard-design.md` maps to a task — `/api/status` (Task 1), `/api/frequencia` + `/api/atraso` (Task 2), `/api/atualizar` (Task 3), `/` + frontend (Task 4), Dockerfile/entrypoint/EasyPanel config (Task 5).
- **Placeholder scan:** no TBD/TODO — every step has runnable code, including the full `dashboard.html`.
- **Type consistency:** `DatabaseManager.get_all_concursos()`/`get_latest_concurso()` return shape (`{"concurso", "data", "dezenas"}`) is used identically across Tasks 1, 2, and the frontend's expectations in Task 4. `QuinaFetcher.sync_new_draws() -> int` is used consistently between Task 3's route and its test's `FakeFetcher`.
- **Fora de escopo** (confirmed untouched by any task): authentication, predições, modelos, backtest, portfólio, alertas, scheduler.
