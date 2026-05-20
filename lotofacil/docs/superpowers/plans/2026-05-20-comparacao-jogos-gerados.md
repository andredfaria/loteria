# Comparação de Jogos Gerados com Sorteio Real — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quando o concurso alvo de jogos gerados já aconteceu, mostrar automaticamente acertos, nome do prêmio e dezenas reais — no tab Gerar (inline após gerar) e no tab Histórico (badge enriquecido + stat de premiados + filtro).

**Architecture:** Backend enriquece a resposta de `/api/treinos/{id}/gerar` com `dezenas_reais` e `acertos_por_jogo` usando a função `_get_draw_dezenas` já existente. Frontend usa esses campos em `renderJogos()` para exibir o sorteio real e hits; tab Histórico ganha nome de prêmio no badge e filtro "Só premiados".

**Tech Stack:** Python/Flask (server.py), Vanilla JS (dashboard.html), SQLite (já existente).

---

## Files Modified

| File | Changes |
|------|---------|
| `src/lotofacil/interface/painel/server.py` | Add `_compute_acertos()` helper (~6 lines); enrich `api_treino_gerar` return (+3 lines) |
| `src/lotofacil/interface/painel/static/dashboard.html` | Add `_premioCat()` helper; rewrite `renderJogos()`; enrich `_historicoStats()`, `_renderHistoricoPanel()`, `_onHistoricoFiltro()` |
| `src/lotofacil/interface/painel/tests/test_server.py` | Add 3 tests para `_compute_acertos` e `_get_draw_dezenas` |

---

## Task 1: Backend — helper `_compute_acertos` + testes

**Files:**
- Modify: `src/lotofacil/interface/painel/server.py:1159` (após `_get_draw_dezenas`)
- Test: `src/lotofacil/interface/painel/tests/test_server.py`

### Context

`_get_draw_dezenas(concurso)` está em `server.py:1159`. Ela consulta o SQLite `DB_PATH` e retorna `list[int]` ou `None`. Precisamos de um helper puro `_compute_acertos` e precisamos testar ambos.

- [ ] **Step 1: Escrever os testes que vão falhar**

Adicione ao final de `src/lotofacil/interface/painel/tests/test_server.py`:

```python
import sqlite3 as _sqlite3


def test_compute_acertos_with_matching_numbers():
    jogos = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]]
    real = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    result = server_module._compute_acertos(jogos, real)
    assert result == [15]


def test_compute_acertos_returns_none_when_no_real():
    jogos = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]]
    result = server_module._compute_acertos(jogos, None)
    assert result is None


def test_compute_acertos_partial_hits():
    jogos = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
             [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 1, 2, 3, 4, 5]]
    real = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    result = server_module._compute_acertos(jogos, real)
    assert result == [15, 5]


def test_get_draw_dezenas_returns_list(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    with _sqlite3.connect(str(db)) as conn:
        conn.execute("CREATE TABLE concursos (concurso INTEGER, dezenas TEXT)")
        conn.execute(
            "INSERT INTO concursos VALUES (?, ?)",
            (1000, '[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]'),
        )
    monkeypatch.setattr(server_module, "DB_PATH", db)
    result = server_module._get_draw_dezenas(1000)
    assert result == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]


def test_get_draw_dezenas_returns_none_for_missing(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    with _sqlite3.connect(str(db)) as conn:
        conn.execute("CREATE TABLE concursos (concurso INTEGER, dezenas TEXT)")
    monkeypatch.setattr(server_module, "DB_PATH", db)
    result = server_module._get_draw_dezenas(9999)
    assert result is None
```

- [ ] **Step 2: Confirmar que os testes falham**

```bash
cd lotofacil && source venv/bin/activate
pytest src/lotofacil/interface/painel/tests/test_server.py::test_compute_acertos_with_matching_numbers -v
```

Esperado: `FAILED` com `AttributeError: module ... has no attribute '_compute_acertos'`

- [ ] **Step 3: Implementar `_compute_acertos` em `server.py`**

Em `server.py`, localize a função `_get_draw_dezenas` (linha ~1159) e adicione **logo abaixo** dela:

```python
def _compute_acertos(jogos: list[list[int]], dezenas_reais: list[int] | None) -> list[int] | None:
    if not dezenas_reais:
        return None
    real_set = set(dezenas_reais)
    return [len(set(j) & real_set) for j in jogos]
```

