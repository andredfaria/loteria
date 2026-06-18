# Tela canônica "Jogos" — consolidação dos jogos gerados por modelos

**Data:** 2026-06-18
**Arquivo afetado:** `src/lotofacil/interface/painel/static/dashboard.html` (frontend, single-page)
**Backend:** nenhuma mudança — reaproveita `GET /api/jogos-gerados`

## Problema

A listagem de "jogos gerados por modelos" hoje vive em **três lugares** com lógica
duplicada e divergente, e um dos caminhos está **quebrado**:

1. **Aba Geração** — `carregarJogosGerados()` (`?limit=10`): faixa de estatísticas +
   cards com bolas, destaque de acertos e badge de prêmio. Inclui um botão
   **"Ver histórico completo"** que chama `switchTab('modelos')` +
   `showModelosSubTab('historico')`.
2. **Modelos → Gerar**, mini-widget `_loadGerarRecentes()` (`?limit=6`, mostra
   `slice(1,3)`): "Gerações anteriores", só bolas, sem acertos/badge.
3. **Histórico** — `renderPredHistorico()` / `_renderHistoricoPanel()` (sem limite):
   tabela completa com filtro por modelo, "só premiados", export CSV.

**Bug confirmado:** o layout atual de Modelos (`renderModelosPage`, duas seções
inline: Treinar+Lista | Gerar) não cria mais `#modelosSubnav` nem `#mod-historico`.
Logo `showModelosSubTab('historico')` e `renderPredHistorico()` não encontram seus
alvos no DOM — **a tela de Histórico (filtro, só-premiados, CSV) está inacessível**,
e o botão "Ver histórico completo" da aba Geração não faz nada útil.

O cálculo de estatísticas e a renderização de bolas foram reescritos em cada lugar,
com pequenas divergências (opacidade dos não-acertos, formato do badge, etc.).

## Decisão

Criar **uma tela canônica de nível superior "Jogos" (🎲)** no grupo CORE da navegação
(ao lado de Modelos). Ela passa a ser a única visão completa dos jogos gerados,
lendo de `GET /api/jogos-gerados` (sem limite), e absorve a funcionalidade da antiga
Histórico (filtro por modelo + "só premiados" + CSV) com o layout de cards (bolas)
— mais legível que a tabela antiga.

### Mudanças

1. **Navegação:** adicionar `{ id: 'jogos', icon: '🎲', label: 'Jogos' }` em
   `CATEGORIES` (CORE), depois de `modelos`.
2. **DOM:** adicionar `<div id="tab-jogos">` em `#contentSplit`; ligar em
   `switchTab` (display + `consoleSection` oculto + branch `renderJogosPage()`).
3. **Helpers compartilhados** (DRY core, junto de `_premioCat`):
   - `jogosStats(items)` → `{ totalGeracoes, totalJogos, media, melhor, comResultado, premiados }`
   - `jogosStatsStripHtml(stats)` → faixa de estatísticas
   - `renderJogoBalls(jogo, realSet, { dim })` → string de bolas com destaque de acerto
   - `renderGeracaoCard(item)` → card de uma geração (cabeçalho + linhas de jogo com badge)
   - `jogosGeradosCSV(items)` → dispara download do CSV
4. **Tela canônica** `renderJogosPage()` + estado `_jogosData`, `_jogosFiltroModelo`,
   `_jogosSoPremiados`, handler `_onJogosFiltro()`: cabeçalho (título + filtro de
   modelo + checkbox "só premiados" + botão CSV) + faixa de estatísticas + lista de
   cards por geração (via helpers).
5. **Remoções (dedup + dead code):**
   - Aba Geração passa a conter **só** a ferramenta de fechamento: remover a seção
     "Jogos Gerados por Modelos" + botão quebrado, e a chamada/função
     `carregarJogosGerados()`.
   - Remover código legado da Histórico: `renderPredHistorico`,
     `_renderHistoricoPanel`, `_historicoStats`, `_onHistoricoFiltro`,
     `_exportHistoricoCSV`, e o ramo `if (t === 'historico')` em
     `_renderActiveModSubTab`.
   - `_loadGerarRecentes()` (mini-widget de Modelos→Gerar) **permanece** (atalho útil
     logo após gerar), refatorado para usar `renderJogoBalls`.

### Não-objetivos

- Sem mudança de backend / endpoint / formato de payload.
- Sem alterar o fluxo de geração em si (Modelos→Gerar continua igual).
- Sem novo harness de teste JS (não existe no projeto); cobertura é via pytest do painel.

## Layout (tela Jogos)

```
🎲 Jogos Gerados        [Todos os modelos ▾] [☐ Só premiados]        [⬇ CSV]
Gerações: N · Jogos: M · Média acertos: X · Melhor: Y/15 · Premiados (11+): Z
┌───────────────────────────────────────────────────────────────┐
│ <modelo> · concurso N · DD/MM/AAAA HH:MM                        │
│ J1  ① ② ③ … (15 bolas, acertos destacados)   14/15 — 14 pontos  │
│ J2  …                                                           │
└───────────────────────────────────────────────────────────────┘
```

Quando o concurso ainda não ocorreu (`dezenas_reais` ausente), as bolas aparecem sem
destaque e sem badge — comportamento idêntico ao atual.

## Risco e verificação

- **Risco baixo:** frontend-only, sem mudança de contrato de API.
- Testes do painel (`pytest src/lotofacil/interface/painel/tests/ -v`) continuam válidos.
- Verificação manual das 3 superfícies: nova aba Jogos (filtro/só-premiados/CSV),
  aba Geração (só fechamento), mini-widget Modelos→Gerar.
