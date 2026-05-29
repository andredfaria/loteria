# Training Modal Improvements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir os 5 bugs no modal de treinamento: barra de progresso que trava em 0%, log sem informação, path do modelo não capturado, ausência de botão "Fechar" e sem indicador de tempo decorrido.

**Architecture:** Três arquivos alterados independentemente. (1) `neural_modular.py` adiciona callback Keras que emite `EPOCH_PROGRESS: N/M loss=X val_loss=Y` a cada epoch. (2) `server.py` filtra ruído de TF antes de escrever no log e corrige parsing do path multiline. (3) `dashboard.html` atualiza o parser de progresso, adiciona botão "Fechar" com CSS, timer de tempo decorrido e comportamento pós-treino sem auto-close.

**Tech Stack:** Python 3.12 + TensorFlow/Keras, Flask, JavaScript vanilla.

---

## File Map

| Arquivo | Ação |
|---------|------|
| `src/lotofacil/experimentos/models/neural_modular.py` | Adicionar `_EpochProgressCallback`, incluir no `model.fit()` |
| `src/lotofacil/interface/painel/server.py` | Fix `_extract_model_path_from_output` + regex `_TF_NOISE_RE` |
| `src/lotofacil/interface/painel/static/dashboard.html` | Fechar btn + CSS + timer + parser `EPOCH_PROGRESS:` + `_finishTreinoModal` + `closeTreinoModal` |

---

## Task 1: `neural_modular.py` — Callback de progresso por epoch

**Files:**
- Modify: `src/lotofacil/experimentos/models/neural_modular.py`

- [ ] **Step 1: Inserir a classe `_EpochProgressCallback` antes da classe `NeuralModular`**

Localizar a linha `logger = logging.getLogger(__name__)` (linha ~30). Inserir logo **após** ela:

```python
class _EpochProgressCallback(tf.keras.callbacks.Callback):
    """Emits parseable epoch progress to stdout for the dashboard modal."""

    def __init__(self, total_epochs: int) -> None:
        super().__init__()
        self._total = total_epochs

    def on_epoch_end(self, epoch, logs=None) -> None:
        logs = logs or {}
        e = epoch + 1
        loss = logs.get("loss", 0.0)
        val_loss = logs.get("val_loss", 0.0)
        print(
            f"EPOCH_PROGRESS: {e}/{self._total} "
            f"loss={loss:.4f} val_loss={val_loss:.4f}",
            flush=True,
        )
```

**Por que `flush=True`:** o subprocess captura stdout com `bufsize=1` (line-buffered), mas `print()` pode ainda bufferizar. `flush=True` força a entrega imediata de cada linha.

- [ ] **Step 2: Adicionar o callback ao `model.fit()`**

Localizar o bloco `callbacks = [...]` dentro do método `fit` (linhas ~104-114). Está assim:

```python
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=self._hp_val("LSTM_PATIENCE"),
                restore_best_weights=True, min_delta=1e-5,
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss", factor=self._hp_val("LSTM_LR_FACTOR"),
                patience=self._hp_val("LSTM_LR_PATIENCE"),
                min_lr=self._hp_val("LSTM_LR_MIN"), verbose=0,
            ),
        ]
```

Substituir por:

```python
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=self._hp_val("LSTM_PATIENCE"),
                restore_best_weights=True, min_delta=1e-5,
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss", factor=self._hp_val("LSTM_LR_FACTOR"),
                patience=self._hp_val("LSTM_LR_PATIENCE"),
                min_lr=self._hp_val("LSTM_LR_MIN"), verbose=0,
            ),
            _EpochProgressCallback(self._hp_val("LSTM_EPOCHS")),
        ]
```

- [ ] **Step 3: Verificar que a importação de `tf` está disponível no escopo**

A classe `_EpochProgressCallback` usa `tf.keras.callbacks.Callback`. O import de `tf` é feito dentro do método `fit()` (lazy import). Verificar se há `import tensorflow as tf` no topo do arquivo ou se é importado lazy. Se for lazy (dentro do método), mover a classe `_EpochProgressCallback` para **dentro** do método `fit()`, logo antes de `callbacks = [...]`:

```python
    def fit(self, draws: list, *, ...):
        ...
        import tensorflow as tf   # já existe nesta linha

        class _EpochProgressCallback(tf.keras.callbacks.Callback):
            def __init__(self, total_epochs: int) -> None:
                super().__init__()
                self._total = total_epochs

            def on_epoch_end(self, epoch, logs=None) -> None:
                logs = logs or {}
                e = epoch + 1
                loss = logs.get("loss", 0.0)
                val_loss = logs.get("val_loss", 0.0)
                print(
                    f"EPOCH_PROGRESS: {e}/{self._total} "
                    f"loss={loss:.4f} val_loss={val_loss:.4f}",
                    flush=True,
                )

        callbacks = [
            ...
            _EpochProgressCallback(self._hp_val("LSTM_EPOCHS")),
        ]
```