- [ ] **Step 4: Rodar todos os novos testes**

```bash
pytest src/lotofacil/interface/painel/tests/test_server.py -k "compute_acertos or get_draw_dezenas" -v
```

Esperado: 5 testes `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/interface/painel/server.py src/lotofacil/interface/painel/tests/test_server.py
git commit -m "feat: add _compute_acertos helper with tests"
```

---

## Task 2: Backend — enriquecer resposta de `api_treino_gerar`

**Files:**
- Modify: `src/lotofacil/interface/painel/server.py:1260-1269` (bloco `return jsonify(...)` em `api_treino_gerar`)

### Context

A função `api_treino_gerar` termina com `return jsonify({...})` (linha ~1262). Precisamos, antes do return, consultar `_get_draw_dezenas` e calcular `_compute_acertos`, e incluir esses campos no JSON de resposta.

- [ ] **Step 1: Modificar `api_treino_gerar` em `server.py`**

Localize o bloco (linhas ~1259–1269):

```python
        # Persist to registry for history tab
        _registry.salvar_jogo(treino_id, t.get("nome", treino_id), next_concurso, jogos)

        return jsonify({
            "treino_id": treino_id,
            "treino_nome": t.get("nome"),
            "concurso": next_concurso,
            "n_jogos": n_jogos,
            "n_numeros": n_numeros,
            "jogos": jogos,
        })
```

Substitua por:

```python
        # Persist to registry for history tab
        _registry.salvar_jogo(treino_id, t.get("nome", treino_id), next_concurso, jogos)

        dezenas_reais = _get_draw_dezenas(next_concurso)
        acertos_por_jogo = _compute_acertos(jogos, dezenas_reais)

        return jsonify({
            "treino_id": treino_id,
            "treino_nome": t.get("nome"),
            "concurso": next_concurso,
            "n_jogos": n_jogos,
            "n_numeros": n_numeros,
            "jogos": jogos,
            "dezenas_reais": dezenas_reais,
            "acertos_por_jogo": acertos_por_jogo,
        })
```

- [ ] **Step 2: Rodar suite completa para garantir nenhuma regressão**

```bash
pytest src/lotofacil/interface/painel/tests/ -v
```

Esperado: todos os testes existentes `PASSED` + os 5 novos `PASSED`.

- [ ] **Step 3: Commit**

```bash
git add src/lotofacil/interface/painel/server.py
git commit -m "feat: enrich /gerar response with dezenas_reais and acertos_por_jogo"
```

---

## Task 3: Frontend — helper `_premioCat` + `renderJogos` com comparação

**Files:**
- Modify: `src/lotofacil/interface/painel/static/dashboard.html:869` (após `_ballClass`)
- Modify: `src/lotofacil/interface/painel/static/dashboard.html:2623` (função `renderJogos`)

### Context

`_ballClass(n)` termina na linha 869. `renderJogos(data)` vai de 2623 a 2665. Vamos:
1. Inserir `_premioCat` logo após `_ballClass`
2. Substituir o corpo completo de `renderJogos`

- [ ] **Step 1: Inserir `_premioCat` após `_ballClass` em `dashboard.html`**

Localize (linha ~870):

```javascript
}
// ──────────────────────────────────────────────────────────────

const CONSOLE_MAX = 150;
```

Insira logo após o `}` (fechamento de `_ballClass`) e antes do comentário divisor:

```javascript
}

function _premioCat(hits) {
  if (hits === 15) return { label: '15 pontos 🏆', color: 'var(--accent)' };
  if (hits === 14) return { label: '14 pontos', color: 'var(--green)' };
  if (hits === 13) return { label: '13 pontos', color: 'var(--green)' };
  if (hits === 12) return { label: '12 pontos', color: 'var(--yellow)' };
  if (hits === 11) return { label: '11 pontos', color: 'var(--yellow)' };
  return { label: 'Sem prêmio', color: 'var(--red)' };
}
// ──────────────────────────────────────────────────────────────

const CONSOLE_MAX = 150;
```

- [ ] **Step 2: Substituir o corpo de `renderJogos` em `dashboard.html`**

Localize a função completa (linhas 2623–2665):

