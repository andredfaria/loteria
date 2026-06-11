# Onda 11 — Melhorias no Treinamento

**Prioridade: 🟡 Média.** Hoje só `epochs`, `seed`, `window_size` e `fast` são
configuráveis; o resto está fixo em `experimentos/config.py` (batch_size,
dropout, learning rate, patience, focal loss, val_split). Esta onda expõe o que
importa, cria presets para não assustar usuário leigo, e traz tuning honesto
com walk-forward. Pode rodar em paralelo com a onda 10.

## Smoke test da onda

```bash
pytest
lotofacil lab train --config base+temp+priors --preset rapido
lotofacil lab tune --config base+temp+priors --n-trials 5 --fast
# dashboard: formulário de treino com modo simples (presets) e avançado
```

---

## Tasks

### - [x] 01 — Expor hiperparâmetros do neural na CLI

- **Objetivo:** experimentar sem editar `config.py`.
- **Descrição:** flags novas em `lotofacil lab train`: `--batch-size`,
  `--learning-rate`, `--dropout`, `--patience`, `--val-split`,
  `--focal-gamma`, `--focal-alpha`, `--lstm-units` (ex.: `256,128,64`).
  Defaults continuam vindo de `config.py`. Valores efetivos gravados no
  `.meta.json` do modelo (hoje já grava config — garantir que inclui todos).
- **Arquivos:** `src/lotofacil/experimentos/main.py`,
  `src/lotofacil/experimentos/models/neural_modular.py`; teste de parsing.
- **Critérios de aceite:** `--help` documenta todas; treino fast com
  `--batch-size 64 --dropout 0.2` completa e meta.json reflete os valores.
- **Commit:** `feat(lab): hiperparametros do neural expostos na CLI`

### - [x] 02 — Presets de treino (rápido / equilibrado / completo)

- **Objetivo:** usuário leigo escolhe 1 de 3 opções em vez de 8 números.
- **Descrição:** `--preset rapido|equilibrado|completo` na CLI:
  - **rapido** — modo fast atual (LSTM [64,32,16], batch 64, ~5–10 min CPU)
  - **equilibrado** — LSTM [128,64,32], epochs 60, patience 8 (~20–40 min)
  - **completo** — defaults atuais (LSTM [256,128,64], epochs 100, ~1–2h CPU)
  Presets definidos em dict único em `config.py`; flags explícitas sobrescrevem preset.
- **Arquivos:** `src/lotofacil/experimentos/config.py`, `main.py`; teste.
- **Dependências:** 01.
- **Critérios de aceite:** os 3 presets treinam no dataset sample; flag explícita
  vence o preset; meta.json registra o preset usado.
- **Commit:** `feat(lab): presets de treino rapido/equilibrado/completo`

### - [ ] 03 — Formulário de treino do painel: modo simples e avançado

- **Objetivo:** dashboard acompanha as tasks 01–02.
- **Descrição:** formulário da sub-aba Treinar ganha duas seções: **Simples**
  (cards de preset com estimativa de duração + escolha de features, que já
  existe) e **Avançado** (colapsável, com os hiperparâmetros da task 01,
  pré-preenchidos pelo preset). Backend `api_treinos_iniciar` aceita e valida
  os novos parâmetros e monta a linha de comando.
- **Arquivos:** `static/dashboard.html`, `server.py`,
  `treino_registry.py` (parametros já são JSON — sem migração); testes de endpoint.
- **Dependências:** 01, 02; onda 10 task 02 (validação) se já existir.
- **Critérios de aceite:** treino disparado com preset "rapido" completa;
  seção avançada sobrescreve preset; parâmetros aparecem no detalhe do treino.
- **Commit:** `feat(painel): formulario de treino com presets e modo avancado`

### - [x] 04 — Tuning com busca aleatória + walk-forward (`lotofacil lab tune`)

- **Objetivo:** encontrar hiperparâmetros melhores sem se enganar (sem overfitting
  ao período de validação).
- **Descrição:** comando `lotofacil lab tune --config <features> --n-trials N`:
  amostra hiperparâmetros (lr log-uniforme, dropout, batch, units) de espaço
  definido em `config.py`, avalia cada trial com walk-forward curto
  (reaproveitar `evaluation/walkforward.py`), ranqueia por mean_hits com
  p-value vs baseline aleatório, salva `saida/experimentos/tuning_<data>.json`
  + markdown resumo. `--fast` usa preset rapido por trial.
- **Arquivos:** criar `src/lotofacil/experimentos/experiments/tuning.py`;
  `main.py`; teste smoke com n-trials=2 fast.
- **Dependências:** 01.
- **Critérios de aceite:** `tune --n-trials 2 --fast` completa no sample;
  relatório lista trials ordenados com métricas e p-value; nenhum trial usa
  dados futuros (asserção no teste).
- **Commit:** `feat(lab): tuning por busca aleatoria com walk-forward`

### - [ ] 05 — Treino do modelo_ordem pelo dashboard

- **Objetivo:** o LightGBM (mais barato que o neural: ~1–2 min) treinável pela UI.
- **Descrição:** depois da onda 09 task 05/06, adicionar no formulário de treino
  a opção de tipo de modelo: **Neural (LSTM)** ou **Ordem (LightGBM)**. Para
  ordem, formulário reduzido (features + seed + n_estimators/learning_rate em
  avançado). Mesmo fluxo de job/registry/histórico.
- **Arquivos:** `static/dashboard.html`, `server.py`, `commands.py`.
- **Dependências:** onda 09 tasks 05–06; task 03 desta onda.
- **Critérios de aceite:** treino de ordem dispara pelo painel, completa em
  minutos, aparece na lista de modelos e pode gerar jogos.
- **Commit:** `feat(painel): treino do modelo_ordem pelo dashboard`

### - [ ] 06 — Baseline aleatório sempre visível nas métricas de treino

- **Objetivo:** honestidade estatística em todo lugar que mostra qualidade.
- **Descrição:** todo card/tabela de métricas (lista de modelos, comparar A/B,
  leaderboard, detalhe do treino) exibe junto: acertos esperados do acaso (~9/15,
  hipergeométrico), delta do modelo vs acaso e p-value quando houver validações.
  Tooltip explicando "por que 9". Componente/formatter único no JS para não
  duplicar.
- **Arquivos:** `static/dashboard.html`, `server.py` (incluir baseline nos
  payloads onde falta).
- **Critérios de aceite:** nenhuma métrica de hits aparece sem o baseline ao lado;
  comparar A/B mostra os dois modelos contra o acaso, não só entre si.
- **Commit:** `feat(painel): baseline aleatorio visivel em todas as metricas`