- [ ] **Step 4: Verificar sintaxe**

```bash
cd /home/andre/Documentos/projetos/loteria/lotofacil && source venv/bin/activate
python -c "from lotofacil.experimentos.models.neural_modular import NeuralModular; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/experimentos/models/neural_modular.py
git commit -m "feat: add EpochProgressCallback to neural_modular for dashboard progress bar

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: `server.py` — Fix path multiline + filtro ruído TF

**Files:**
- Modify: `src/lotofacil/interface/painel/server.py`

- [ ] **Step 1: Adicionar testes para `_extract_model_path_from_output`**

Acrescentar ao final de `src/lotofacil/interface/painel/tests/test_server.py`:

```python
# ── _extract_model_path_from_output ──────────────────────────────

def test_extract_path_same_line():
    """Path na mesma linha que o prefixo."""
    lines = ["TREINO_MODELO_PATH: /home/user/models/neural_abc.keras"]
    result = server_module._extract_model_path_from_output(lines)
    assert result == "/home/user/models/neural_abc.keras"


def test_extract_path_next_line():
    """Path na linha seguinte (line wrapping)."""
    lines = [
        "Saved: neural_test.keras",
        "TREINO_MODELO_PATH: ",
        "/home/user/models/neural_test.keras",
    ]
    result = server_module._extract_model_path_from_output(lines)
    assert result == "/home/user/models/neural_test.keras"


def test_extract_path_not_found():
    """Sem prefixo retorna None."""
    lines = ["Config: base", "Training... (this may take a while)"]
    result = server_module._extract_model_path_from_output(lines)
    assert result is None
```

- [ ] **Step 2: Rodar para confirmar que o teste multiline falha**

```bash
pytest src/lotofacil/interface/painel/tests/test_server.py::test_extract_path_next_line -v 2>&1 | tail -8
```

Expected: `FAILED` — retorna `""` em vez do path.

- [ ] **Step 3: Corrigir `_extract_model_path_from_output` em `server.py`**

Localizar a função `_extract_model_path_from_output` (linha ~1115). Está assim:

```python
def _extract_model_path_from_output(lines: list[str]) -> str | None:
    for line in lines:
        if line.startswith("TREINO_MODELO_PATH:"):
            return line.split(":", 1)[1].strip()
    return None
```

Substituir por:

```python
def _extract_model_path_from_output(lines: list[str]) -> str | None:
    for i, line in enumerate(lines):
        if line.startswith("TREINO_MODELO_PATH:"):
            rest = line.split(":", 1)[1].strip()
            if rest:
                return rest
            # path está na próxima linha por line wrapping
            if i + 1 < len(lines):
                return lines[i + 1].strip()
    return None
```

- [ ] **Step 4: Rodar os 3 testes**

```bash
pytest src/lotofacil/interface/painel/tests/test_server.py -v -k "extract_path" 2>&1 | tail -8
```

Expected: `3 passed`.

- [ ] **Step 5: Adicionar regex `_TF_NOISE_RE` e aplicar em `_run_command`**

Localizar o bloco de constantes no início do arquivo (próximo às outras constantes como `_ANSI_RE`, `_procs`, `_freq_cache`). Adicionar após `_ANSI_RE`:

```python
_TF_NOISE_RE = re.compile(
    r"^(WARNING: All log messages|I\d{4} |W\d{4} |Skipping registering)"
)
```

Localizar dentro de `_run_command` o loop de leitura (linha ~1069-1073):

```python
        for line in iter(proc.stdout.readline, ""):
            clean = _strip_ansi(line.rstrip("\n"))
            LOGGER.info("TASK %s output: %s", task_id, clean)
            output_lines.append(clean)
            registry.write_line(task_id, clean)
```

Substituir por:

```python
        for line in iter(proc.stdout.readline, ""):
            clean = _strip_ansi(line.rstrip("\n"))
            LOGGER.info("TASK %s output: %s", task_id, clean)
            output_lines.append(clean)
            if not _TF_NOISE_RE.match(clean):
                registry.write_line(task_id, clean)