```javascript
function renderJogos(data) {
  const div = document.getElementById('gerarResultados');
  if (!data.jogos || !data.jogos.length) {
    div.innerHTML = '<div style="color:var(--muted);margin-top:0.5rem">Nenhum jogo retornado.</div>'; return;
  }
  let html = `<div style="font-size:0.72rem;color:var(--muted);margin-top:0.5rem;margin-bottom:0.5rem">
    Concurso alvo: <b style="color:var(--text)">${data.concurso}</b> ·
    Modelo: <b style="color:var(--accent)">${esc(data.treino_nome||data.treino_id)}</b>
  </div><div class="pred-jogos-grid">`;
  data.jogos.forEach((jogo, i) => {
    html += `<div class="pred-jogo-card">
      <div class="pred-jogo-title">Jogo ${i+1} — ${jogo.length} números</div>
      <div class="pred-balls">${jogo.map(n=>`<span class="ball ${_ballClass(n)}">${String(n).padStart(2,'0')}</span>`).join('')}</div>
    </div>`;
  });
  html += '</div>';

  // frequency heatmap across all generated games
  const freq = {};
  data.jogos.forEach(jogo => jogo.forEach(n => { freq[n] = (freq[n] || 0) + 1; }));
  const maxFreq = Math.max(...Object.values(freq), 1);
  let heatHtml = '<div style="margin-top:0.75rem"><div style="font-size:0.65rem;color:var(--dim);margin-bottom:0.3rem">Frequência nos jogos gerados</div><div style="display:flex;gap:3px;flex-wrap:wrap">';
  for (let n = 1; n <= 25; n++) {
    const f = freq[n] || 0;
    const alpha = f ? 0.25 + (f / maxFreq) * 0.75 : 0.08;
    heatHtml += `<div title="${n}: ${f}x" style="width:22px;height:22px;border-radius:4px;background:rgba(96,165,250,${alpha.toFixed(2)});display:flex;align-items:center;justify-content:center;font-size:0.6rem;font-weight:${f===maxFreq?700:400};color:${f===maxFreq?'#fff':'rgba(255,255,255,0.7)'}">${n}</div>`;
  }
  heatHtml += '</div></div>';
  html += heatHtml;

  // show last real draw for reference
  const ld = _predState.lastDraw;
  if (ld && Array.isArray(ld.dezenas) && ld.dezenas.length) {
    html += `<div style="margin-top:0.75rem;padding:0.5rem 0.75rem;background:rgba(255,255,255,0.04);border-radius:6px;border:1px solid var(--border)">
      <div style="font-size:0.65rem;color:var(--dim);margin-bottom:0.3rem">Último sorteio real — concurso ${ld.concurso}${ld.data ? ' · ' + ld.data : ''}</div>
      <div class="pred-balls" style="display:inline-flex;gap:2px;opacity:0.75">
        ${ld.dezenas.map(n=>`<span class="ball ${_ballClass(n)}">${String(n).padStart(2,'0')}</span>`).join('')}
      </div>
    </div>`;
  }

  div.innerHTML = html;
}
```

Substitua pela versão abaixo (o heatmap é preservado intacto; "último sorteio" só aparece quando não há resultado real):

