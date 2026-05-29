# Autenticação Básica — Design Spec

**Data:** 2026-05-29  
**Status:** Aprovado  
**Limitação resolvida:** #1 — sem autenticação, impossível expor em rede com segurança

---

## Contexto

O dashboard roda em `0.0.0.0:5000` sem qualquer proteção. Qualquer pessoa na mesma rede pode acessar, disparar treinos, ver dados e cancelar processos. Para acesso remoto seguro (ex: de outro computador na rede local, ou via tunnel), é necessário ao menos uma senha.

**Requisitos:**
- Sem banco de usuários — um único password configurado por env var
- Sem TLS (o tunnel/proxy cuida disso externamente)
- Sessão persistente (não pede senha a cada request)
- Sem auth → dashboard simplesmente não é acessível (não degraded mode)
- Se `DASHBOARD_PASSWORD` não estiver definida → sem auth (comportamento atual, uso local)

---

## Design

### Configuração

```bash
DASHBOARD_PASSWORD=minha-senha lotofacil dashboard
# ou
export DASHBOARD_PASSWORD=minha-senha
```

Se a variável não estiver definida ou for string vazia → auth desabilitada. Comportamento idêntico ao atual.

### Backend

**`SECRET_KEY`** gerada aleatoriamente na inicialização se `DASHBOARD_AUTH_SECRET` não estiver definida:

```python
app.secret_key = os.environ.get("DASHBOARD_AUTH_SECRET") or secrets.token_hex(32)
```

**Decorator `@require_auth`:**

```python
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        password = os.environ.get("DASHBOARD_PASSWORD", "")
        if not password:
            return f(*args, **kwargs)   # auth desabilitada
        if session.get("authenticated"):
            return f(*args, **kwargs)   # sessão válida
        if request.path == "/login":
            return f(*args, **kwargs)   # permitir a página de login
        # SSE e API: retornar 401 JSON
        if request.path.startswith("/api/"):
            return jsonify({"error": "unauthorized"}), 401
        # Páginas: redirecionar para /login
        return redirect(url_for("login_page"))
    return decorated
```

Aplicado via `@app.before_request` (único ponto, não decorador por rota):

```python
@app.before_request
def check_auth():
    return require_auth(lambda: None)()
```

**Rota `/login`:**

```python
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        if request.form.get("password") == os.environ.get("DASHBOARD_PASSWORD", ""):
            session.permanent = True
            app.permanent_session_lifetime = timedelta(days=30)
            session["authenticated"] = True
            return redirect(url_for("index"))
        return render_template_string(LOGIN_HTML, error="Senha incorreta.")
    return render_template_string(LOGIN_HTML)
```

**`LOGIN_HTML`:** template mínimo inline (sem arquivo externo) — formulário com campo `password` + botão, estilo consistente com o dashboard (fundo escuro, fonte monospace, mesmas variáveis CSS).

**Logout:**

```python
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))
```

Botão de logout adicionado à navbar (visível apenas quando auth está ativa).

### Frontend

**Mudanças mínimas no `dashboard.html`:**

1. Botão `Sair` na navbar — visível apenas se `DASHBOARD_PASSWORD` estiver configurada. Detectado via novo campo em `/api/status`:
   ```json
   { ..., "auth_enabled": true }
   ```

2. Handler de erro 401 nas chamadas `fetch`: redireciona para `/login`:
   ```javascript
   if (resp.status === 401) { window.location.href = '/login'; return; }
   ```
   Adicionado nas funções `loadStatus`, `runRoiBacktest`, `gerarJogos` e `loadModelosAndRender` (os fetches principais).

---

## Arquivos a modificar

| Arquivo | Mudança |
|---------|---------|
| `src/lotofacil/interface/painel/server.py` | `secret_key`, `require_auth` via `before_request`, rotas `/login` e `/logout`, `LOGIN_HTML`, `auth_enabled` em `/api/status` |
| `src/lotofacil/interface/painel/static/dashboard.html` | Botão logout na navbar, handler 401 nos fetches principais |
| `src/lotofacil/interface/painel/tests/test_server.py` | Testes para `/login`, 401 em rota protegida, bypass quando sem password |

---

## Testes

```python
def test_sem_password_nao_requer_auth(client):
    # GET / sem password configurada → 200

def test_com_password_redireciona_para_login(client, monkeypatch):
    # monkeypatch DASHBOARD_PASSWORD=test123
    # GET / sem sessão → 302 para /login

def test_login_correto_cria_sessao(client, monkeypatch):
    # POST /login password=test123 → 302 para /

def test_login_errado_retorna_erro(client, monkeypatch):
    # POST /login password=errada → 200 com "Senha incorreta"

def test_api_sem_sessao_retorna_401(client, monkeypatch):
    # GET /api/status sem sessão com password configurada → 401 JSON

def test_logout_limpa_sessao(client, monkeypatch):
    # login → GET /logout → GET / → 302 para login
```

---

## O que não muda

- Toda a lógica de negócio do dashboard — zero mudanças
- Endpoints do ROI Lab, treinos, dados — mesma implementação
- Comportamento quando `DASHBOARD_PASSWORD` não está definida — idêntico ao atual
- Sem banco de usuários, sem registro, sem recuperação de senha (uso local/pessoal)
