# Autenticação Básica Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar proteção por senha ao dashboard via `DASHBOARD_PASSWORD` env var, com sessão de 30 dias, página de login inline e botão de logout na navbar.

**Architecture:** `app.before_request` checa sessão; se `DASHBOARD_PASSWORD` não definida, auth é desabilitada (comportamento atual). Página `/login` com formulário POST. `/logout` limpa a sessão. `LOGIN_HTML` é um template string inline em `server.py`. `auth_enabled` adicionado a `/api/status` para o frontend detectar se deve mostrar o botão de logout.

**Tech Stack:** Python 3.12, Flask sessions, `secrets`, pytest.

---

## File Map

| Arquivo | Ação |
|---------|------|
| `src/lotofacil/interface/painel/server.py` | `secret_key`, `before_request`, `/login`, `/logout`, `LOGIN_HTML`, `auth_enabled` em `/api/status` |
| `src/lotofacil/interface/painel/static/dashboard.html` | Botão logout na navbar + handler 401 nos fetches principais |
| `src/lotofacil/interface/painel/tests/test_server.py` | Acrescentar 6 testes de auth |

---

## Task 1: Testes de auth em `test_server.py` (TDD)

**Files:**
- Modify: `src/lotofacil/interface/painel/tests/test_server.py`

- [ ] **Step 1: Acrescentar 6 testes ao final de `test_server.py`**

```python
# ── Autenticação ───────────────────────────────────────────────
import os


def test_sem_password_nao_requer_auth(client):
    """Sem DASHBOARD_PASSWORD configurada, dashboard abre sem login."""
    # fixture autouse já garante que DADOS_DIR está patchado
    resp = client.get("/")
    assert resp.status_code == 200


def test_com_password_redireciona_para_login(client, monkeypatch):
    """Com DASHBOARD_PASSWORD definida, GET / sem sessão → 302 para /login."""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "teste123")
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_correto_cria_sessao(client, monkeypatch):
    """POST /login com senha correta → redireciona para / e cria sessão."""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "teste123")
    resp = client.post("/login", data={"password": "teste123"}, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/") or "/" in resp.headers["Location"]


def test_login_errado_retorna_erro(client, monkeypatch):
    """POST /login com senha errada → 200 com mensagem de erro."""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "teste123")
    resp = client.post("/login", data={"password": "errada"})
    assert resp.status_code == 200
    assert b"incorreta" in resp.data.lower() or b"senha" in resp.data.lower()


def test_api_sem_sessao_retorna_401(client, monkeypatch):
    """Com auth ativa, GET /api/status sem sessão → 401 JSON."""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "teste123")
    resp = client.get("/api/status")
    assert resp.status_code == 401
    data = json.loads(resp.data)
    assert "error" in data


def test_logout_limpa_sessao(client, monkeypatch):
    """Após login + logout, GET / redireciona novamente para /login."""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "teste123")
    # login
    client.post("/login", data={"password": "teste123"})
    # logout
    client.get("/logout")
    # agora sem sessão
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd /home/andre/Documentos/projetos/loteria/lotofacil && source venv/bin/activate
pytest src/lotofacil/interface/painel/tests/test_server.py::test_com_password_redireciona_para_login -v 2>&1 | tail -8
```

Expected: `AssertionError` — GET / retorna 200 mesmo com password setada.

---

## Task 2: Backend — auth em `server.py`

**Files:**
- Modify: `src/lotofacil/interface/painel/server.py`

- [ ] **Step 1: Adicionar imports necessários**

Localizar:
```python
from flask import Flask, jsonify, request, send_from_directory, Response
```

Substituir por:
```python
import secrets
from functools import wraps
from flask import (
    Flask, jsonify, request, send_from_directory, Response,
    session, redirect, url_for, render_template_string,
)
```

- [ ] **Step 2: Configurar `secret_key` e `permanent_session_lifetime`**

Após a linha `app = Flask(__name__)` (procure `app = Flask`), inserir imediatamente abaixo:

```python
app.secret_key = os.environ.get("DASHBOARD_AUTH_SECRET") or secrets.token_hex(32)
from datetime import timedelta as _timedelta
app.permanent_session_lifetime = _timedelta(days=30)
```

- [ ] **Step 3: Adicionar o template de login**

Imediatamente antes de `@app.route("/")` inserir:

```python
_LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Login — Lotofácil Dashboard</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#0f1117;color:#e2e8f0;font-family:monospace;display:flex;
       align-items:center;justify-content:center;height:100vh}
  .card{background:#1a1f2e;border:1px solid #2d3748;border-radius:10px;
        padding:2rem;width:320px}
  h1{font-size:1.1rem;margin-bottom:1.5rem;color:#60a5fa}
  label{font-size:0.78rem;color:#94a3b8;display:block;margin-bottom:0.3rem}
  input[type=password]{width:100%;padding:0.5rem 0.75rem;background:#0f1117;
    color:#e2e8f0;border:1px solid #2d3748;border-radius:5px;
    font-family:monospace;font-size:0.9rem;margin-bottom:1rem}
  input[type=password]:focus{outline:none;border-color:#60a5fa}
  button{width:100%;padding:0.55rem;background:#1e3a5f;color:#60a5fa;
    border:1px solid #60a5fa;border-radius:5px;font-family:monospace;
    font-size:0.9rem;cursor:pointer}
  button:hover{background:#2d4a6f}
  .error{color:#f87171;font-size:0.78rem;margin-bottom:0.75rem}
</style>
</head>
<body>
<div class="card">
  <h1>🎰 Lotofácil Dashboard</h1>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  <form method="post">
    <label>Senha</label>
    <input type="password" name="password" autofocus autocomplete="current-password">
    <button type="submit">Entrar</button>
  </form>
</div>
</body>
</html>"""
```

- [ ] **Step 4: Adicionar rotas `/login` e `/logout`**

Imediatamente após o template `_LOGIN_HTML` (antes de `@app.route("/")`), inserir:

```python
@app.route("/login", methods=["GET", "POST"])
def login_page():
    password = os.environ.get("DASHBOARD_PASSWORD", "")
    if not password:
        return redirect(url_for("index"))
    if request.method == "POST":
        if request.form.get("password") == password:
            session.permanent = True
            session["authenticated"] = True
            return redirect(url_for("index"))
        return render_template_string(_LOGIN_HTML, error="Senha incorreta.")
    return render_template_string(_LOGIN_HTML, error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))
```

- [ ] **Step 5: Adicionar `before_request` para proteger todas as rotas**

Imediatamente após as rotas `/login` e `/logout`, inserir:

```python
@app.before_request
def _check_auth():
    password = os.environ.get("DASHBOARD_PASSWORD", "")
    if not password:
        return None  # auth desabilitada
    if session.get("authenticated"):
        return None  # sessão válida
    if request.endpoint in ("login_page", "logout", "static"):
        return None  # rotas públicas
    if request.path.startswith("/api/"):
        return jsonify({"error": "unauthorized"}), 401
    return redirect(url_for("login_page"))
```

- [ ] **Step 6: Adicionar `auth_enabled` em `/api/status`**

Localizar a função `api_status` e o `return jsonify(...)`:

```python
    return jsonify({
        "last_concurso": latest,
        "total_draws": info["total"],
        "games_count": len(_list_game_files()),
        "timestamp": datetime.now().isoformat(),
    })
```

Substituir por:

```python
    return jsonify({
        "last_concurso": latest,
        "total_draws": info["total"],
        "games_count": len(_list_game_files()),
        "timestamp": datetime.now().isoformat(),
        "auth_enabled": bool(os.environ.get("DASHBOARD_PASSWORD", "")),
    })
```

- [ ] **Step 7: Rodar os 6 testes de auth**

```bash
pytest src/lotofacil/interface/painel/tests/test_server.py -v -k "login or auth or logout or password or sem_password" 2>&1 | tail -15
```