```javascript
function renderJogos(data) {
  const div = document.getElementById('gerarResultados');
  if (!data.jogos || !data.jogos.length) {
    div.innerHTML = '<div style="color:var(--muted);margin-top:0.5rem">Nenhum jogo retornado.</div>'; return;
  }

  const dezReais = Array.isArray(data.dezenas_reais) ? data.dezenas_reais : null;
  const acertos  = Array.isArray(data.acertos_por_jogo) ? data.acertos_por_jogo : null;
  const realSet  = dezReais ? new Set(dezReais) : null;

  let html = `<div style="font-size:0.72rem;color:var(--muted);margin-top:0.5rem;margin-bottom:0.5rem">
    Concurso alvo: <b style="color:var(--text)">${data.concurso}</b> ·
    Modelo: <b style="color:var(--accent)">${esc(data.treino_nome||data.treino_id)}</b>
  </div>`;

  // Banner sorteio real — só aparece quando concurso já aconteceu
  if (dezReais) {
    html += `<div style="margin-bottom:0.75rem;padding:0.5rem 0.75rem;background:rgba(255,255,255,0.04);border-radius:6px;border:1px solid var(--green);opacity:0.9">
      <div style="font-size:0.65rem;color:var(--green);font-weight:600;margin-bottom:0.3rem">🎯 Concurso ${data.concurso} já aconteceu — sorteio real</div>
      <div class="pred-balls" style="display:inline-flex;gap:2px">
        ${dezReais.map(n=>`<span class="ball ${_ballClass(n)}">${String(n).padStart(2,'0')}</span>`).join('')}
      </div>
    </div>`;
  }

  html += `<div class="pred-jogos-grid">`;
  data.jogos.forEach((jogo, i) => {
    const hits = acertos ? (acertos[i] ?? null) : null;
    const premio = hits !== null ? _premioCat(hits) : null;
    const badgeHtml = premio && jogo.length === 15
      ? `<span style="font-size:0.62rem;font-weight:600;color:${premio.color};margin-left:0.35rem">${hits}/15 — ${premio.label}</span>`
      : hits !== null
        ? `<span style="font-size:0.62rem;color:var(--dim);margin-left:0.35rem">${hits}/${jogo.length}</span>`
        : '';

    const ballsHtml = jogo.map(n => {
      const isHit = realSet && realSet.has(n);
      const style = dezReais ? (isHit ? 'outline:2px solid var(--green);opacity:1' : 'opacity:0.35') : '';
      return `<span class="ball ${_ballClass(n)}" style="${style}">${String(n).padStart(2,'0')}</span>`;
    }).join('');

    html += `<div class="pred-jogo-card">
      <div class="pred-jogo-title" style="display:flex;align-items:center;flex-wrap:wrap;gap:0.2rem">
        <span>Jogo ${i+1} — ${jogo.length} números</span>${badgeHtml}
      </div>
      <div class="pred-balls">${ballsHtml}</div>
    </div>`;
  });
  html += '</div>';

  // Resumo de prêmios por jogo
  if (acertos) {
    const chips = acertos.map((h, i) => {
      const p = _premioCat(h);
      return `<span style="font-size:0.62rem;padding:2px 7px;border-radius:10px;background:rgba(255,255,255,0.06);color:${p.color}">J${i+1}: ${p.label}</span>`;
    }).join(' · ');
    html += `<div style="margin-top:0.6rem;font-size:0.72rem;color:var(--dim);display:flex;flex-wrap:wrap;gap:0.3rem;align-items:center">
      <span>Resultado:</span> ${chips}
    </div>`;
  }

  // Heatmap de frequência (preservado intacto)
  const freq = {};
  data.jogos.forEach(jogo => jogo.forEach(n => { freq[n] = (freq[n] || 0) + 1; }));
  const maxFreq = Math.max(...Object.values(freq), 1);
  let heatHtml = '<div style="margin-top:0.75rem"><div style="font-size:0.65rem;color:var(--dim);margin-bottom:0.3rem">Frequência nos jogos gerados</div><div style="display:flex;gap:3px;flex-wrap:wrap">';
  for (let n = 1; n <= 25; n++) {
    const f = freq[n] || 0;
    const alpha = f ? 0.25 + (f / maxFreq) * 0.75 : 0.08;
    heatHtml += `<div title="${n}: ${f}x" style="width:22px;height:22px;border-radius:4px;background:rgba(96,165,250,${alpha.toFixed(2)});display:flex;align-items:center;justify-content:center;font-size:0.6rem;font-weight:${f===maxFreq?700:400};color:${f===maxFreq?'#fff':'rgba(255,255,255,0.7)'}">${n}</div>`;
  }
  heatHtml += '</div></div>';
  html += heatHtml;

  // Último sorteio real — só quando concurso alvo ainda não aconteceu
  if (!dezReais) {
    const ld = _predState.lastDraw;
    if (ld && Array.isArray(ld.dezenas) && ld.dezenas.length) {
      html += `<div style="margin-top:0.75rem;padding:0.5rem 0.75rem;background:rgba(255,255,255,0.04);border-radius:6px;border:1px solid var(--border)">
        <div style="font-size:0.65rem;color:var(--dim);margin-bottom:0.3rem">Último sorteio real — concurso ${ld.concurso}${ld.data ? ' · ' + ld.data : ''}</div>
        <div class="pred-balls" style="display:inline-flex;gap:2px;opacity:0.75">
          ${ld.dezenas.map(n=>`<span class="ball ${_ballClass(n)}">${String(n).padStart(2,'0')}</span>`).join('')}
        </div>
      </div>`;
    }
  }

  div.innerHTML = html;
}
```

- [ ] **Step 3: Teste manual — concurso passado**

Inicie o dashboard:
```bash
cd lotofacil && source venv/bin/activate
lotofacil painel  # ou: python -m lotofacil.interface.painel.server
```

