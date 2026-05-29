# SSE Streaming — Design Spec

**Data:** 2026-05-29  
**Status:** Aprovado  
**Limitação resolvida:** #3 — polling a 500ms em vez de Server-Sent Events

---

## Contexto

O mecanismo atual de streaming de output de jobs:
1. Frontend faz `GET /api/jobs/<id>/poll?offset=N` a cada 500ms via `setInterval`
2. Backend responde com `{lines: [...], done: bool, offset: N}`
3. Frontend acumula linhas no console

**Problemas:**
- 2 requests/segundo por job ativo — carga desnecessária
- Latência de até 500ms para exibir uma linha de output
- `setInterval` + `clearInterval` manual é frágil; vazamentos se o componente for destruído antes do job terminar

**SSE resolve:** conexão única, o servidor empurra linhas assim que saem do subprocess, zero polling.

---

## Design

### Backend: novo endpoint SSE

```python
@app.route("/api/jobs/<task_id>/stream")
def api_job_stream(task_id: str):
    def generate():
        offset = 0
        while True:
            result = _registry.poll_job(task_id, offset)
            for line in result["lines"]:
                yield f"data: {json.dumps({'text': line})}\n\n"
            offset = result["offset"]
            if result["done"]:
                yield "event: done\ndata: {}\n\n"
                return
            time.sleep(0.15)   # 150ms — 3× melhor que 500ms, sem busy-loop

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # nginx: sem buffering
        },
    )
```

**O endpoint `/api/jobs/<id>/poll` é mantido** — é usado pelos modelos em treino (`renderModLista` poll loop) e por compatibilidade. Não é removido neste spec.

### Frontend: substituir `pollJob()` por `EventSource`

A função `pollJob` em `dashboard.html` é chamada após `POST /api/generate`. Substituída por:

```javascript
function listenJob(taskId, actionId, label) {
  const es = new EventSource(`/api/jobs/${taskId}/stream`);

  es.onmessage = (e) => {
    const { text } = JSON.parse(e.data);
    if (text) addConsoleLine(text);
  };

  es.addEventListener('done', () => {
    es.close();
    _onJobFinished(actionId, label);
  });

  es.onerror = () => {
    es.close();
    addConsoleLine(`⚠️ Conexão interrompida para task ${taskId}`, 'warn');
    _onJobFinished(actionId, label, /*error=*/true);
  };
}
```

`_onJobFinished(actionId, label, error)` extrai a lógica atual de pós-conclusão: para timer, remove do `runningTasks`, exibe toast, chama refresh.

**A função `pollJob` atual é deletada.** O endpoint `/api/jobs/<id>/poll` é mantido apenas para o loop de polling dos modelos em treino (`_predState.pollingInterval`).

### Compatibilidade

| Caso | Mecanismo |
|------|-----------|
| Comandos CLI (`/api/generate`) | SSE via `listenJob()` |
| Treinos ML (modal de progresso) | Polling via `/api/jobs/<id>/poll` (inalterado) |
| Cancel de job | `POST /api/jobs/<id>/cancel` (inalterado) |

---

## Arquivos a modificar

| Arquivo | Mudança |
|---------|---------|
| `src/lotofacil/interface/painel/server.py` | Novo endpoint `GET /api/jobs/<id>/stream` (SSE) |
| `src/lotofacil/interface/painel/static/dashboard.html` | Substituir `pollJob()` por `listenJob()` usando `EventSource` |
| `src/lotofacil/interface/painel/tests/test_server.py` | Teste do endpoint SSE (gerador produz linhas + evento done) |

---

## Testes

```python
def test_api_job_stream_emite_linhas_e_done(client):
    # Cria job com output fixo, verifica que SSE emite data: {...} + event: done

def test_api_job_stream_job_inexistente_retorna_done_imediato(client):
    # SSE com task_id inválido deve emitir done imediatamente (job não existe = done)
```

---

## O que não muda

- Endpoint `/api/jobs/<id>/poll` — mantido para o loop de treino
- Endpoint `/api/jobs/<id>/cancel` — inalterado
- Lógica interna do `TreinoRegistry` — sem alterações
- Console, toast, timer no frontend — mesma lógica, só o gatilho muda
