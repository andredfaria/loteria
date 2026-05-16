# Design: Correção TensorFlow + SSE success/failure (Abordagem B)

**Data:** 2026-05-15  
**Escopo:** Três correções cirúrgicas na integração frontend↔CLI do dashboard de treino neural.

---

## Contexto

O treinamento neural via dashboard falha com `ModuleNotFoundError: No module named 'tensorflow'` porque a imagem Docker foi construída antes do TF ser adicionado ao `pyproject.toml`. Além disso, o frontend sempre exibe "✅ concluído" no evento SSE `done`, independente de o comando ter falhado.

---

## Mudanças

### 1 — Infra Docker

**Arquivo:** `Dockerfile`

O `pyproject.toml` já lista `tensorflow>=2.16.0` nas dependências principais. O `Dockerfile` já executa `pip install -e ".[dev]"`, o que deveria instalar TF. O problema é a imagem desatualizada.

Adicionar `libgomp1` ao `apt-get` (necessário para TF em imagem slim) e garantir rebuild:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
```

**Ação:** `docker-compose build --no-cache` após o commit.

---

### 2 — Verificação antecipada de TF no CLI

**Arquivo:** `src/lotofacil/experimentos/main.py` — função `train()`

Adicionar import check no início da função, antes de qualquer processamento de dados:

```python
try:
    import tensorflow  # noqa: F401
except ImportError:
    console.print("[red]Erro:[/red] TensorFlow não encontrado.")
    console.print("Reconstrua a imagem Docker: docker-compose build --no-cache")
    raise typer.Exit(1)
```

**Por quê:** Elimina o stack trace Python e substitui por mensagem acionável. O exit code 1 já existia — só a mensagem muda.

---

### 3 — SSE `done` com flag de sucesso

**Arquivo:** `src/lotofacil/interface/painel/server.py`

**`_run_command`:** Trocar `q.put(None)` (sentinel atual) por um dict com status:

```python
# antes
q.put(None)

# depois
q.put({"_done": True, "success": ret == 0})
```

**`api_stream`:** Detectar o sentinel e incluir `success` no evento `done`:

```python
# antes
if line is None:
    yield f"event: done\ndata: {json.dumps({'type': 'done'})}\n\n"
    break

# depois
if isinstance(line, dict) and line.get("_done"):
    yield f"event: done\ndata: {json.dumps({'type': 'done', 'success': line['success']})}\n\n"
    break
```

**Arquivo:** `src/lotofacil/interface/painel/static/dashboard.html`

**`listenStream`:** Usar `data.success` para decidir a mensagem:

```javascript
// antes
evtSource.addEventListener('done', () => {
  // ...
  addConsoleLine(`✅ ${label} concluído`, 'success');
  showToast(`${label} concluído com sucesso`, 'success');
});

// depois
evtSource.addEventListener('done', (event) => {
  const data = JSON.parse(event.data);
  evtSource.close();
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
});
```

---

## Arquivos alterados

| Arquivo | Tipo de mudança |
|---|---|
| `Dockerfile` | Adicionar `libgomp1` ao apt-get |
| `src/lotofacil/experimentos/main.py` | Import check de TF no início de `train()` |
| `src/lotofacil/interface/painel/server.py` | Sentinel com `success` em `_run_command` + `api_stream` |
| `src/lotofacil/interface/painel/static/dashboard.html` | Handler `done` usa `data.success` |

---

## Fora do escopo

- `api_treinos/gerar` carrega TF em processo (problema 3 identificado na revisão) — deixado para depois, funciona quando TF está instalado.
- Timeout em tarefas longas — não é crítico agora.
- Preflight endpoint — não necessário com TF garantido no Docker.