1. Abra `http://localhost:5000`
2. Vá em Modelo → Gerar
3. Selecione um modelo treinado
4. No campo "Concurso alvo", entre com um número de concurso **que já aconteceu** (qualquer número ≤ ao último concurso na base)
5. Clique "⚡ Gerar Jogos"
6. Confirme que aparece o banner verde "🎯 Concurso X já aconteceu — sorteio real" com as dezenas reais
7. Confirme que bolas acertadas têm borda verde e as erradas têm opacidade reduzida
8. Confirme o badge por jogo: `13/15 — 13 pontos`
9. Confirme o resumo "Resultado: J1: 13 pontos · J2: 11 pontos ..."

- [ ] **Step 4: Teste manual — concurso futuro**

1. Apague o número do campo "Concurso alvo" (deixe em branco) ou entre com um número maior que o último concurso
2. Clique "⚡ Gerar Jogos"
3. Confirme que **não aparece** o banner do sorteio real
4. Confirme que o "Último sorteio real" (referência) **aparece** como antes

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/interface/painel/static/dashboard.html
git commit -m "feat: show real draw comparison in Gerar tab when concurso already happened"
```

---

## Task 4: Frontend — enriquecer tab Histórico

**Files:**
- Modify: `src/lotofacil/interface/painel/static/dashboard.html:2778` (variáveis de estado do histórico)
- Modify: `src/lotofacil/interface/painel/static/dashboard.html:2794` (`_historicoStats`)
- Modify: `src/lotofacil/interface/painel/static/dashboard.html:2826` (statsHtml — adicionar premiados)
- Modify: `src/lotofacil/interface/painel/static/dashboard.html:2835` (barra de filtros — adicionar checkbox)
- Modify: `src/lotofacil/interface/painel/static/dashboard.html:2821` (lógica de filtro — `filtered`)
- Modify: `src/lotofacil/interface/painel/static/dashboard.html:2865` (badge por jogo)
- Modify: `src/lotofacil/interface/painel/static/dashboard.html:2897` (`_onHistoricoFiltro`)

### Context

Todas as mudanças são no mesmo arquivo `dashboard.html`. Execute-as em ordem para evitar conflito de linha.

- [ ] **Step 1: Adicionar variável de estado `_historicoSoPremiados`**

Localize (linha ~2779):

```javascript
let _historicoData = [];
let _historicoFiltroModelo = '';
```

Substitua por:

```javascript
let _historicoData = [];
let _historicoFiltroModelo = '';
let _historicoSoPremiados = false;
```

- [ ] **Step 2: Enriquecer `_historicoStats` com contador `premiados`**

Localize a função completa (linhas 2794–2809):

```javascript
function _historicoStats(items) {
  let totalJogos = 0, acertosAll = [], melhor = null;
  for (const item of items) {
    const arr = Array.isArray(item.jogos) ? item.jogos : [];
    totalJogos += arr.length;
    const ac = item.acertos_por_jogo || [];
    for (const h of ac) {
      acertosAll.push(h);
      if (melhor === null || h > melhor) melhor = h;
    }
  }
  const media = acertosAll.length
    ? (acertosAll.reduce((s, v) => s + v, 0) / acertosAll.length).toFixed(2)
    : null;
  return { totalGeracoes: items.length, totalJogos, media, melhor, comResultado: acertosAll.length };
}
```

Substitua por:

```javascript
function _historicoStats(items) {
  let totalJogos = 0, acertosAll = [], melhor = null, premiados = 0;
  for (const item of items) {
    const arr = Array.isArray(item.jogos) ? item.jogos : [];
    totalJogos += arr.length;
    const ac = item.acertos_por_jogo || [];
    for (const h of ac) {
      acertosAll.push(h);
      if (melhor === null || h > melhor) melhor = h;
      if (h >= 11) premiados++;
    }
  }
  const media = acertosAll.length
    ? (acertosAll.reduce((s, v) => s + v, 0) / acertosAll.length).toFixed(2)
    : null;
  return { totalGeracoes: items.length, totalJogos, media, melhor, comResultado: acertosAll.length, premiados };
}
```

- [ ] **Step 3: Adicionar campo "Premiados (11+)" no statsHtml**

Localize (linhas 2826–2833):

```javascript
  const statsHtml = `
    <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:0.75rem">
      <div style="font-size:0.72rem;color:var(--muted)">Gerações: <b style="color:var(--text)">${stats.totalGeracoes}</b></div>
      <div style="font-size:0.72rem;color:var(--muted)">Jogos: <b style="color:var(--text)">${stats.totalJogos}</b></div>
      ${stats.media != null ? `<div style="font-size:0.72rem;color:var(--muted)">Média acertos: <b style="color:var(--accent)">${stats.media}</b></div>` : ''}
      ${stats.melhor != null ? `<div style="font-size:0.72rem;color:var(--muted)">Melhor: <b style="color:var(--green)">${stats.melhor}/15</b></div>` : ''}
      ${stats.comResultado > 0 ? `<div style="font-size:0.72rem;color:var(--dim)">${stats.comResultado} jogo${stats.comResultado>1?'s':''} com resultado</div>` : ''}
    </div>`;
