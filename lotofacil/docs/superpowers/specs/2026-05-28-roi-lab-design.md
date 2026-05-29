# ROI Lab — Design Spec

**Data:** 2026-05-28  
**Status:** Aprovado  
**Meta:** nova aba "ROI Lab" no dashboard para comparar estratégias de filtros estatísticos por ROI histórico vs. baseline aleatório.

---

## 1. Contexto e Objetivo

A Lotofácil tem edge da casa de ~35% — ROI positivo puro no longo prazo é matematicamente impossível. O objetivo não é ganhar, mas **perder menos que o aleatório**: encontrar combinações de filtros estatísticos que, historicamente, produzem distribuições de acertos melhores que jogos completamente aleatórios.

O sistema já possui:
- `FinancialSimulator` (`infra/avaliacao/financeiro.py`) — calcula roi_pct, equity_curve, Sharpe, drawdown
- `_compute_acertos` — conta hits de um jogo vs. sorteio real
- Banco histórico de ~3500 sorteios em SQLite
- Filtros estatísticos documentados em CLAUDE.md com cobertura histórica conhecida

O que falta: um serviço de simulação por filtros e a aba de visualização.

---

## 2. Arquitetura

```
Frontend (aba ROI Lab)
  │
  ├── POST /api/roi/backtest   {filtros, n_jogos, janela}
  ├── GET  /api/roi/strategies
  └── POST /api/roi/strategies  {nome, filtros, resultado}

server.py
  └── chama roi_lab_service.rodar_backtest_roi()

src/lotofacil/servicos/roi_lab.py   ← NOVO
  ├── rodar_backtest_roi(filtros, n_jogos_por_sorteio, janela) → FinancialResult
  └── _gerar_jogo_filtrado(filtros, sorteio_anterior) → list[int] | None

FinancialSimulator.simulate(results)  ← já existe, sem modificações
```

**Persistência de estratégias salvas:** `saida/roi_strategies.json` (lista de dicts com nome + filtros + resultado resumido). Sem banco extra.

---

## 3. Serviço `roi_lab.py`

### Assinatura

```python
def rodar_backtest_roi(
    filtros: dict,
    n_jogos_por_sorteio: int = 5,
    janela: int | None = None,   # None = histórico completo
) -> dict:   # {estrategia: FinancialResult, baseline: FinancialResult}
```

### Lógica

1. Carrega sorteios históricos do DB, ordenados por concurso.
2. Se `janela` não for None, usa apenas os últimos `janela` sorteios.
3. Para cada sorteio:
   a. Gera `n_jogos_por_sorteio` jogos que satisfaçam **todos** os filtros ativos usando sorteio aleatório com rejeição (max 200 tentativas por jogo).
   b. Se não gerar o número pedido (filtros muito restritivos), preenche slots faltantes com `hits=0`.
   c. Computa hits de cada jogo vs. `sorteio.dezenas` com `_compute_acertos`.
   d. Acumula lista `[{"hits": int}, ...]`.
4. Roda `FinancialSimulator.simulate(results)` → `FinancialResult` da estratégia.
5. Roda o mesmo processo com filtros vazios → `FinancialResult` do baseline aleatório.
6. Retorna `{"estrategia": result_dict, "baseline": result_dict}`.

### Filtros suportados

| Chave | Tipo | Padrão (off) | Cobertura histórica |
|-------|------|--------------|---------------------|
| `soma` | `[min, max]` | `null` | 84% em [171, 220] |
| `pares` | `[min, max]` | `null` | ~90% em [6, 9] |
| `primos` | `[min, max]` | `null` | ~70% em [4, 7] |
| `fibonacci` | `[min, max]` | `null` | ~65% em [3, 5] |
| `moldura` | `[min, max]` | `null` | ~55% em [8, 11] |
| `repeticoes` | `[min, max]` | `null` | ~70% em [8, 10] |
| `consecutivos` | `int` (mín.) | `null` | ~80% com ≥2 |

Filtro `null` = desativado (não restringe a geração).

### Números da moldura e primos/fibonacci

```python
MOLDURA = {1,2,3,4,5,6,10,11,15,16,20,21,22,23,24,25}
PRIMOS   = {2,3,5,7,11,13,17,19,23}
FIBONACCI = {1,2,3,5,8,13,21}
```

### Contagem de repetições

Para o filtro `repeticoes`, compara o jogo gerado com `sorteio_anterior.dezenas` — onde "anterior" é o sorteio imediatamente precedente na lista histórica ordenada por concurso, não o concurso mais recente da base. Para o primeiro sorteio da janela (sem predecessor), esse filtro é ignorado naquele sorteio.

### Serialização

`FinancialResult` é um dataclass — server.py deve usar `dataclasses.asdict()` antes de `jsonify()` para serializar corretamente.

---

## 4. Endpoints da API

### `POST /api/roi/backtest`