Expected: `6 passed`.

- [ ] **Step 8: Rodar suite completa**

```bash
pytest src/lotofacil/interface/painel/tests/test_server.py -v 2>&1 | tail -10
```

Expected: todos `PASSED`.

- [ ] **Step 9: Commit**

```bash
git add src/lotofacil/interface/painel/server.py \
        src/lotofacil/interface/painel/tests/test_server.py
git commit -m "feat: add password-based auth via DASHBOARD_PASSWORD env var

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Frontend — botão logout e handler 401

**Files:**
- Modify: `src/lotofacil/interface/painel/static/dashboard.html`

- [ ] **Step 1: Adicionar botão logout na navbar**

Localizar a navbar HTML (próximo a `<nav class="navbar">`). Dentro do `<nav class="navbar">`, adicionar o botão de logout após os elementos existentes de status:

Procurar por `id="onlineIndicator"` ou o último elemento da navbar. Antes do fechamento `</nav>`, inserir:

```html
<span id="logoutBtn" style="display:none">
  <a href="/logout" style="font-size:0.7rem;color:var(--muted);text-decoration:none;
     border:1px solid var(--border);border-radius:4px;padding:2px 8px;
     margin-left:0.5rem">
    Sair
  </a>
</span>
```

- [ ] **Step 2: Mostrar o botão logout quando `auth_enabled=true`**

Localizar a função `loadStatus()` em dashboard.html. Ela faz `fetch('/api/status')` e usa o resultado. Dentro do callback de sucesso, após as linhas que atualizam `total_draws`, `last_concurso`, etc., adicionar:

```javascript
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) logoutBtn.style.display = d.auth_enabled ? 'inline' : 'none';
```

- [ ] **Step 3: Adicionar handler 401 nas chamadas fetch principais**

Nas 4 funções que fazem fetch de dados importantes (`loadStatus`, `renderDados`, `loadModelosAndRender`, `runRoiBacktest`), o tratamento já existe ou é implícito. Adicionar uma função helper global que detecta 401 e redireciona:

Localizar o início do bloco `<script>` principal. Imediatamente após a abertura do script, antes de qualquer função, inserir:

```javascript
function _handle401(resp) {
  if (resp.status === 401) {
    window.location.href = '/login';
    return true;
  }
  return false;
}
```

Em seguida, nos fetches de `loadStatus` (que é o mais crítico), localizar o padrão:
```javascript
const r = await fetch('/api/status');
```

Adicionar verificação logo após:
```javascript
const r = await fetch('/api/status');
if (_handle401(r)) return;
```

Fazer o mesmo para `renderDados` (`fetch('/api/dados...')`).

- [ ] **Step 4: Verificar importação OK**

```bash
python -c "from lotofacil.interface.painel import server; print('OK')"
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/interface/painel/static/dashboard.html
git commit -m "feat: add logout button and 401 redirect handler to dashboard

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Self-Review

- ✅ `DASHBOARD_PASSWORD` vazio → auth desabilitada, zero mudança de comportamento
- ✅ `app.secret_key` usa env var ou gera aleatório na inicialização (muda a cada restart se `DASHBOARD_AUTH_SECRET` não estiver definida — aceitável para uso local)
- ✅ `/login` e `/logout` e `static` são rotas públicas (whitelist em `_check_auth`)
- ✅ Rotas `/api/*` retornam 401 JSON (não redirect) — friendly para fetch do frontend
- ✅ `LOGIN_HTML` é template string inline — sem arquivo externo, sem `templates/`
- ✅ Testes usam `monkeypatch.setenv` — isolados, não afetam outros testes
- ⚠️ `app.secret_key` muda a cada restart se `DASHBOARD_AUTH_SECRET` não está definida — isso invalida sessões. Usuário precisa fazer login de novo após restart do servidor. Documentar no README se necessário. Para persistência de sessão entre restarts, definir `DASHBOARD_AUTH_SECRET` fixo.
