# ROI Walk-Forward Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar parâmetro `holdout_pct` ao backtest do ROI Lab para separar um período de teste (últimos N%) dos dados usados para escolher filtros, tornando os resultados mais honestos.

**Architecture:** `rodar_backtest_roi` recebe `holdout_pct: float = 0.0` — quando >0, o backtest roda **somente nos últimos `holdout_pct * 100%`** dos sorteios históricos. O endpoint Flask lê o parâmetro do body. O dashboard exibe um select de holdout e um badge informativo no resultado.

**Tech Stack:** Python 3.12, Flask, JS vanilla.

---

## File Map

| Arquivo | Ação |
|---------|------|
| `src/lotofacil/servicos/roi_lab.py` | Adicionar `holdout_pct` a `rodar_backtest_roi`, retornar `meta` |
| `src/lotofacil/interface/painel/server.py` | Ler `holdout_pct` do body do POST `/api/roi/backtest` |
| `src/lotofacil/interface/painel/static/dashboard.html` | Select de holdout + badge condicional nos resultados |
| `testes/unidade/servicos/test_roi_lab.py` | Acrescentar 3 testes |

---

## Task 1: Serviço `roi_lab.py` — holdout_pct (TDD)

**Files:**
- Modify: `testes/unidade/servicos/test_roi_lab.py` (append)
- Modify: `src/lotofacil/servicos/roi_lab.py`

- [ ] **Step 1: Acrescentar 3 testes ao final de `testes/unidade/servicos/test_roi_lab.py`**

```python
def test_holdout_pct_zero_usa_todos_sorteios():
    from unittest.mock import patch
    from lotofacil.servicos.roi_lab import rodar_backtest_roi

    fake_draws = [
        {"concurso": i, "data": "01/01/2020", "dezenas": list(range(i, i + 15))}
        for i in range(1, 11)
    ]
    with patch("lotofacil.servicos.roi_lab.DatabaseManager") as MockDB:
        MockDB.return_value.get_all_concursos.return_value = fake_draws
        result = rodar_backtest_roi({}, n_jogos_por_sorteio=1, holdout_pct=0.0)
    assert result["estrategia"]["n_games"] == 10
    assert result["meta"]["holdout_pct"] == 0.0
    assert result["meta"]["sorteios_teste"] == 10


def test_holdout_pct_02_usa_ultimos_20_pct():
    from unittest.mock import patch
    from lotofacil.servicos.roi_lab import rodar_backtest_roi

    fake_draws = [
        {"concurso": i, "data": "01/01/2020", "dezenas": list(range(i, i + 15))}
        for i in range(1, 11)
    ]
    with patch("lotofacil.servicos.roi_lab.DatabaseManager") as MockDB:
        MockDB.return_value.get_all_concursos.return_value = fake_draws
        result = rodar_backtest_roi({}, n_jogos_por_sorteio=1, holdout_pct=0.2)
    # 20% de 10 = 2 sorteios de teste
    assert result["estrategia"]["n_games"] == 2
    assert result["meta"]["sorteios_teste"] == 2
    assert result["meta"]["sorteios_treino"] == 8


def test_meta_retorna_concurso_corte():
    from unittest.mock import patch
    from lotofacil.servicos.roi_lab import rodar_backtest_roi

    fake_draws = [
        {"concurso": i, "data": "01/01/2020", "dezenas": list(range(i, i + 15))}
        for i in range(1, 11)
    ]
    with patch("lotofacil.servicos.roi_lab.DatabaseManager") as MockDB:
        MockDB.return_value.get_all_concursos.return_value = fake_draws
        result = rodar_backtest_roi({}, n_jogos_por_sorteio=1, holdout_pct=0.2)
    # 10 draws, 20% = 2 últimos: draws 9 e 10 → corte no concurso 9
    assert result["meta"]["concurso_corte"] == 9
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd /home/andre/Documentos/projetos/loteria/lotofacil && source venv/bin/activate
pytest testes/unidade/servicos/test_roi_lab.py::test_holdout_pct_zero_usa_todos_sorteios -v 2>&1 | tail -8
```

Expected: `TypeError` — `rodar_backtest_roi()` não aceita `holdout_pct`.

- [ ] **Step 3: Atualizar `rodar_backtest_roi` em `roi_lab.py`**

Substituir a assinatura e o corpo da função:

```python
def rodar_backtest_roi(
    filtros: dict[str, Any],
    n_jogos_por_sorteio: int = 5,
    janela: int | None = None,
    holdout_pct: float = 0.0,
) -> dict[str, Any]:
    """Simula ROI histórico para os filtros dados vs. baseline aleatório.

    Returns:
        {
          "estrategia": FinancialResult dict,
          "baseline": FinancialResult dict,
          "meta": {total_sorteios, sorteios_treino, sorteios_teste, holdout_pct, concurso_corte}
        }
    """
    db = DatabaseManager()
    sorteios = db.get_all_concursos()
    if janela is not None:
        sorteios = sorteios[-janela:]

    total = len(sorteios)
    holdout_pct = max(0.0, min(holdout_pct, 0.9))
    n_teste = max(1, round(total * holdout_pct)) if holdout_pct > 0.0 else total
    sorteios_teste = sorteios[-n_teste:] if holdout_pct > 0.0 else sorteios
    concurso_corte = sorteios_teste[0]["concurso"] if sorteios_teste else None

    def _simular(filtros_ativos: dict[str, Any]) -> dict[str, Any]:
        rng = random.Random(42)
        resultados: list[dict] = []
        anterior: list[int] | None = None
        for sorteio in sorteios_teste:
            dezenas_reais = sorteio["dezenas"]
            for _ in range(n_jogos_por_sorteio):
                jogo = _gerar_jogo_filtrado(filtros_ativos, anterior, rng)
                if jogo is None:
                    resultados.append({"hits": 0})
                else:
                    hits = len(set(jogo) & set(dezenas_reais))
                    resultados.append({"hits": hits})
            anterior = dezenas_reais
        sim = FinancialSimulator()
        return dataclasses.asdict(sim.simulate(resultados))

    return {
        "estrategia": _simular(filtros),
        "baseline": _simular({}),
        "meta": {
            "total_sorteios": total,
            "sorteios_treino": total - n_teste,
            "sorteios_teste": n_teste,
            "holdout_pct": holdout_pct,
            "concurso_corte": concurso_corte,
        },
    }
```

- [ ] **Step 4: Rodar todos os testes do serviço**

```bash
pytest testes/unidade/servicos/test_roi_lab.py -v
```

Expected: todos `PASSED` (os 16 existentes + 3 novos = 19).

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/servicos/roi_lab.py testes/unidade/servicos/test_roi_lab.py
git commit -m "feat: add holdout_pct to rodar_backtest_roi for walk-forward evaluation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: API — ler `holdout_pct` em `server.py`

**Files:**
- Modify: `src/lotofacil/interface/painel/server.py`

- [ ] **Step 1: Atualizar `api_roi_backtest` para ler `holdout_pct`**

Localizar a função `api_roi_backtest`. O corpo atual:

```python
@app.route("/api/roi/backtest", methods=["POST"])
def api_roi_backtest():
    body = request.get_json(force=True) or {}
    filtros: dict = {k: v for k, v in (body.get("filtros") or {}).items() if v is not None}
    n_jogos = max(1, min(int(body.get("n_jogos", 5)), 20))
    janela = body.get("janela")
    if janela is not None:
        janela = max(10, min(int(janela), 5000))
    try:
        result = _rodar_backtest_roi(filtros, n_jogos_por_sorteio=n_jogos, janela=janela)
        return jsonify(result)
    except Exception as exc:
        LOGGER.exception("roi backtest error")
        return jsonify({"error": str(exc)}), 500
```

Substituir por:

```python
@app.route("/api/roi/backtest", methods=["POST"])
def api_roi_backtest():
    body = request.get_json(force=True) or {}
    filtros: dict = {k: v for k, v in (body.get("filtros") or {}).items() if v is not None}
    n_jogos = max(1, min(int(body.get("n_jogos", 5)), 20))
    janela = body.get("janela")
    if janela is not None:
        janela = max(10, min(int(janela), 5000))
    try:
        holdout_pct = float(body.get("holdout_pct", 0.0))
        holdout_pct = max(0.0, min(holdout_pct, 0.9))
    except (TypeError, ValueError):
        holdout_pct = 0.0
    try:
        result = _rodar_backtest_roi(
            filtros,
            n_jogos_por_sorteio=n_jogos,
            janela=janela,
            holdout_pct=holdout_pct,
        )
        return jsonify(result)
    except Exception as exc:
        LOGGER.exception("roi backtest error")
        return jsonify({"error": str(exc)}), 500
```

- [ ] **Step 2: Rodar testes do server**

```bash
pytest src/lotofacil/interface/painel/tests/test_server.py -v -k "roi" 2>&1 | tail -10
```

Expected: todos os 6 testes ROI passam.

- [ ] **Step 3: Commit**