```

Substitua por:

```javascript
  const statsHtml = `
    <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:0.75rem">
      <div style="font-size:0.72rem;color:var(--muted)">Gerações: <b style="color:var(--text)">${stats.totalGeracoes}</b></div>
      <div style="font-size:0.72rem;color:var(--muted)">Jogos: <b style="color:var(--text)">${stats.totalJogos}</b></div>
      ${stats.media != null ? `<div style="font-size:0.72rem;color:var(--muted)">Média acertos: <b style="color:var(--accent)">${stats.media}</b></div>` : ''}
      ${stats.melhor != null ? `<div style="font-size:0.72rem;color:var(--muted)">Melhor: <b style="color:var(--green)">${stats.melhor}/15</b></div>` : ''}
      ${stats.premiados > 0 ? `<div style="font-size:0.72rem;color:var(--muted)">Premiados (11+): <b style="color:var(--green)">${stats.premiados}</b></div>` : ''}
      ${stats.comResultado > 0 ? `<div style="font-size:0.72rem;color:var(--dim)">${stats.comResultado} jogo${stats.comResultado>1?'s':''} com resultado</div>` : ''}
    </div>`;
```

- [ ] **Step 4: Adicionar filtro de premiados na barra de controles**

Localize (linhas 2835–2845):

```javascript
  let html = `
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;flex-wrap:wrap">
      <div class="modelos-section-title" style="margin:0">🗂 Histórico de Jogos Gerados</div>
      <select id="historicoFiltroModelo" onchange="_onHistoricoFiltro()"
        style="font-size:0.72rem;padding:0.2rem 0.4rem;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:4px">
        <option value="">Todos os modelos</option>
        ${modelos.map(m => `<option value="${esc(m)}"${_historicoFiltroModelo===m?' selected':''}>${esc(m)}</option>`).join('')}
      </select>
      <button class="action-btn" onclick="_exportHistoricoCSV()"
        style="font-size:0.72rem;padding:0.2rem 0.5rem;margin-left:auto">⬇ CSV</button>
    </div>
    ${statsHtml}`;
```

Substitua por:

```javascript
  let html = `
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;flex-wrap:wrap">
      <div class="modelos-section-title" style="margin:0">🗂 Histórico de Jogos Gerados</div>
      <select id="historicoFiltroModelo" onchange="_onHistoricoFiltro()"
        style="font-size:0.72rem;padding:0.2rem 0.4rem;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:4px">
        <option value="">Todos os modelos</option>
        ${modelos.map(m => `<option value="${esc(m)}"${_historicoFiltroModelo===m?' selected':''}>${esc(m)}</option>`).join('')}
      </select>
      <label style="display:flex;align-items:center;gap:0.3rem;font-size:0.72rem;cursor:pointer;color:var(--muted)">
        <input type="checkbox" id="historicoSoPremiados" onchange="_onHistoricoFiltro()"${_historicoSoPremiados?' checked':''}>
        Só premiados
      </label>
      <button class="action-btn" onclick="_exportHistoricoCSV()"
        style="font-size:0.72rem;padding:0.2rem 0.5rem;margin-left:auto">⬇ CSV</button>
    </div>
    ${statsHtml}`;
```

- [ ] **Step 5: Atualizar lógica de filtro para incluir `_historicoSoPremiados`**

Localize (linhas 2821–2823):

```javascript
  const filtered = _historicoFiltroModelo
    ? jogos.filter(j => (j.treino_nome || j.treino_id) === _historicoFiltroModelo)
    : jogos;