```

**Importante:** `output_lines.append(clean)` continua antes do filtro — o `_extract_model_path_from_output` ainda consegue encontrar o path mesmo com o filtro (pois o filtro só afeta o que vai para o log do modal, não a lista interna).

- [ ] **Step 6: Rodar suite completa do server**

```bash
pytest src/lotofacil/interface/painel/tests/test_server.py -q 2>&1 | tail -5
```

Expected: todos passam.

- [ ] **Step 7: Commit**

```bash
git add src/lotofacil/interface/painel/server.py \
        src/lotofacil/interface/painel/tests/test_server.py
git commit -m "fix: extract model path from next line + filter TF noise from training log

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: `dashboard.html` — Modal UI completo

**Files:**
- Modify: `src/lotofacil/interface/painel/static/dashboard.html`

### Mudanças no HTML e CSS

- [ ] **Step 1: Adicionar botão "Fechar" no HTML do modal**

Localizar (linha ~827-829):

```html
    <div class="treino-modal-footer">
      <button class="treino-cancel-btn" id="treinoCancelBtn" onclick="cancelTreino()">✕ Cancelar</button>
    </div>
```

Substituir por:

```html
    <div class="treino-modal-footer">
      <button class="treino-cancel-btn" id="treinoCancelBtn" onclick="cancelTreino()">✕ Cancelar</button>
      <button class="treino-close-btn" id="treinoCloseBtn" onclick="closeTreinoModal()" disabled>✓ Fechar</button>
    </div>
```

- [ ] **Step 2: Adicionar CSS para o botão "Fechar"**

Localizar (linha ~677):

```css
  .treino-cancel-btn:hover { background: rgba(248,113,113,0.2); }
```

Inserir logo depois:

```css
  .treino-close-btn {
    padding: 0.35rem 0.9rem; border-radius: var(--radius);
    border: 1px solid var(--green); background: rgba(74,222,128,0.1);
    color: var(--green); font-size: 0.78rem; cursor: pointer;
    transition: all var(--transition); margin-left: 0.5rem;
  }
  .treino-close-btn:hover:not(:disabled) { background: rgba(74,222,128,0.2); }
  .treino-close-btn:disabled { opacity: 0.35; cursor: not-allowed; }
```

### Mudanças no JavaScript

- [ ] **Step 3: Atualizar `openTreinoModal` para habilitar/desabilitar botões e adicionar timer**

Localizar a função `openTreinoModal` (linha ~3110). Está assim:

```javascript
function openTreinoModal(taskId, configLabel, epochsHint) {
  _treinoTaskId = taskId;
  _treinoPollOffset = 0;
  _treinoTotalEpochs = epochsHint || parseInt(document.getElementById('predEpocas')?.value) || 100;
  _treinoEpochLog = [];

  document.getElementById('treinoModalTitle').textContent = `Treinando (${configLabel})…`;
  document.getElementById('treinoModalStatus').textContent = '';
  document.getElementById('treinoProgressFill').style.width = '0%';
  document.getElementById('treinoEpochLabel').textContent = 'Iniciando…';
  document.getElementById('treinoLog').innerHTML = '';
  document.getElementById('treinoCancelBtn').disabled = false;
  document.getElementById('treinoModalOverlay').classList.add('visible');

  _treinoPoller = setInterval(() => _pollTreino(), 2000);
}
```

Substituir por:

```javascript
function openTreinoModal(taskId, configLabel, epochsHint) {
  _treinoTaskId = taskId;
  _treinoPollOffset = 0;
  _treinoTotalEpochs = epochsHint || parseInt(document.getElementById('predEpocas')?.value) || 100;
  _treinoEpochLog = [];

  document.getElementById('treinoModalTitle').textContent = `Treinando (${configLabel})…`;
  document.getElementById('treinoModalStatus').textContent = 'Em andamento · 00:00';
  document.getElementById('treinoProgressFill').style.width = '0%';
  document.getElementById('treinoProgressFill').style.background = '';
  document.getElementById('treinoEpochLabel').textContent = 'Iniciando…';
  document.getElementById('treinoLog').innerHTML = '';
  document.getElementById('treinoCancelBtn').disabled = false;
  document.getElementById('treinoCloseBtn').disabled = true;
  document.getElementById('treinoModalOverlay').classList.add('visible');

  // Timer de tempo decorrido
  const _modalStart = Date.now();
  window._treinoElapsedTimer = setInterval(() => {
    if (!_treinoPoller) { clearInterval(window._treinoElapsedTimer); return; }
    const sec = Math.floor((Date.now() - _modalStart) / 1000);
    const mm = String(Math.floor(sec / 60)).padStart(2, '0');
    const ss = String(sec % 60).padStart(2, '0');
    document.getElementById('treinoModalStatus').textContent = `Em andamento · ${mm}:${ss}`;
  }, 1000);

  _treinoPoller = setInterval(() => _pollTreino(), 2000);
}
```

