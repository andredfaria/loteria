# Spec: Comparação de Jogos Gerados com Sorteio Real

**Data:** 2026-05-20  
**Status:** Aprovado — pronto para planejamento  
**Escopo:** Dashboard Lotofácil — tela de Modelo (tabs Gerar e Histórico)

---

## Problema

Quando o usuário gera jogos para um concurso alvo que **já aconteceu**, o dashboard não mostra nenhum feedback sobre acertos. O tab Histórico já calcula acertos básicos, mas:

- O tab **Gerar** não exibe nenhuma comparação no ato da geração
- O tab **Histórico** não mostra o nome do prêmio (11/12/13/14/15 pontos)
- Não há resumo de quantos jogos foram premiados

---

## Objetivo

Mostrar automaticamente, quando o concurso alvo já aconteceu:
1. **Tab Gerar:** resultado inline logo após gerar os jogos
2. **Tab Histórico:** badge enriquecido com nome de prêmio + stats de premiados + filtro

---

## Arquitetura

### Camadas afetadas

| Camada | Arquivo | Mudança |
|--------|---------|---------|
| Infra (Flask) | `server.py` | Enriquecer resposta do endpoint `/api/treinos/{id}/gerar` |
| Interface (HTML/JS) | `static/dashboard.html` | `renderJogos()` + `_renderHistoricoPanel()` |

Sem novas rotas. Sem mudanças de schema no banco. Sem dependências externas.

---

## Mudanças no Backend

### `/api/treinos/{treino_id}/gerar` (POST)

**Localização:** `server.py`, função `api_treino_gerar()`, bloco `return jsonify(...)`.

Após calcular `next_concurso` e gerar `jogos`, adicionar:

```python
dezenas_reais = _get_draw_dezenas(next_concurso)
acertos_por_jogo = None
if dezenas_reais:
    real_set = set(dezenas_reais)
    acertos_por_jogo = [len(set(j) & real_set) for j in jogos]
```

Resposta enriquecida:

```json
{
  "treino_id": "...",
  "treino_nome": "...",
  "concurso": 3620,
  "n_jogos": 3,
  "n_numeros": 15,
  "jogos": [[1,3,7,...], ...],
  "dezenas_reais": [2,5,7,...],
  "acertos_por_jogo": [13, 11, 9]
}
```

`dezenas_reais` e `acertos_por_jogo` são `null` quando o concurso ainda não aconteceu. O frontend verifica `data.dezenas_reais != null` antes de renderizar a comparação.

**Função `_get_draw_dezenas(concurso)`** já existe em `server.py:1159` — sem mudanças.

---

## Mudanças no Frontend

### Mapeamento de prêmios (helper JS)

Adicionar função auxiliar no escopo global do dashboard:

```javascript
function _premioCat(hits) {
  if (hits === 15) return { label: '15 pontos 🏆', color: 'var(--accent)' };
  if (hits === 14) return { label: '14 pontos', color: 'var(--green)' };
  if (hits === 13) return { label: '13 pontos', color: 'var(--green)' };
  if (hits === 12) return { label: '12 pontos', color: 'var(--yellow)' };
  if (hits === 11) return { label: '11 pontos', color: 'var(--yellow)' };
  return { label: 'Sem prêmio', color: 'var(--red)' };
}
```

---

### Tab Gerar — `renderJogos(data)`

**Condição de ativação:** `data.dezenas_reais != null`

**Layout adicionado acima dos cards de jogos:**

```
┌─────────────────────────────────────────────────────────────┐
│ 🎯 Concurso 3620 já aconteceu — sorteio real               │
│ [02][05][07][09][11][12][14][15][17][18][20][21][22][24][25]│
└─────────────────────────────────────────────────────────────┘
```

- Bolas do sorteio real renderizadas com `_ballClass(n)` (hot/warm/cold) e opacidade normal
- Fundo levemente diferente (`rgba(255,255,255,0.04)`) com borda `var(--border)`

**Cada card de jogo** ganha:
- Bolas acertadas: `outline: 2px solid var(--green); opacity: 1`
- Bolas erradas: `opacity: 0.4`
- Badge no título: `13/15 — 13 pontos` na cor do prêmio

**Resumo ao final dos cards:**

```
Resultado geral: 1 jogo com 13 pontos · 1 jogo com 11 pontos · 1 jogo sem prêmio
```

Renderizado como linha de chips coloridos, um por jogo, em ordem.

---

### Tab Histórico — `_renderHistoricoPanel()`

**Badge por jogo** (já existe `${hits}/15 ✓`):  
Antes: `13/15 ✓`  
Depois: `13/15 — 13 pontos ✓`

**Stats header** — adicionar campo:  
`Premiados (11+): X jogos`  
Calculado em `_historicoStats()` iterando `acertos_por_jogo` e contando `h >= 11`.

**Filtro "Só premiados"** — checkbox na barra de filtros:
- Quando marcado, filtra `filtered` para manter apenas itens que têm pelo menos um jogo com `acertos_por_jogo[i] >= 11`
- Estado mantido em variável `_historicoSoPremiados` (boolean)
- `_onHistoricoFiltro()` já re-renderiza, basta ler o checkbox

---

## Casos de borda

| Situação | Comportamento |
|----------|---------------|
| Concurso futuro | `dezenas_reais: null` — nenhuma comparação exibida, comportamento atual mantido |
| Concurso existe mas `dezenas` está vazia | `_get_draw_dezenas` retorna `None` — tratado como concurso futuro |
| Jogo com n_numeros < 15 (ex: 11 dezenas) | Acertos calculados corretamente (interseção de conjuntos), badge mostra `X/11` se n_numeros < 15 — verificar se `n_numeros` deve ser incluído no denominador. **Decisão:** usar `len(jogo)` como denominador para exibição, mas o critério de prêmio Lotofácil exige 15 dezenas — badge de prêmio só aparece para jogos de 15 números. |
| `acertos_por_jogo` com índice faltando | Frontend usa `acertos[i] ?? null` com fallback seguro |

---

## Testes

- Backend: `testes/unidade/` — testar `api_treino_gerar` retorna `dezenas_reais` quando concurso existe e `null` quando não existe
- Frontend: verificação manual — gerar para concurso passado e confirmar exibição; gerar para concurso futuro e confirmar ausência de comparação

---

## Não incluído neste escopo

- Persistência de `dezenas_reais` no arquivo JSON salvo em `saida/jogos/` (os arquivos já existentes continuam sem esse campo)
- Notificação push ou alerta quando concurso futuro acontece
- Comparação retroativa para jogos antigos no Histórico que foram gerados antes desta feature (já funciona — `/api/jogos-gerados` já enriquece ao carregar)