```

Substitua por:

```javascript
  const byModel = _historicoFiltroModelo
    ? jogos.filter(j => (j.treino_nome || j.treino_id) === _historicoFiltroModelo)
    : jogos;
  const filtered = _historicoSoPremiados
    ? byModel.filter(j => (j.acertos_por_jogo || []).some(h => h >= 11))
    : byModel;
```

- [ ] **Step 6: Enriquecer badge por jogo com nome do prêmio**

Localize (linhas 2865–2870):

```javascript
      const hits = acertos[i];
      const hasReal = hits != null;
      const hitColor = hasReal ? (hits >= 13 ? 'var(--green)' : hits >= 11 ? 'var(--yellow)' : 'var(--red)') : '';
      const badge = hasReal
        ? `<span style="font-size:0.6rem;font-weight:700;padding:1px 4px;border-radius:3px;background:rgba(255,255,255,0.07);color:${hitColor};margin-left:4px">${hits}/15 ✓</span>`
        : '';
```

Substitua por:

```javascript
      const hits = acertos[i];
      const hasReal = hits != null;
      const hitColor = hasReal ? (hits >= 13 ? 'var(--green)' : hits >= 11 ? 'var(--yellow)' : 'var(--red)') : '';
      const premioNome = hasReal && Array.isArray(jogo) && jogo.length === 15 ? ` — ${_premioCat(hits).label}` : '';
      const badge = hasReal
        ? `<span style="font-size:0.6rem;font-weight:700;padding:1px 4px;border-radius:3px;background:rgba(255,255,255,0.07);color:${hitColor};margin-left:4px">${hits}/15${premioNome} ✓</span>`
        : '';
```

- [ ] **Step 7: Atualizar `_onHistoricoFiltro` para ler o checkbox**

Localize a função completa (linhas 2897–2901):

```javascript
function _onHistoricoFiltro() {
  const sel = document.getElementById('historicoFiltroModelo');
  _historicoFiltroModelo = sel ? sel.value : '';
  const panel = document.getElementById('mod-historico');
  if (panel) _renderHistoricoPanel(panel);
}
```

Substitua por:

```javascript
function _onHistoricoFiltro() {
  const sel = document.getElementById('historicoFiltroModelo');
  _historicoFiltroModelo = sel ? sel.value : '';
  const chk = document.getElementById('historicoSoPremiados');
  _historicoSoPremiados = chk ? chk.checked : false;
  const panel = document.getElementById('mod-historico');
  if (panel) _renderHistoricoPanel(panel);
}
```

- [ ] **Step 8: Teste manual — tab Histórico**

1. Vá em Modelo → Histórico
2. Confirme que jogos com resultado mostram badge `13/15 — 13 pontos ✓`
3. Confirme que o stats header mostra `Premiados (11+): X` quando há jogos com ≥11 acertos
4. Marque o checkbox "Só premiados" e confirme que apenas linhas com pelo menos um jogo ≥11 acertos aparecem
5. Desmarque o checkbox e confirme que todos voltam a aparecer
6. Combine checkbox + filtro de modelo e confirme que ambos os filtros se aplicam juntos

- [ ] **Step 9: Commit**

```bash
git add src/lotofacil/interface/painel/static/dashboard.html
git commit -m "feat: enrich Histórico tab with prize names, premiados stat and filter"
```

---

## Self-Review

### Cobertura do spec

| Requisito | Task que implementa |
|-----------|-------------------|
| Backend retorna `dezenas_reais` + `acertos_por_jogo` | Task 1 + 2 |
| Tab Gerar: banner sorteio real com bolas | Task 3 |
| Tab Gerar: bolas acertadas em verde, erradas opacas | Task 3 |
| Tab Gerar: badge por jogo com nome do prêmio | Task 3 |
| Tab Gerar: resumo geral de prêmios | Task 3 |
| Tab Gerar: sorteio real suprime "último sorteio" | Task 3 |
| Tab Histórico: badge com nome do prêmio | Task 4 |
| Tab Histórico: stat "Premiados (11+)" | Task 4 |
| Tab Histórico: filtro "Só premiados" | Task 4 |
| Concurso futuro → nenhuma comparação exibida | Task 2 (backend retorna null) + Task 3 (frontend checa `dezenas_reais`) |
| Testes unitários `_compute_acertos` | Task 1 |
| Testes `_get_draw_dezenas` com SQLite temp | Task 1 |
