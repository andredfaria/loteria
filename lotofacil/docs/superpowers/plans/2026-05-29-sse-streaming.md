# SSE Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o polling de 2 segundos de output de jobs CLI por Server-Sent Events, reduzindo latência e eliminando o setInterval frágil do frontend.

**Architecture:** Novo endpoint `GET /api/jobs/<id>/stream` envia linhas de `job_output` via SSE em loop com 150ms de sleep. Frontend usa `EventSource` em vez de `setInterval + fetch`. O endpoint `/api/jobs/<id>/poll` é mantido para o loop de treino ML já existente.

**Tech Stack:** Python 3.12, Flask `Response` + generator, `EventSource` (JS nativo), pytest.

---

## File Map

| Arquivo | Ação |
|---------|------|
| `src/lotofacil/interface/painel/server.py` | Adicionar endpoint SSE `/api/jobs/<id>/stream` |
| `src/lotofacil/interface/painel/static/dashboard.html` | Substituir `pollJob()` por `listenJob()` com `EventSource` |
| `src/lotofacil/interface/painel/tests/test_server.py` | Acrescentar 2 testes do endpoint SSE |

---

## Task 1: Endpoint SSE em `server.py`

**Files:**
- Modify: `src/lotofacil/interface/painel/server.py`

- [ ] **Step 1: Acrescentar 2 testes ao final de `test_server.py`**

```python
# ── SSE streaming ──────────────────────────────────────────────

def test_api_job_stream_emite_linhas_e_done(client, tmp_path, monkeypatch):
    """SSE endpoint emite linhas de output e finaliza com event: done."""
    from lotofacil.interface.painel.treino_registry import TreinoRegistry
    reg = TreinoRegistry(tmp_path / "test.db")
    reg.create_job("test_sse")
    reg.write_line("test_sse", "linha 1")
    reg.write_line("test_sse", "linha 2")
    reg.finish_job("test_sse", success=True)
    monkeypatch.setattr(server_module, "_registry", reg)

    resp = client.get("/api/jobs/test_sse/stream")
    assert resp.status_code == 200
    assert b"linha 1" in resp.data
    assert b"linha 2" in resp.data
    assert b"event: done" in resp.data


def test_api_job_stream_job_inexistente_retorna_done(client, tmp_path, monkeypatch):
    """SSE com task_id desconhecido emite event: done imediatamente."""
    from lotofacil.interface.painel.treino_registry import TreinoRegistry
    reg = TreinoRegistry(tmp_path / "test.db")
    monkeypatch.setattr(server_module, "_registry", reg)

    resp = client.get("/api/jobs/nao_existe/stream")
    assert resp.status_code == 200
    assert b"event: done" in resp.data
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd /home/andre/Documentos/projetos/loteria/lotofacil && source venv/bin/activate
pytest src/lotofacil/interface/painel/tests/test_server.py::test_api_job_stream_emite_linhas_e_done -v 2>&1 | tail -8
```

Expected: `404 NOT FOUND` (endpoint não existe ainda).

- [ ] **Step 3: Adicionar o endpoint SSE em `server.py`**

Adicionar a importação de `Response` no topo do arquivo Flask imports. Localizar:
```python
from flask import Flask, jsonify, request, send_from_directory
```

Substituir por:
```python
from flask import Flask, jsonify, request, send_from_directory, Response
```

Em seguida, inserir o endpoint ANTES do bloco `# ─── Main ──` (próximo ao final do arquivo, logo antes de `def main()`):

```python
@app.route("/api/jobs/<task_id>/stream")
def api_job_stream(task_id: str):
    def generate():
        offset = 0
        while True:
            result = _registry.poll_job(task_id, offset)
            for line in result["lines"]:
                yield f"data: {json.dumps({'text': line})}\n\n"
            offset = result["next_offset"]
            if result["done"]:
                yield "event: done\ndata: {}\n\n"
                return
            time.sleep(0.15)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 4: Rodar os 2 testes SSE**

```bash
pytest src/lotofacil/interface/painel/tests/test_server.py -v -k "stream" 2>&1 | tail -8
```

Expected: `2 passed`.

- [ ] **Step 5: Rodar suite completa**

```bash
pytest src/lotofacil/interface/painel/tests/test_server.py -v 2>&1 | tail -10
```

Expected: todos `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add src/lotofacil/interface/painel/server.py \
        src/lotofacil/interface/painel/tests/test_server.py