```bash
git add src/lotofacil/interface/painel/server.py
git commit -m "feat: pass holdout_pct from API to roi backtest service

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Dashboard — select de holdout e badge

**Files:**
- Modify: `src/lotofacil/interface/painel/static/dashboard.html`

- [ ] **Step 1: Adicionar select de holdout na zona de configuração**

Localizar dentro de `renderRoiLab()` o bloco de "Jogos/sorteio" e "Janela":

```html
        <div style="margin-top:0.8rem;display:flex;gap:0.4rem;align-items:center;flex-wrap:wrap">
          <span style="font-size:0.7rem;color:var(--muted)">Jogos/sorteio</span>
          <input type="number" id="roiNJogos" class="roi-num-input" value="5" min="1" max="20" style="width:38px">
          <span style="font-size:0.7rem;color:var(--muted)">Janela</span>
          <select id="roiJanela" style="font-size:0.72rem;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:3px;padding:2px 4px">
            <option value="">Todos</option>
            <option value="500">Últ. 500</option>
            <option value="1000">Últ. 1000</option>
            <option value="2000">Últ. 2000</option>
          </select>
        </div>
```

Substituir por (adiciona o select de holdout):

```html
        <div style="margin-top:0.8rem;display:flex;gap:0.4rem;align-items:center;flex-wrap:wrap">
          <span style="font-size:0.7rem;color:var(--muted)">Jogos/sorteio</span>
          <input type="number" id="roiNJogos" class="roi-num-input" value="5" min="1" max="20" style="width:38px">
          <span style="font-size:0.7rem;color:var(--muted)">Janela</span>
          <select id="roiJanela" style="font-size:0.72rem;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:3px;padding:2px 4px">
            <option value="">Todos</option>
            <option value="500">Últ. 500</option>
            <option value="1000">Últ. 1000</option>
            <option value="2000">Últ. 2000</option>
          </select>
          <span style="font-size:0.7rem;color:var(--muted)">Holdout</span>
          <select id="roiHoldout" style="font-size:0.72rem;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:3px;padding:2px 4px">
            <option value="0">Nenhum</option>
            <option value="0.1">10%</option>
            <option value="0.2">20%</option>
            <option value="0.3">30%</option>
          </select>
        </div>
```

- [ ] **Step 2: Atualizar `runRoiBacktest()` para ler o holdout e enviá-lo**

Localizar em `runRoiBacktest()` a linha:
```javascript
  const janela = janelaVal ? parseInt(janelaVal) : null;
```

Substituir por:
```javascript
  const janela = janelaVal ? parseInt(janelaVal) : null;
  const holdout_pct = parseFloat(document.getElementById('roiHoldout').value) || 0;
```

Localizar a linha:
```javascript
      body: JSON.stringify({ filtros, n_jogos: nJogos, janela }),
```

Substituir por:
```javascript
      body: JSON.stringify({ filtros, n_jogos: nJogos, janela, holdout_pct }),
```

- [ ] **Step 3: Adicionar badge na função `_renderRoiResults(data)`**

Localizar em `_renderRoiResults` o início do `innerHTML` do `roiResults`:
```javascript
  document.getElementById('roiResults').innerHTML = `
    <div style="display:flex;gap:0.6rem;flex-wrap:wrap;margin-bottom:0.8rem">
```

Adicionar badge ANTES desse div (inserir a linha abaixo logo após o backtick de abertura):
```javascript
  const meta = data.meta || {};
  const badgeHtml = (meta.holdout_pct > 0)
    ? `<div style="font-size:0.72rem;color:var(--yellow,#f59e0b);background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:4px;padding:4px 8px;margin-bottom:0.6rem">
        ⚠️ Métricas calculadas sobre os últimos ${meta.sorteios_teste} sorteios
        (corte no concurso #${meta.concurso_corte}).
        Os filtros devem ter sido escolhidos usando os ${meta.sorteios_treino} sorteios anteriores.
       </div>`
    : '';
  document.getElementById('roiResults').innerHTML = badgeHtml + `
    <div style="display:flex;gap:0.6rem;flex-wrap:wrap;margin-bottom:0.8rem">
```

- [ ] **Step 4: Verificar que o servidor importa OK**

```bash
cd /home/andre/Documentos/projetos/loteria/lotofacil && source venv/bin/activate
python -c "from lotofacil.interface.painel import server; print('OK')"
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add src/lotofacil/interface/painel/static/dashboard.html
git commit -m "feat: add holdout select and walk-forward badge to ROI Lab dashboard

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Self-Review

- ✅ `holdout_pct=0.0` mantém comportamento atual (backward compat)
- ✅ `n_teste = max(1, round(...))` evita divisão por zero ou 0 sorteios de teste
- ✅ `holdout_pct = max(0.0, min(..., 0.9))` — clamp no backend
- ✅ `meta` presente mesmo quando `holdout_pct=0.0` (badge não aparece)
- ✅ Badge usa `var(--yellow)` com fallback — consistente com design do dashboard
