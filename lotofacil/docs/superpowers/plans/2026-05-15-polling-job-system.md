# Polling Job System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir SSE + TASKS dict em memória por polling com output persistido em SQLite, e corrigir timeout do Gunicorn para treinos longos.

**Architecture:** Cada comando iniciado via POST persiste output linha-a-linha em `job_output` (SQLite). O frontend faz polling a cada 2s em `GET /api/jobs/<task_id>/poll?offset=N`, recebendo as linhas novas e um flag `done`. O `TASKS` dict e o endpoint SSE `/api/stream` são removidos completamente.

**Tech Stack:** Python 3.12, Flask, SQLite (sqlite3 stdlib), Gunicorn, JavaScript (vanilla)

---

## Parallelization Guide

```
Wave 1 (parallel): Task 1 + Task 5
Wave 2 (sequential, after Task 1): Task 2 → Task 3
Wave 3 (after Task 3): Task 4
```

---

## Task 1: TreinoRegistry — job tables + polling methods

**Files:**
- Modify: `src/lotofacil/interface/painel/treino_registry.py`
- Test: `src/lotofacil/interface/painel/tests/test_treino_registry.py`

- [ ] **Step 1: Escrever os testes com falha**

Criar o arquivo `src/lotofacil/interface/painel/tests/test_treino_registry.py`:

```python
"""Tests for TreinoRegistry job output persistence."""
import pytest
from lotofacil.interface.painel.treino_registry import TreinoRegistry


@pytest.fixture
def reg(tmp_path):
    return TreinoRegistry(tmp_path / "treinos.db")


def test_create_job_and_write_lines(reg):
    reg.create_job("task_001")
    reg.write_line("task_001", "linha 1")
    reg.write_line("task_001", "linha 2")
    result = reg.poll_job("task_001", 0)
    assert result["lines"] == ["linha 1", "linha 2"]
    assert result["done"] is False
    assert "success" not in result


def test_finish_job_success(reg):
    reg.create_job("task_002")
    reg.write_line("task_002", "saída")
    reg.finish_job("task_002", True)
    result = reg.poll_job("task_002", 0)
    assert result["done"] is True
    assert result["success"] is True
    assert result["lines"] == ["saída"]


def test_finish_job_failure(reg):
    reg.create_job("task_003")
    reg.finish_job("task_003", False)
    result = reg.poll_job("task_003", 0)
    assert result["done"] is True
    assert result["success"] is False
    assert result["lines"] == []


def test_poll_offset_pagination(reg):
    reg.create_job("task_004")
    reg.write_line("task_004", "linha A")
    reg.write_line("task_004", "linha B")
    reg.write_line("task_004", "linha C")

    first = reg.poll_job("task_004", 0)
    assert first["lines"] == ["linha A", "linha B", "linha C"]
    assert first["next_offset"] > 0

    second = reg.poll_job("task_004", first["next_offset"])
    assert second["lines"] == []
    assert second["next_offset"] == first["next_offset"]


def test_poll_unknown_task_returns_done_false(reg):
    result = reg.poll_job("nonexistent_task", 0)
    assert result["done"] is True
    assert result["success"] is False
    assert result["lines"] == []
```

- [ ] **Step 2: Confirmar falha**

```bash
cd /home/andre/Documentos/projetos/loteria/lotofacil && source venv/bin/activate
pytest src/lotofacil/interface/painel/tests/test_treino_registry.py -v
```

Esperado: `AttributeError: 'TreinoRegistry' object has no attribute 'create_job'`

- [ ] **Step 3: Adicionar tabelas e métodos ao TreinoRegistry**

Substituir o conteúdo de `src/lotofacil/interface/painel/treino_registry.py`:

```python
"""SQLite registry for versioned training sessions and job output."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


_SCHEMA = """
CREATE TABLE IF NOT EXISTS treinos (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    tipo_config TEXT NOT NULL,
    parametros TEXT NOT NULL,
    arquivo_modelo TEXT,
    metricas TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    criado_em TEXT NOT NULL,
    concluido_em TEXT
);

CREATE TABLE IF NOT EXISTS job_output (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id  TEXT NOT NULL,
    text     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_status (
    task_id     TEXT PRIMARY KEY,
    done        INTEGER NOT NULL DEFAULT 0,
    success     INTEGER,
    finished_at TEXT
);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_job_output_task ON job_output(task_id, id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for key in ("parametros", "metricas"):
        if d.get(key):
            try:
                d[key] = json.loads(d[key])
            except Exception:
                pass
    return d


class TreinoRegistry:
    def __init__(self, db_path: Path) -> None:
        self._db = Path(db_path)
        self._db.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_SCHEMA)
            conn.executescript(_INDEXES)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db))
        conn.row_factory = sqlite3.Row
        return conn

    # ── Treinos ──────────────────────────────────────────────────

    def criar(self, treino_id: str, nome: str, tipo_config: str, parametros: dict) -> dict:
        row = {
            "id": treino_id,
            "nome": nome,
            "tipo_config": tipo_config,
            "parametros": json.dumps(parametros, ensure_ascii=False),
            "status": "running",
            "criado_em": _now(),
        }
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO treinos (id, nome, tipo_config, parametros, status, criado_em) "
                "VALUES (:id, :nome, :tipo_config, :parametros, :status, :criado_em)",
                row,
            )
        return self.buscar(treino_id)

    def atualizar_status(self, treino_id: str, status: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE treinos SET status = ? WHERE id = ?",
                (status, treino_id),
            )

    def registrar_modelo(self, treino_id: str, arquivo_modelo: str, metricas: dict) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE treinos SET arquivo_modelo = ?, metricas = ?, status = 'completed', concluido_em = ? WHERE id = ?",
                (str(arquivo_modelo), json.dumps(metricas, ensure_ascii=False), _now(), treino_id),
            )

    def marcar_falha(self, treino_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE treinos SET status = 'failed', concluido_em = ? WHERE id = ?",
                (_now(), treino_id),
            )

    def listar(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM treinos ORDER BY criado_em DESC"
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def buscar(self, treino_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM treinos WHERE id = ?", (treino_id,)
            ).fetchone()
        return _row_to_dict(row) if row else None

    # ── Job output ───────────────────────────────────────────────

    def create_job(self, task_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO job_status (task_id, done) VALUES (?, 0)",
                (task_id,),
            )

    def write_line(self, task_id: str, text: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO job_output (task_id, text) VALUES (?, ?)",
                (task_id, text),
            )

    def finish_job(self, task_id: str, success: bool) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE job_status SET done = 1, success = ?, finished_at = ? WHERE task_id = ?",
                (1 if success else 0, _now(), task_id),
            )

    def poll_job(self, task_id: str, offset: int) -> dict:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, text FROM job_output WHERE task_id = ? AND id > ? ORDER BY id LIMIT 100",
                (task_id, offset),
            ).fetchall()
            status_row = conn.execute(
                "SELECT done, success FROM job_status WHERE task_id = ?",
                (task_id,),
            ).fetchone()

        lines = [r["text"] for r in rows]
        next_offset = rows[-1]["id"] if rows else offset

        if status_row is None:
            return {"lines": lines, "done": True, "success": False, "next_offset": next_offset}

        done = bool(status_row["done"])
        result: dict = {"lines": lines, "done": done, "next_offset": next_offset}
        if done:
            result["success"] = bool(status_row["success"])
        return result
```

- [ ] **Step 4: Confirmar testes passando**

```bash
pytest src/lotofacil/interface/painel/tests/test_treino_registry.py -v
```

Esperado: 5 testes `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/interface/painel/treino_registry.py \
        src/lotofacil/interface/painel/tests/test_treino_registry.py
git commit -m "feat: TreinoRegistry — job_output + job_status tables e métodos de polling"
```

---

## Task 2: Refatorar `_run_command` no server.py

**Depends on:** Task 1

**Files:**
- Modify: `src/lotofacil/interface/painel/server.py`

- [ ] **Step 1: Remover TASKS dict**

Localizar e remover a linha:
```python
TASKS: dict[str, queue.Queue] = {}
```

Também remover o import `queue` se não for mais usado:
```python
import queue
```

- [ ] **Step 2: Substituir a assinatura e corpo de `_run_command`**

Localizar a função `_run_command` (linha ~845) e substituí-la integralmente por:

```python
def _run_command(
    task_id: str,
    registry: "TreinoRegistry",
    cmd: list[str],
    cwd: str,
    on_complete=None,
):
    LOGGER.info("TASK %s started cmd=%s cwd=%s", task_id, " ".join(cmd), cwd)

    cmd = [
        sys.executable if c == "python"
        else _LOTOFACIL_BIN if c == "lotofacil"
        else c
        for c in cmd
    ]
    env = {**os.environ, "PYTHONPATH": str(_SRC)}
    output_lines: list[str] = []
    ret = -1

    try:
        first = f"$ {' '.join(cmd)}"
        registry.write_line(task_id, first)
        output_lines.append(first)

        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        for line in iter(proc.stdout.readline, ""):
            clean = _strip_ansi(line.rstrip("\n"))
            LOGGER.info("TASK %s output: %s", task_id, clean)
            output_lines.append(clean)
            registry.write_line(task_id, clean)
        proc.stdout.close()
        ret = proc.wait()
        LOGGER.info("TASK %s finished exit_code=%s", task_id, ret)
        if ret == 0:
            registry.write_line(task_id, "")
            registry.write_line(task_id, "✅ Comando concluído com sucesso.")
            if on_complete:
                on_complete(success=True, output_lines=output_lines)
        else:
            registry.write_line(task_id, "")
            registry.write_line(task_id, f"⚠️  Comando finalizou com código {ret}.")
            if on_complete:
                on_complete(success=False, output_lines=output_lines)
    except Exception as e:
        LOGGER.exception("TASK %s failed", task_id)
        registry.write_line(task_id, f"❌ Erro: {e}")
        if on_complete:
            on_complete(success=False, output_lines=output_lines)
        ret = -1
    finally:
        registry.finish_job(task_id, ret == 0)
```

- [ ] **Step 3: Atualizar `api_generate` para usar registry em vez de queue**

Localizar `@app.route("/api/generate", methods=["POST"])` e substituir o corpo por:

```python
@app.route("/api/generate", methods=["POST"])
def api_generate():
    body = request.get_json(force=True) or {}
    action = body.get("action")
    if not action:
        return jsonify({"error": "Missing 'action' field"}), 400

    for cat in COMMANDS.values():
        for item in cat["items"]:
            if item["id"] == action:
                task_id = f"task_{int(time.time() * 1000)}_{action}"
                _registry.create_job(task_id)
                t = threading.Thread(
                    target=_run_command,
                    args=(task_id, _registry, item["cmd"], item["cwd"]),
                    daemon=True,
                )
                t.start()
                return jsonify({"task_id": task_id})
    return jsonify({"error": f"Unknown action: {action}"}), 400
```

- [ ] **Step 4: Atualizar `api_treinos_iniciar` para usar registry em vez de queue**

Localizar `@app.route("/api/treinos/iniciar", methods=["POST"])`. Dentro da função, substituir o bloco que cria a queue:

Remover:
```python
task_id = f"treino_{int(time.time() * 1000)}_{treino_id}"
q: queue.Queue = queue.Queue()
TASKS[task_id] = q

def on_done(success: bool, output_lines: list[str]):
    ...

t = threading.Thread(
    target=_run_command,
    args=(task_id, q, cmd, str(BASE_DIR)),
    kwargs={"on_complete": on_done},
    daemon=True,
)
t.start()
return jsonify({"treino_id": treino_id, "task_id": task_id})
```

Adicionar no lugar:
```python
task_id = f"treino_{int(time.time() * 1000)}_{treino_id}"
_registry.create_job(task_id)

def on_done(success: bool, output_lines: list[str]):
    if success:
        keras_path = _extract_model_path_from_output(output_lines)
        if not keras_path:
            keras_path = str(_LAB_MODELS_DIR / f"neural_{model_name}.keras")
        metricas = _read_meta_from_keras(keras_path)
        _registry.registrar_modelo(treino_id, keras_path, metricas)
        LOGGER.info("TREINO %s registered: %s", treino_id, keras_path)
    else:
        _registry.marcar_falha(treino_id)
        LOGGER.warning("TREINO %s failed", treino_id)

t = threading.Thread(
    target=_run_command,
    args=(task_id, _registry, cmd, str(BASE_DIR)),
    kwargs={"on_complete": on_done},
    daemon=True,
)
t.start()
return jsonify({"treino_id": treino_id, "task_id": task_id})
```

- [ ] **Step 5: Confirmar que os testes existentes ainda passam**

```bash
pytest src/lotofacil/interface/painel/tests/ -v
```

Esperado: todos os testes existentes `PASSED` (nenhum usa `TASKS` diretamente).

- [ ] **Step 6: Commit**

