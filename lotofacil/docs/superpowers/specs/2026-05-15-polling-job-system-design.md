# Design: Sistema de Jobs com Polling (substitui SSE)

**Data:** 2026-05-15
**Escopo:** Substituir SSE + TASKS dict em memória por polling com output persistido em SQLite. Corrige treinamento no EasyPanel.

---

## Contexto e Problemas

O dashboard executa comandos longos (treino neural, coleta, predição) via SSE. O mecanismo atual tem três falhas que impedem o treinamento de funcionar no EasyPanel:

| # | Problema | Causa | Impacto |
|---|---|---|---|
| P1 | TensorFlow não instalado na imagem | Imagem buildada antes do TF ser adicionado | Treino falha imediatamente com ModuleNotFoundError |
| P3 | TASKS dict em memória + 2 workers Gunicorn | POST pode cair no worker A, GET no worker B | "Task not found" ~50% das tentativas |
| P4 | Timeout de 120s no Gunicorn | Treino longo excede o timeout | Conexão SSE cai no meio do treino |

O problema de persistência de volumes (P2) já foi resolvido pelo usuário via configuração no EasyPanel.

---

## Decisão: Polling em vez de SSE

O SSE exige estado em memória compartilhado entre workers. Para um deploy VPS via EasyPanel (Docker sem orquestração), polling com SQLite é mais simples e resiliente:

- Qualquer worker responde qualquer requisição de poll
- Output persiste mesmo se o container reiniciar durante o treino
- Sem dependências de infraestrutura extra (Redis descartado)
- 2s de delay é imperceptível para jobs que levam minutos

---

## Novo Fluxo

```
Antes (SSE):
  POST /api/treinos/iniciar  → cria queue em TASKS[task_id] (memória worker A)
  GET  /api/stream/<task_id> → pode bater no worker B → "Task not found"

Depois (Polling):
  POST /api/treinos/iniciar  → cria registro em job_status, inicia thread
  Thread                     → grava cada linha em job_output (SQLite)
  GET  /api/jobs/<id>/poll?offset=N (a cada 2s) → lê linhas do SQLite
```

---

## Backend

### Schema SQLite — novas tabelas em `treinos.db`

```sql
CREATE TABLE IF NOT EXISTS job_output (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id  TEXT NOT NULL,
    text     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_job_output_task ON job_output(task_id, id);

CREATE TABLE IF NOT EXISTS job_status (
    task_id     TEXT PRIMARY KEY,
    done        INTEGER NOT NULL DEFAULT 0,
    success     INTEGER,           -- NULL enquanto running, 1=ok, 0=fail
    finished_at TEXT
);
```

Essas tabelas ficam no mesmo arquivo `treinos.db` gerenciado por `TreinoRegistry`. O schema é inicializado no construtor junto com a tabela `treinos` existente.

### `TreinoRegistry` — novos métodos

```python
def create_job(self, task_id: str) -> None
def write_line(self, task_id: str, text: str) -> None
def finish_job(self, task_id: str, success: bool) -> None
def poll_job(self, task_id: str, offset: int) -> dict
# retorna: { lines, done, success, next_offset }
```

`poll_job` executa:
```sql
SELECT id, text FROM job_output
WHERE task_id = ? AND id > ?
ORDER BY id
LIMIT 100
```

### `_run_command` refatorado

Recebe `task_id` e `registry` em vez de `queue.Queue`. Em vez de `q.put(line)` chama `registry.write_line(task_id, line)`. Ao final chama `registry.finish_job(task_id, ret == 0)`.

`TASKS: dict[str, queue.Queue]` é removido completamente do `server.py`.

### Endpoints alterados

| Antes | Depois |
|---|---|
| `GET /api/stream/<task_id>` (SSE) | removido |
| — | `GET /api/jobs/<task_id>/poll?offset=<n>` (novo) |

Resposta do poll:
```json
{ "lines": ["linha1", "linha2"], "done": false, "next_offset": 42 }
{ "lines": [], "done": true, "success": true, "next_offset": 50 }
```

`next_offset` é sempre o `id` do último registro retornado. Se `lines` está vazio, `next_offset` é igual ao `offset` recebido (sem avanço). O cliente nunca precisa deduzir — usa o `next_offset` da resposta diretamente.

Os endpoints `POST /api/generate` e `POST /api/treinos/iniciar` mantêm a mesma interface — só trocam a implementação interna (queue → SQLite).

### Gunicorn

```dockerfile
CMD ["gunicorn", "lotofacil.interface.painel.server:app",
     "--bind", "0.0.0.0:5000",
     "--workers", "2",
     "--timeout", "600",
     "--access-logfile", "-",
     "--error-logfile", "-"]
```

`--timeout` sobe de 120 para 600 segundos. `--workers 2` é mantido (agora seguro com SQLite).

---

## Frontend (`dashboard.html`)

### Função `pollJob` substitui `listenStream`/`EventSource`

```javascript
async function pollJob(taskId, label, actionId) {
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
        if (STATE.activeTab === 'predicao') loadPredictions();
        loadStatus();
      }
    } catch (e) {
      // Erro de rede: não cancela o poll, tenta de novo em 2s
      addConsoleLine(`⚠️ Falha ao buscar output: ${e.message}`, 'warn');
    }
  }, 2000);
}
```

Todos os lugares que hoje chamam `listenStream(taskId, ...)` passam a chamar `pollJob(taskId, ...)`. O `EventSource` é removido completamente.

### Reconexão automática

Como o polling é stateless, uma queda de rede de até o intervalo de poll (2s) é transparente. Se a aba for fechada e reaberta, o output pode ser recuperado enquanto o job estiver no SQLite (sem prazo de expiração definido).

---

## Infraestrutura

### Docker — rebuild obrigatório

O `libgomp1` já está no `Dockerfile` (adicionado no spec `2026-05-15-tensorflow-sse-integration-fix-design.md`). Nenhuma mudança adicional no Dockerfile além do timeout do Gunicorn.

**Ação pós-deploy:** Rebuild no EasyPanel (equivalente a `docker-compose build --no-cache`).

---

## Arquivos alterados

| Arquivo | Mudança |
|---|---|
| `src/lotofacil/interface/painel/treino_registry.py` | Adicionar tabelas `job_output` + `job_status` e métodos `create_job`, `write_line`, `finish_job`, `poll_job` |
| `src/lotofacil/interface/painel/server.py` | Refatorar `_run_command` (queue→SQLite), remover `TASKS` dict, remover `/api/stream`, adicionar `/api/jobs/<id>/poll`, atualizar `api_generate` e `api_treinos_iniciar` |
| `src/lotofacil/interface/painel/static/dashboard.html` | Substituir `EventSource`/`listenStream` por `pollJob` |
| `Dockerfile` | `--timeout 120` → `--timeout 600` no CMD do Gunicorn |

---

## Fora do escopo

- `api_treinos/<id>/gerar` carrega TF em processo — funciona quando TF está instalado, não crítico agora.
- Limpeza/expiração de `job_output` antigas — não necessário agora.
- Autenticação no dashboard — não solicitado.
