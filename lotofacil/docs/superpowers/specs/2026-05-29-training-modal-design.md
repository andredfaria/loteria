# Training Modal Improvements — Design Spec

**Data:** 2026-05-29  
**Status:** Aprovado  
**Problemas resolvidos:** 5 bugs no fluxo de treinamento do dashboard

---

## Diagnóstico

O output real do comando `lotofacil lab train` é:

```
WARNING: All log messages...    ← TF noise (stderr capturado)
I0000 00:00:...                 ← TF noise
Config: base
Draws: 3688 (1–3690)
Training... (this may take a while)
[5 minutos de silêncio — verbose=0]
09:55:41 [INFO] best_epoch=21 val_loss=0.0679
Saved: neural_test_diag.keras
TREINO_MODELO_PATH:             ← BUG: path na PRÓXIMA linha
/home/.../neural_test_diag.keras
```

**5 problemas:**

| # | Problema | Causa |
|---|---------|-------|
| 1 | Barra de progresso trava em 0% | `verbose=0` — sem output de epoch |
| 2 | Log vazio / só ruído TF | TF warnings poluem, nenhuma info útil durante treino |
| 3 | `TREINO_MODELO_PATH:` não capturado | Line wrapping: path na linha seguinte |
| 4 | Sem botão "Fechar" persistente | Modal auto-fecha em 1.8s, sem chance de ver resultado |
| 5 | Sem indicador de tempo decorrido | 5min sem feedback parece que travou |

---

## Solução: Abordagem A — Callback personalizado

### Arquivo 1: `src/lotofacil/experimentos/models/neural_modular.py`

Adicionar inner class `_EpochProgressCallback` antes da classe `NeuralModular`:

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

Adicionar ao `model.fit()` call em `NeuralModular.fit()`:

```python
callbacks = [
    tf.keras.callbacks.EarlyStopping(...),
    tf.keras.callbacks.ReduceLROnPlateau(...),
    _EpochProgressCallback(self._hp_val("LSTM_EPOCHS")),  # ← ADICIONAR
]
```

**Invariante:** o total de epochs passado ao callback é `self._hp_val("LSTM_EPOCHS")` — o mesmo valor configurado no `EarlyStopping`. O early stopping pode parar antes, o que é correto (barra vai até onde chegar).

---

### Arquivo 2: `src/lotofacil/interface/painel/server.py`

**Fix A — `_extract_model_path_from_output`** (linha ~1115):

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

**Fix B — Filtro de ruído TF** — adicionar regex de filtro e aplicar em `_run_command` antes de escrever no registro:

```python
_TF_NOISE_RE = re.compile(
    r"^(WARNING: All log messages|I\d{4} |W\d{4} |"
    r".*oneDNN|.*cuDNN|.*GPU libraries|Skipping registering|"
    r".*cpu_feature_guard|.*port\.cc)"
)
```

No loop de leitura de stdout de `_run_command`, antes de `registry.write_line(task_id, clean)`:

```python
if not _TF_NOISE_RE.match(clean):
    registry.write_line(task_id, clean)
```

---

### Arquivo 3: `src/lotofacil/interface/painel/static/dashboard.html`

**Fix A — HTML do modal:** adicionar botão "Fechar" (desabilitado inicialmente):

```html
<div class="treino-modal-footer">
  <button class="treino-cancel-btn" id="treinoCancelBtn" onclick="cancelTreino()">
    ✕ Cancelar
  </button>
  <button class="treino-close-btn" id="treinoCloseBtn"
          onclick="closeTreinoModal()" disabled>
    ✓ Fechar
  </button>
</div>
```

**Fix B — CSS para botão Fechar:**

```css
.treino-close-btn {
  background: var(--green);
  color: #fff;
  border: none;
  border-radius: 5px;
  padding: 0.4rem 1rem;
  font-family: monospace;
  cursor: pointer;
  opacity: 0.4;
}
.treino-close-btn:not(:disabled) { opacity: 1; cursor: pointer; }
.treino-close-btn:disabled { cursor: not-allowed; }
```

**Fix C — `openTreinoModal`:** adicionar timer de tempo decorrido:

```javascript
function openTreinoModal(taskId, configLabel, epochsHint) {
  // ... código existente ...
  document.getElementById('treinoCloseBtn').disabled = true;
  document.getElementById('treinoCancelBtn').disabled = false;

  // Timer de tempo decorrido
  const _modalStart = Date.now();
  window._treinoElapsedTimer = setInterval(() => {
    if (!_treinoPoller) { clearInterval(window._treinoElapsedTimer); return; }
    const sec = Math.floor((Date.now() - _modalStart) / 1000);
    const mm = String(Math.floor(sec / 60)).padStart(2, '0');
    const ss = String(sec % 60).padStart(2, '0');
    document.getElementById('treinoModalStatus').textContent = `Em andamento · ${mm}:${ss}`;
  }, 1000);
}
```

**Fix D — `_updateEpochFromLog`:** parser do novo formato `EPOCH_PROGRESS:`:

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

**Fix E — `_finishTreinoModal`:** não fechar sozinho, habilitar "Fechar":

```javascript
function _finishTreinoModal(success) {
  clearInterval(window._treinoElapsedTimer);
  document.getElementById('treinoCancelBtn').disabled = true;
  document.getElementById('treinoCloseBtn').disabled = false;

  const fill = document.getElementById('treinoProgressFill');
  if (success) {
    document.getElementById('treinoModalTitle').textContent = '✅ Treino concluído';
    fill.style.width = '100%';
    fill.style.background = 'var(--green)';
    document.getElementById('treinoModalStatus').textContent =
      'Modelo salvo. Clique Fechar para continuar.';
    showToast('✅ Treino concluído! Veja o resultado no modal.', 'success');
  } else {
    document.getElementById('treinoModalTitle').textContent = '❌ Treino falhou';
    document.getElementById('treinoModalStatus').textContent =
      'Veja o log para detalhes.';
  }
  // Não auto-fecha — usuário decide quando fechar
}
```

**Fix F — `closeTreinoModal`:** ao fechar com sucesso, navegar para aba Lista:

```javascript
function closeTreinoModal() {
  clearInterval(window._treinoElapsedTimer);
  clearInterval(_treinoPoller);
  _treinoPoller = null;
  _treinoTaskId = null;
  document.getElementById('treinoModalOverlay').classList.remove('visible');
  // Se treino foi bem-sucedido, ir para lista de modelos
  const title = document.getElementById('treinoModalTitle').textContent;
  if (title.includes('✅')) {
    loadModelosAndRender();
    showModelosSubTab('lista');
  }
}
```

---

## Arquivos a modificar

| Arquivo | Mudanças |
|---------|---------|
| `src/lotofacil/experimentos/models/neural_modular.py` | Adicionar `_EpochProgressCallback`, incluir no `model.fit()` |
| `src/lotofacil/interface/painel/server.py` | Fix `_extract_model_path_from_output` + filtro `_TF_NOISE_RE` |
| `src/lotofacil/interface/painel/static/dashboard.html` | Botão Fechar + CSS + timer + parser `EPOCH_PROGRESS:` + `_finishTreinoModal` + `closeTreinoModal` |

## Sem testes automatizados

O modal é puro frontend/integração — testado manualmente iniciando um treino real. O `neural_modular.py` não tem testes de unidade para callbacks (testar o callback requereria TF carregado).