```bash
git add src/lotofacil/interface/painel/server.py
git commit -m "refactor: _run_command usa registry SQLite em vez de queue em memória"
```

---

## Task 3: Novo endpoint de polling + remover SSE

**Depends on:** Task 2

**Files:**
- Modify: `src/lotofacil/interface/painel/server.py`
- Test: `src/lotofacil/interface/painel/tests/test_server.py`

- [ ] **Step 1: Escrever testes com falha para o endpoint de polling**

Adicionar ao final de `src/lotofacil/interface/painel/tests/test_server.py`:

```python
from lotofacil.interface.painel.treino_registry import TreinoRegistry


@pytest.fixture
def reg(tmp_path):
    return TreinoRegistry(tmp_path / "test_treinos.db")


def test_api_jobs_poll_returns_lines(client, tmp_path, monkeypatch):
    reg = TreinoRegistry(tmp_path / "test_treinos.db")
    monkeypatch.setattr(server_module, "_registry", reg)
    reg.create_job("task_abc")
    reg.write_line("task_abc", "output line 1")
    reg.finish_job("task_abc", True)

    r = client.get("/api/jobs/task_abc/poll?offset=0")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["lines"] == ["output line 1"]
    assert data["done"] is True
    assert data["success"] is True


def test_api_jobs_poll_offset_advances(client, tmp_path, monkeypatch):
    reg = TreinoRegistry(tmp_path / "test_treinos.db")
    monkeypatch.setattr(server_module, "_registry", reg)
    reg.create_job("task_xyz")
    reg.write_line("task_xyz", "linha A")
    reg.write_line("task_xyz", "linha B")

    first = json.loads(client.get("/api/jobs/task_xyz/poll?offset=0").data)
    assert first["lines"] == ["linha A", "linha B"]

    second = json.loads(client.get(f"/api/jobs/task_xyz/poll?offset={first['next_offset']}").data)
    assert second["lines"] == []


def test_api_jobs_poll_unknown_task(client, tmp_path, monkeypatch):
    reg = TreinoRegistry(tmp_path / "test_treinos.db")
    monkeypatch.setattr(server_module, "_registry", reg)

    r = client.get("/api/jobs/nonexistent_task/poll?offset=0")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["done"] is True
    assert data["success"] is False
```

- [ ] **Step 2: Confirmar falha**

```bash
pytest src/lotofacil/interface/painel/tests/test_server.py::test_api_jobs_poll_returns_lines -v
```

Esperado: `404` ou `AssertionError` — o endpoint não existe ainda.

- [ ] **Step 3: Adicionar endpoint `GET /api/jobs/<task_id>/poll`**

No `server.py`, adicionar após o endpoint `api_treinos_comparar` (e antes de `api_stream` que será removido):

```python
@app.route("/api/jobs/<task_id>/poll")
def api_jobs_poll(task_id: str):
    offset = request.args.get("offset", default=0, type=int)
    return jsonify(_registry.poll_job(task_id, offset))
```

- [ ] **Step 4: Remover endpoint SSE**

Localizar e remover a função inteira `api_stream`:

```python
@app.route("/api/stream/<task_id>")
def api_stream(task_id):
    def generate():
        ...
    return Response(generate(), mimetype="text/event-stream")
```

Remover também o import `Response` de Flask se não for mais usado em nenhum outro lugar. Verificar antes:

```bash
grep -n "Response" src/lotofacil/interface/painel/server.py
```

Se só aparecia em `api_stream`, remover do import:
```python
from flask import Flask, jsonify, request, send_from_directory
```

- [ ] **Step 5: Confirmar testes**

```bash
pytest src/lotofacil/interface/painel/tests/ -v
```

Esperado: todos os testes `PASSED`, incluindo os 3 novos de polling.

- [ ] **Step 6: Commit**

```bash
git add src/lotofacil/interface/painel/server.py \
        src/lotofacil/interface/painel/tests/test_server.py
git commit -m "feat: endpoint /api/jobs/<id>/poll + remove SSE /api/stream"
```

---

## Task 4: Frontend — substituir EventSource por polling

**Depends on:** Task 3

**Files:**
- Modify: `src/lotofacil/interface/painel/static/dashboard.html`

- [ ] **Step 1: Substituir a função `listenStream` por `pollJob`**

Localizar a função `listenStream` (linha ~888) e substituí-la integralmente por:

```javascript
function pollJob(taskId, actionId, label) {
  let offset = 0;
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/api/jobs/${taskId}/poll?offset=${offset}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      data.lines.forEach(l => addConsoleLine(l));
      offset = data.next_offset;
      if (data.done) {
        clearInterval(interval);
        STATE.runningTasks.delete(actionId);
        updateButtonState(actionId, false);
        addConsoleLine('', 'sep');
        if (data.success) {
          addConsoleLine(`✅ ${label} concluído`, 'success');
          showToast(`${label} concluído com sucesso`, 'success');
        } else {
          addConsoleLine(`❌ ${label} falhou — veja o log acima`, 'error');
          showToast(`${label} falhou`, 'error');
        }
        if (STATE.activeTab === 'predicao') { loadPredictions(); }
        loadStatus();
      }
    } catch (e) {
      logClient('error', 'Erro ao buscar output do job', { taskId, error: e.message });
      addConsoleLine(`⚠️ Falha ao buscar output: ${e.message}`, 'warn');
    }
  }, 2000);
}
```

- [ ] **Step 2: Atualizar os dois call sites**

**Call site 1** — linha ~878, dentro do handler genérico de comandos:

Localizar:
```javascript
listenStream(data.task_id, actionId, label);
```

Substituir por:
```javascript
pollJob(data.task_id, actionId, label);
```

**Call site 2** — linha ~1575, dentro do handler de início de treino:

Localizar:
```javascript
listenStream(data.task_id, `treino_${data.treino_id}`, nome);
```

Substituir por:
```javascript
pollJob(data.task_id, `treino_${data.treino_id}`, nome);
```

- [ ] **Step 3: Confirmar que não restou nenhuma referência a `listenStream` ou `EventSource`**

```bash
grep -n "listenStream\|EventSource\|api/stream" \
  src/lotofacil/interface/painel/static/dashboard.html
```

Esperado: nenhum resultado.

- [ ] **Step 4: Commit**

```bash
git add src/lotofacil/interface/painel/static/dashboard.html
git commit -m "feat: dashboard usa polling /api/jobs/<id>/poll em vez de SSE"
```

---

## Task 5: Gunicorn timeout 120s → 600s no Dockerfile

**Files:**
- Modify: `Dockerfile`

> Esta task é independente e pode rodar em paralelo com a Task 1.

- [ ] **Step 1: Alterar o CMD no Dockerfile**

Localizar o bloco `CMD` no final do `Dockerfile`:

```dockerfile
CMD ["gunicorn", "lotofacil.interface.painel.server:app", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

Substituir `"--timeout", "120"` por `"--timeout", "600"`:

```dockerfile
CMD ["gunicorn", "lotofacil.interface.painel.server:app", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--timeout", "600", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

- [ ] **Step 2: Confirmar a mudança**

```bash
grep "timeout" Dockerfile
```

Esperado: `"--timeout", "600"`

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "fix: gunicorn timeout 120s → 600s para suportar treinos longos"
```

---

## Task 6: Rebuild + smoke test no EasyPanel

**Depends on:** Tasks 1–5 merged

- [ ] **Step 1: Fazer push do branch para o repositório remoto**

```bash
git push
```

- [ ] **Step 2: Disparar rebuild no EasyPanel**

No painel do EasyPanel, selecionar a aplicação e clicar em **Rebuild** (equivalente a `docker build --no-cache`). Isso garante que o TensorFlow seja instalado na nova imagem.

- [ ] **Step 3: Após o deploy, validar o endpoint de polling**

```bash
curl -s https://<seu-dominio>/api/jobs/nonexistent/poll?offset=0 | python3 -m json.tool
```

Esperado:
```json
{
    "done": true,
    "lines": [],
    "next_offset": 0,
    "success": false
}
```

- [ ] **Step 4: Validar um comando curto pelo dashboard**

Abrir o dashboard, clicar em **Status do DB** (comando rápido) e verificar:
- O log aparece linha a linha (com ~2s de delay)
- O botão desabilita durante a execução e reabilita ao final
- Aparece "✅ concluído" ou "❌ falhou" corretamente

- [ ] **Step 5: Iniciar um treino neural e verificar que não trava**

No dashboard, aba Predição, iniciar um treino com epochs=5 para teste rápido. Verificar:
- Output aparece no console via polling
- Não aparece mais "⚠️ Conexão perdida com o servidor"
- Ao final, o registro aparece na lista de treinos
