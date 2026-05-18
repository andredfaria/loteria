# Design: Fix climate_loader + Campo Concurso Alvo na Geração

**Data:** 2026-05-18  
**Status:** Aprovado

---

## Escopo

Dois itens independentes:

1. **Bug fix** — `ImportError` ao treinar modelos com config `clima` ou `lua+clima`
2. **Feature** — Campo "concurso alvo" na aba Gerar da tela de Modelos

---

## Parte A — Bug fix: `climate_loader.py`

### Problema

O container Docker (EasyPanel) roda uma versão antiga de `climate_loader.py` onde `get_climate_matrix` continha uma auto-importação interna quebrada:

```python
# versão antiga (dentro de get_climate_matrix)
from lotofacil.experimentos.data.climate_loader import load_all_climate, normalize_climate
```

Isso gera `ImportError: cannot import name 'load_all_climate'` ao treinar qualquer modelo com feature de clima.

### Solução

O arquivo local `src/lotofacil/experimentos/data/climate_loader.py` já está corrigido (aparece como `M` no git). A versão correta define `load_all_climate()` e `normalize_climate()` no escopo do módulo e `get_climate_matrix` as chama diretamente — sem auto-import.

**Ação necessária:** commit + push do arquivo modificado + rebuild no EasyPanel.

**Arquivos afetados:**
- `src/lotofacil/experimentos/data/climate_loader.py` (já corrigido localmente)

---

## Parte B — Feature: campo "concurso alvo"

### Comportamento atual

`POST /api/treinos/{treino_id}/gerar` calcula o concurso automaticamente:
```python
next_concurso = draws[-1].concurso + 1
```

Não há como especificar outro concurso via UI.

### Comportamento desejado

Na aba **Gerar**, o usuário pode digitar o número do concurso alvo. O campo vem pré-preenchido com `último_concurso + 1` (comportamento atual preservado como padrão).

### Design

#### Frontend — `dashboard.html`, função `renderPredGerar()`

O grid de parâmetros passa de 3 colunas para 4:

| Modelo treinado | Nº de jogos | Números por jogo | **Concurso alvo** |
|---|---|---|---|
| select | number | select | **number (novo)** |

- ID do novo campo: `gerarConcursoAlvo`
- Tipo: `<input type="number" min="1">`
- Valor padrão: `_predState.nextConcurso` (calculado ao carregar a lista de treinos, buscando `/api/status`)
- Função `gerarJogos()` lê o campo e passa `concurso_alvo` no body do POST

#### Backend — `server.py`, função `api_treino_gerar()`

```python
body = request.get_json(force=True) or {}
concurso_alvo_raw = body.get("concurso_alvo")
# ... (lógica existente de validação, load model, predict_proba) ...
if concurso_alvo_raw and int(concurso_alvo_raw) >= 1:
    next_concurso = int(concurso_alvo_raw)
else:
    next_concurso = draws[-1].concurso + 1
```

O parâmetro é **opcional** — ausência mantém comportamento atual (backward-compatible).

### Fluxo de dados

```
UI: input[concurso_alvo] pré-preenchido com último+1
  ↓ clica "Gerar Jogos"
POST /api/treinos/{id}/gerar  { n_jogos, n_numeros, concurso_alvo }
  ↓
backend: concurso = concurso_alvo (se válido) ou draws[-1].concurso + 1
  ↓
salva: saida/jogos/predicao_lab_{treino_id}_j{i}_{concurso}.json
  ↓
retorna: { concurso, jogos, treino_id, treino_nome, n_jogos, n_numeros }
  ↓
UI: "Concurso alvo: #XXXX · Modelo: nome"
```

### Arquivos afetados

- `src/lotofacil/interface/painel/static/dashboard.html` — `renderPredGerar()` e `gerarJogos()`
- `src/lotofacil/interface/painel/server.py` — `api_treino_gerar()`

### O que não muda

- API contract de resposta (`jogos`, `concurso`, etc.) — apenas o valor de `concurso` pode variar
- Nomes dos arquivos salvos em `saida/jogos/` usam o concurso escolhido (já era assim)
- Todos os outros campos do form permanecem iguais

---

## Critérios de aceitação

- [ ] Treinar modelo com config `clima` ou `lua+clima` não lança `ImportError`
- [ ] Campo "Concurso alvo" aparece na aba Gerar pré-preenchido com `último+1`
- [ ] Digitar outro concurso e gerar produz arquivo com o número correto
- [ ] Omitir o campo (ou deixar vazio) mantém comportamento atual
- [ ] Nenhum outro subtab da tela Modelos é afetado