- [ ] **Step 4: Substituir `_updateEpochFromLog` pelo parser do novo formato**

Localizar a função `_updateEpochFromLog` (linha ~3164). Está assim:

```javascript
function _updateEpochFromLog(lines) {
  for (const line of [...lines].reverse()) {
    const m = line.match(/[Ee]poch[\s:]+(\d+)[\s\/\\]+(\d+)/);
    if (m) {
      const cur = parseInt(m[1]);
      const total = parseInt(m[2]) || _treinoTotalEpochs;
      const pct = Math.min(100, Math.round((cur / total) * 100));
      document.getElementById('treinoProgressFill').style.width = `${pct}%`;

      // ETA calculation using last 5 epoch intervals
      _treinoEpochLog.push({ epoch: cur, ts: Date.now() });
      if (_treinoEpochLog.length > 6) _treinoEpochLog.shift();
      let etaStr = '';
      if (_treinoEpochLog.length >= 2) {
        const samples = _treinoEpochLog;
        const msPerEpoch = (samples[samples.length-1].ts - samples[0].ts) / (samples[samples.length-1].epoch - samples[0].epoch);
        if (msPerEpoch > 0 && cur < total) {
          const remSec = Math.round(((total - cur) * msPerEpoch) / 1000);
          etaStr = remSec < 60 ? ` · ETA ${remSec}s` : ` · ETA ${Math.ceil(remSec/60)}min`;
        }
      }
      document.getElementById('treinoEpochLabel').textContent = `Epoch ${cur}/${total} · ${pct}%${etaStr}`;
      return;
    }
  }
}
```

Substituir integralmente por:

```javascript
function _updateEpochFromLog(lines) {
  for (const line of [...lines].reverse()) {
    const m = line.match(
      /EPOCH_PROGRESS:\s*(\d+)\/(\d+)\s+loss=([\d.]+)\s+val_loss=([\d.]+)/
    );
    if (!m) continue;
    const cur = parseInt(m[1]), total = parseInt(m[2]);
    const valLoss = parseFloat(m[4]);
    const pct = Math.min(100, Math.round((cur / total) * 100));

    document.getElementById('treinoProgressFill').style.width = `${pct}%`;

    _treinoEpochLog.push({ epoch: cur, ts: Date.now() });
    if (_treinoEpochLog.length > 6) _treinoEpochLog.shift();
    let etaStr = '';
    if (_treinoEpochLog.length >= 2) {
      const s = _treinoEpochLog;
      const msPerEpoch = (s.at(-1).ts - s[0].ts) / (s.at(-1).epoch - s[0].epoch);
      if (msPerEpoch > 0 && cur < total) {
        const remSec = Math.round(((total - cur) * msPerEpoch) / 1000);
        etaStr = remSec < 60 ? ` · ETA ${remSec}s` : ` · ETA ${Math.ceil(remSec/60)}min`;
      }
    }
    document.getElementById('treinoEpochLabel').textContent =
      `Epoch ${cur}/${total} · ${pct}% · val_loss: ${valLoss.toFixed(4)}${etaStr}`;
    return;
  }
}
```

- [ ] **Step 5: Substituir `_finishTreinoModal` para não fechar sozinho**

Localizar `_finishTreinoModal` (linha ~3191). Está assim:

```javascript
function _finishTreinoModal(success) {
  const title = document.getElementById('treinoModalTitle');
  const status = document.getElementById('treinoModalStatus');
  const fill = document.getElementById('treinoProgressFill');
  document.getElementById('treinoCancelBtn').disabled = true;

  if (success) {
    title.textContent = '✅ Treino concluído';
    fill.style.width = '100%';
    fill.style.background = 'var(--green)';
    status.textContent = 'Recarregando modelos…';
    if (STATE.activeTab !== 'modelos') {
      showToast('✅ Treino concluído! Acesse a aba Modelos para ver o resultado.', 'success');
    }
    setTimeout(() => {
      closeTreinoModal();
      loadModelosAndRender();
      showModelosSubTab('lista');
    }, 1800);
  } else {
    title.textContent = '❌ Treino falhou';
    status.textContent = 'Veja o log para detalhes';
    document.getElementById('treinoCancelBtn').textContent = 'Fechar';
    document.getElementById('treinoCancelBtn').disabled = false;
    document.getElementById('treinoCancelBtn').onclick = closeTreinoModal;
    if (STATE.activeTab !== 'modelos') {
      showToast('❌ Treino falhou. Verifique o log na aba Modelos.', 'error');
    }
  }
}
```