**Body:**
```json
{
  "filtros": {
    "soma": [171, 220],
    "pares": [6, 9],
    "primos": null,
    "fibonacci": null,
    "moldura": null,
    "repeticoes": null,
    "consecutivos": null
  },
  "n_jogos": 5,
  "janela": null
}
```

**Resposta:**
```json
{
  "estrategia": {
    "n_games": 17500,
    "total_cost": 45500.0,
    "total_revenue": 38220.0,
    "net_profit": -7280.0,
    "roi_pct": -16.0,
    "max_drawdown": -312.0,
    "sharpe": 0.31,
    "equity_curve": [...],
    "hits_distribution": {"11": 420, "12": 180, ...},
    "rate_ge": {"11": 0.042, "12": 0.012, "13": 0.003, "14": 0.0004, "15": 0.0}
  },
  "baseline": { ... mesma estrutura ... }
}
```

### `GET /api/roi/strategies`

Retorna lista de estratégias salvas de `saida/roi_strategies.json`.

### `POST /api/roi/strategies`

**Body:** `{"nome": "Minha-A", "filtros": {...}, "resumo": {"roi_pct": -16.0, ...}}`  
Appenda ao JSON, sem duplicar nomes (sobrescreve se mesmo nome).

### `DELETE /api/roi/strategies/:nome`

Remove entrada do JSON.

---

## 5. Interface — Aba "ROI Lab"

### Adição ao CATEGORIES

```js
{ id: 'roi_lab', icon: '🧪', label: 'ROI Lab' }
```

### Layout (3 zonas)

```
┌─────────────────────────────────────────────────────────────┐
│ ZONA 1: CONFIGURAR ESTRATÉGIA                               │
│                                                             │
│  Soma:        [171]════════════[220]                        │
│  Pares:       [  6]════════════[  9]                        │
│  Primos:      [  4]════════════[  7]                        │
│  Fibonacci:   [  3]════════════[  5]                        │
│  Moldura:     [  8]════════════[ 11]                        │
│  Repetições:  [  8]════════════[ 10]                        │
│  Consec. mín: [  2]                                         │
│                                                             │
│  Jogos/sorteio: [5]   Janela: [Todos ▾]                    │
│                                                             │
│  [▶ Rodar Backtest]  ← desativa durante execução           │
├─────────────────────────────────────────────────────────────┤
│ ZONA 2: RESULTADO                                           │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  ROI%       │  │  Sharpe     │  │  Drawdown   │        │
│  │  Estratégia │  │  Estratégia │  │  Estratégia │        │
│  │  -16%       │  │   0.31      │  │  -R$312     │        │
│  │  Baseline   │  │  Baseline   │  │  Baseline   │        │
│  │  -35%       │  │  -0.12      │  │  -R$1.820   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│  Equity Curve (canvas 100% largura)                        │
│  ── Estratégia    ---- Baseline                            │
│                                                             │
│  Distribuição de Acertos (bar chart)                       │
│  Hit rate ≥13: 4.2%  |  ≥14: 0.8%  |  ≥15: 0.02%         │
│                                                             │
│  Nome: [_______________]  [💾 Salvar estratégia]           │
├─────────────────────────────────────────────────────────────┤
│ ZONA 3: COMPARAÇÃO                                          │
│  Nome       │ ROI%  │ Sharpe │ Hit≥13 │ Drawdown │         │
│  Minha-A    │ -16%  │  0.31  │  4.2%  │  -R$312  │ [🗑]   │
│  Aleatório  │ -35%  │ -0.12  │  2.1%  │ -R$1.820 │ [🗑]   │
└─────────────────────────────────────────────────────────────┘
```

### Interação

- Cada filtro tem checkbox de ativação + range slider (ou single slider para `consecutivos`)
- Filtro desativado = slider cinza, não enviado no payload
- Equity curve usa `<canvas>` com desenho manual (padrão do projeto — sem libs externas)
- Cards de métricas mostram estratégia em destaque e baseline em subtexto cinza
- Baseline aleatório é sempre calculado junto e exibido para referência
- Tabela da Zona 3 carrega de `GET /api/roi/strategies` ao entrar na aba

---

## 6. Arquivos a criar/modificar

| Arquivo | Ação |
|---------|------|
| `src/lotofacil/servicos/roi_lab.py` | Criar |
| `src/lotofacil/interface/painel/server.py` | Adicionar 3 endpoints ROI |
| `src/lotofacil/interface/painel/static/dashboard.html` | Adicionar aba + renderRoiLab() |
| `testes/unidade/test_roi_lab.py` | Criar (testes do serviço) |

---

## 7. O que não está no escopo

- Auto-descoberta (leaderboard automático) — descartado pelo usuário em favor do comparador manual
- Integração com modelos ML — complexidade não justificada sem baseline positivo
- Persistência em SQLite — JSON simples é suficiente para o volume esperado
- Exportação CSV das estratégias — pode ser adicionado depois