git commit -m "feat: add SSE streaming endpoint /api/jobs/<id>/stream

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Frontend — substituir `pollJob()` por `listenJob()`

**Files:**
- Modify: `src/lotofacil/interface/painel/static/dashboard.html`

- [ ] **Step 1: Substituir a chamada de `pollJob` por `listenJob`**

Localizar (linha ~1197):
```javascript
    pollJob(data.task_id, actionId, label);
```

Substituir por:
```javascript
    listenJob(data.task_id, actionId, label);
```

- [ ] **Step 2: Substituir a função `pollJob` pela nova `listenJob`**

Localizar o bloco completo da função `pollJob`:
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
        if (STATE.activeTab === 'modelos') { loadModelosAndRender(); }
        if (STATE.activeTab === 'coleta') { _renderColetaStats(); }
        loadStatus();
      }
    } catch (e) {
      logClient('error', 'Erro ao buscar output do job', { taskId, actionId, offset, error: e.message });
      addConsoleLine(`⚠️ Falha ao buscar output: ${e.message}`, 'warn');
    }
  }, 2000);
}
```

Substituir por:
```javascript
function listenJob(taskId, actionId, label) {
  const es = new EventSource(`/api/jobs/${taskId}/stream`);

  es.onmessage = (e) => {
    try {
      const { text } = JSON.parse(e.data);
      if (text) addConsoleLine(text);
    } catch (_) {}
  };

  es.addEventListener('done', () => {
    es.close();
    STATE.runningTasks.delete(actionId);
    updateButtonState(actionId, false);
    addConsoleLine('', 'sep');
    // success unknown from SSE — infer from console (no exit code in SSE)
    addConsoleLine(`✅ ${label} concluído`, 'success');
    showToast(`${label} concluído com sucesso`, 'success');
    if (STATE.activeTab === 'modelos') { loadModelosAndRender(); }
    if (STATE.activeTab === 'coleta') { _renderColetaStats(); }
    loadStatus();
  });

  es.onerror = () => {
    es.close();
    STATE.runningTasks.delete(actionId);
    updateButtonState(actionId, false);
    addConsoleLine(`⚠️ Conexão SSE interrompida para ${taskId}`, 'warn');
    showToast(`${label} — conexão interrompida`, 'warn');
    loadStatus();
  };
}
```

- [ ] **Step 3: Verificar que server.py importa OK**

```bash
python -c "from lotofacil.interface.painel import server; print('OK')"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add src/lotofacil/interface/painel/static/dashboard.html
git commit -m "feat: replace pollJob setInterval with EventSource SSE in dashboard

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Self-Review

- ✅ `/api/jobs/<id>/poll` mantido — o loop de treino ML continua usando polling (não é alterado)
- ✅ `Response` movido para import global (antes estava inline em outro endpoint na linha 845 — o import inline pode ser removido ou mantido; ambos funcionam)
- ✅ `es.close()` chamado em `done` e `onerror` — sem vazamento de EventSource
- ✅ `time.sleep(0.15)` no gerador SSE (150ms) — 13× melhor que o polling de 2000ms anterior, sem busy-loop
- ✅ `generate()` é um generator Python — Flask consome lazily e envia chunks conforme produzidos
- ⚠️ `success` não está disponível via SSE (o generator não tem acesso ao exit code). O `event: done` apenas sinaliza conclusão. Para saber se houve erro, o usuário vê o output no console. Se precisar de `success/failure` toast diferenciado, seria necessário adicionar o `success` ao evento `done` (ex: `data: {"success": true}`). Esse refinamento está fora do escopo deste plano.