Substituir integralmente por:

```javascript
function _finishTreinoModal(success) {
  clearInterval(window._treinoElapsedTimer);
  const title = document.getElementById('treinoModalTitle');
  const status = document.getElementById('treinoModalStatus');
  const fill = document.getElementById('treinoProgressFill');
  document.getElementById('treinoCancelBtn').disabled = true;
  document.getElementById('treinoCloseBtn').disabled = false;

  if (success) {
    title.textContent = '✅ Treino concluído';
    fill.style.width = '100%';
    fill.style.background = 'var(--green)';
    status.textContent = 'Modelo salvo. Clique Fechar para continuar.';
    showToast('✅ Treino concluído! Veja o resultado e clique Fechar.', 'success');
  } else {
    title.textContent = '❌ Treino falhou';
    status.textContent = 'Veja o log para detalhes.';
    showToast('❌ Treino falhou. Verifique o log no modal.', 'error');
  }
}
```

- [ ] **Step 6: Atualizar `closeTreinoModal` para navegar para Lista após sucesso**

Localizar `closeTreinoModal` (linha ~3233). Está assim:

```javascript
function closeTreinoModal() {
  document.getElementById('treinoModalOverlay').classList.remove('visible');
  const btn = document.getElementById('modTreinoBtn');
  if (btn) { btn.disabled = false; btn.textContent = '▶ Iniciar Treino'; }
  document.getElementById('treinoCancelBtn').onclick = cancelTreino;
  document.getElementById('treinoCancelBtn').textContent = '✕ Cancelar';
  _treinoTaskId = null;
  _treinoPollOffset = 0;
}
```

Substituir por:

```javascript
function closeTreinoModal() {
  clearInterval(window._treinoElapsedTimer);
  const wasSuccess = document.getElementById('treinoModalTitle').textContent.includes('✅');
  document.getElementById('treinoModalOverlay').classList.remove('visible');
  const btn = document.getElementById('modTreinoBtn');
  if (btn) { btn.disabled = false; btn.textContent = '▶ Iniciar Treino'; }
  document.getElementById('treinoCancelBtn').disabled = false;
  document.getElementById('treinoCancelBtn').textContent = '✕ Cancelar';
  document.getElementById('treinoCloseBtn').disabled = true;
  _treinoTaskId = null;
  _treinoPollOffset = 0;
  if (wasSuccess) {
    loadModelosAndRender();
    showModelosSubTab('lista');
  }
}
```

- [ ] **Step 7: Verificar importação do server**

```bash
cd /home/andre/Documentos/projetos/loteria/lotofacil && source venv/bin/activate
python -c "from lotofacil.interface.painel import server; print('OK')"
```

Expected: `OK`

- [ ] **Step 8: Rodar suite completa de testes**

```bash
pytest src/lotofacil/interface/painel/tests/ -q 2>&1 | tail -5
```

Expected: todos passam.

- [ ] **Step 9: Commit**

```bash
git add src/lotofacil/interface/painel/static/dashboard.html
git commit -m "feat: improve training modal — progress bar, Fechar button, timer, no auto-close

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- ✅ Callback `EPOCH_PROGRESS:` — Task 1
- ✅ Fix path multiline — Task 2 + teste
- ✅ Filtro ruído TF `_TF_NOISE_RE` — Task 2 (após `_ANSI_RE`)
- ✅ Botão "Fechar" (HTML + CSS) — Task 3 Step 1-2
- ✅ Timer mm:ss no `treinoModalStatus` — Task 3 Step 3
- ✅ Parser `EPOCH_PROGRESS:` com val_loss + ETA — Task 3 Step 4
- ✅ Sem auto-close no sucesso — Task 3 Step 5
- ✅ `closeTreinoModal` navega para Lista após sucesso — Task 3 Step 6

**Placeholder scan:** nenhum TBD/TODO/vague. Todos os steps têm código completo.

**Type consistency:**
- `window._treinoElapsedTimer` usado em `openTreinoModal`, `_finishTreinoModal` e `closeTreinoModal` — consistente
- `document.getElementById('treinoCloseBtn')` referenciado nos Steps 3, 5 e 6 — ID coincide com o HTML do Step 1
- `_TF_NOISE_RE` definido como constante de módulo, usada no loop de `_run_command` — sem conflito com `_ANSI_RE` existente
- Task 1 (callback): `self._hp_val("LSTM_EPOCHS")` — valor já usado no `EarlyStopping`, correto para `total_epochs`
