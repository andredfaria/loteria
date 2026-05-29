# ROI Lab Walk-Forward Backtest — Design Spec

**Data:** 2026-05-29  
**Status:** Aprovado  
**Limitação resolvida:** #5 — backtest ROI usa janela estática, sem separação treino/teste

---

## Contexto

O `rodar_backtest_roi` atual avalia filtros sobre **todo o histórico** disponível de uma vez. O usuário escolhe os ranges dos filtros (soma: [171,220], pares: [6,9], etc.) olhando para os dados históricos completos — e então avalia esses mesmos filtros no mesmo conjunto de dados.

**O problema:** o usuário inconscientemente fitou os filtros ao período avaliado. Não é possível saber se os filtros funcionariam em dados futuros. Isso é *look-ahead bias*.

**A solução não é automática** (sem otimização de filtros, porque ranges são definidos pelo usuário). A solução é **separar um período de teste** que o usuário se compromete a não usar para escolher os filtros — e o backtest só reporta performance nesse período.

---

## Design

### Novo parâmetro: `holdout_pct`

```python
def rodar_backtest_roi(
    filtros: dict,
    n_jogos_por_sorteio: int = 5,
    janela: int | None = None,
    holdout_pct: float = 0.0,   # ← NOVO (0.0 = sem holdout, 0.2 = últimos 20%)
) -> dict
```

**Comportamento:**
- `holdout_pct = 0.0` (padrão): comportamento atual — backtest em todos os sorteios
- `holdout_pct = 0.2`: os **últimos 20%** dos sorteios são o "conjunto de teste". O backtest reporta métricas **somente nesse subconjunto**. Os primeiros 80% existem conceitualmente para o usuário escolher os filtros (não são usados no backtest em si)

**Por que só os últimos N%?** Em séries temporais, o teste deve ser sempre posterior ao treino. Usar os últimos sorteios como teste simula o cenário real: "escolhi filtros olhando para o passado, agora vejo como teriam performado nos últimos X concursos".

### Resposta enriquecida

```json
{
  "estrategia": { ...FinancialResult... },
  "baseline":   { ...FinancialResult... },
  "meta": {
    "total_sorteios": 3700,
    "sorteios_treino": 2960,
    "sorteios_teste": 740,
    "holdout_pct": 0.2,
    "concurso_corte": 3200
  }
}
```

### Frontend

**Novo controle na aba ROI Lab:**

```
Holdout (período de teste): [20%] ▾
  Nenhum | 10% | 20% | 30%
```

**Badge no painel de resultados:**

```
⚠️ Métricas calculadas sobre os últimos 740 sorteios (corte no concurso #3200)
   Os filtros devem ter sido escolhidos usando os 2.960 sorteios anteriores.
```

O badge aparece apenas quando `holdout_pct > 0`. Quando é 0.0, o comportamento é idêntico ao atual (sem badge).

---

## Arquivos a modificar

| Arquivo | Mudança |
|---------|---------|
| `src/lotofacil/servicos/roi_lab.py` | Adicionar `holdout_pct` em `rodar_backtest_roi`, slicing correto dos sorteios, retornar `meta` |
| `src/lotofacil/interface/painel/server.py` | Ler `holdout_pct` do body do POST e repassar |
| `src/lotofacil/interface/painel/static/dashboard.html` | Select de holdout + badge condicional |
| `testes/unidade/servicos/test_roi_lab.py` | 3 testes novos para o holdout |

---

## Testes

```python
def test_holdout_pct_zero_usa_todos_sorteios():
    # n_games deve ser total_sorteios * n_jogos

def test_holdout_pct_02_usa_ultimos_20_pct():
    # n_games deve ser 0.2 * total_sorteios * n_jogos (arredondado)

def test_meta_retorna_concurso_corte_correto():
    # meta.concurso_corte deve ser o número do primeiro sorteio do período de teste
```

---

## O que não muda

- A lógica de geração de jogos (`_gerar_jogo_filtrado`, `_valida_filtros`) — sem alterações
- O `FinancialSimulator` — sem alterações
- O comportamento padrão (`holdout_pct=0.0`) — idêntico ao atual
- A tabela de estratégias salvas — o `holdout_pct` é salvo no `resumo` para referência
