# Backlog — Lotofácil Prediction System

> **Objetivo do sistema:** dashboard para predizer os números do próximo sorteio da
> Lotofácil com base em Machine Learning. Toda feature deste backlog deve servir a
> esse objetivo — ou tornando a predição melhor/mais honesta, ou tornando o uso do
> dashboard mais simples.

> **Princípio de honestidade:** loteria é evento aleatório independente. Modelos
> tendem a empatar com o acaso fora de amostra (AUC ≈ 0.5 no modelo_ordem). Toda
> métrica exibida deve sempre comparar contra o baseline aleatório (~9 acertos
> esperados em 15) e mostrar p-value. Nunca exibir métrica sem baseline.

---

## Estado atual (junho/2026)

O que já existe e funciona:

- **Coleta** — API Caixa + clima (Open-Meteo) + fase lunar, via CLI e dashboard
- **Modelos clássicos** — Frequency, Probabilistic, ML Ensemble (RF+XGB+LGBM), LSTM — `lotofacil modelo treinar` / `lotofacil prever`
- **Neural Lab** — LSTM+Attention+Focal Loss com features exógenas — `lotofacil lab train/predict`, integrado ao dashboard (aba Modelos: treinar, listar, gerar, comparar, histórico)
- **modelo_ordem** — LightGBM top-15 com split temporal honesto — **só em `scripts/`, não integrado**
- **Dashboard** — 5 abas (Coleta, Dados, Validação, Modelos, ROI Lab), jobs assíncronos com polling via SQLite
- **Avaliação** — walk-forward backtest, métricas financeiras (ROI, Sharpe), significância (p-value), ablation grid

## Gaps principais

1. Nenhuma tela destaca **a predição do próximo concurso** — razão de existir do sistema
2. modelo_ordem fora do CLI/dashboard
3. Sem **modelo campeão**: a predição padrão não usa automaticamente o melhor modelo validado
4. Validação contra resultado real é **manual** (`validar_predicoes`); sem loop automático pós-sorteio
5. Hiperparâmetros do neural quase todos fixos em `config.py`
6. UX: erros brutos no modal, sem ETA de treino, sem validação de formulário, filtros não persistem

---

## Ondas (ordem de execução)

| Onda | Tema | Prioridade | Tasks |
|------|------|-----------|-------|
| [09-predicao-proximo-concurso/](09-predicao-proximo-concurso/) | Tela "Próximo Concurso" + modelo campeão + integrar modelo_ordem | 🔴 Alta | 6 |
| [10-ux-dashboard/](10-ux-dashboard/) | Usabilidade: erros, ETA, validação, persistência, gráficos | 🟡 Média-alta | 7 |
| [11-treinamento/](11-treinamento/) | Hiperparâmetros expostos, presets, tuning, treino do modelo_ordem no painel | 🟡 Média | 6 |
| [12-automacao-validacao/](12-automacao-validacao/) | Loop automático: novo sorteio → validar → retreinar → promover campeão | 🟢 Média-baixa | 5 |

```
09 ──→ 10 (tela nova primeiro, polimento depois)
09 ──→ 11 (campeão definido antes de tuning)
11 ──→ 12 (automação por último — automatiza o fluxo já consolidado)
```

A onda 10 pode rodar em paralelo com a 11.

## Convenções (mesmas do refactor anterior)

- Nomes de módulos/classes/flags **em português** (loanwords técnicos ok: backtest, status)
- Cada task = 1 commit atômico; `pytest` deve passar após cada task
- Paths sempre via `lotofacil.infra.config` / `experimentos.config`
- Features sem vazamento de dados: apenas `draws[:t]` para predizer `t`
- Marque `- [x]` nas tasks ao completar

## Fora de escopo (por enquanto)

- Predição da **ordem** das dezenas (Modelo B / learning-to-rank) — decisão do design doc 2026-06-05
- WebSocket/SSE no dashboard — polling atual funciona com múltiplos workers Gunicorn
- Outros jogos (Mega-Sena, Dia de Sorte) — foco 100% Lotofácil
