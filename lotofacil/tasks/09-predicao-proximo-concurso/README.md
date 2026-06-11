# Onda 09 — Predição do Próximo Concurso em Destaque

**Prioridade: 🔴 Alta** — é o objetivo central do sistema e hoje não existe.

O dashboard tem histórico de predições, treinos e jogos gerados, mas nenhuma tela
responde a pergunta principal: **"quais números jogar no próximo concurso?"**.
Esta onda cria essa tela, define o conceito de **modelo campeão** e integra o
modelo_ordem (LightGBM) que hoje vive em scripts soltos.

## Smoke test da onda

```bash
pytest
lotofacil prever                                  # usa o campeão automaticamente
curl -s localhost:5000/api/predicao/proxima | python -m json.tool
# dashboard: primeira tela ao abrir = hero "Próximo Concurso" com 15 dezenas
```

---

## Tasks

### - [x] 01 — Serviço `predicao_proximo_concurso`

- **Objetivo:** caso de uso único que consolida a predição do próximo concurso.
- **Descrição:** novo serviço que: detecta o próximo concurso (último do DB + 1),
  carrega o modelo campeão (task 03; enquanto não existir, usa ensemble),
  retorna `{concurso_alvo, data_prevista, dezenas, confianca_por_dezena, modelo,
  gerado_em, baseline_esperado: 9}`. Data prevista calculada do calendário de
  sorteios (seg–sáb).
- **Arquivos:** criar `src/lotofacil/servicos/predicao_proximo_concurso.py`;
  teste `testes/unidade/servicos/test_predicao_proximo_concurso.py`.
- **Dependências:** nenhuma.
- **Critérios de aceite:** teste unitário com DB fake passa; serviço nunca usa
  dados do próprio concurso alvo (sem vazamento).
- **Commit:** `feat(servicos): predicao consolidada do proximo concurso`

### - [x] 02 — Endpoint `GET /api/predicao/proxima`

- **Objetivo:** expor o serviço da task 01 no painel.
- **Descrição:** endpoint que chama o serviço e devolve JSON; cache curto (60s);
  parâmetro `?gerar=1` força regeneração (job assíncrono via `_run_command` se
  o modelo precisar rodar predição pesada).
- **Arquivos:** `src/lotofacil/interface/painel/server.py`;
  teste em `src/lotofacil/interface/painel/tests/test_server.py`.
- **Dependências:** 01.
- **Critérios de aceite:** `curl /api/predicao/proxima` retorna dezenas + metadados;
  teste de endpoint passa.
- **Commit:** `feat(painel): endpoint /api/predicao/proxima`

### - [x] 03 — Modelo campeão (champion)

- **Objetivo:** o sistema sabe qual é o melhor modelo e o usa por padrão.
- **Descrição:** arquivo `saida/campeao.json` com `{modelo, tipo, arquivo,
  metricas: {mean_hits, p_value, n_validacoes}, promovido_em}`. Serviço
  `promover_campeao.py` que ranqueia candidatos por mean_hits validado em
  walk-forward (mínimo 20 validações; só promove se p_value < 0.05 vs aleatório,
  caso contrário campeão = ensemble com aviso "nenhum modelo supera o acaso").
  CLI: `lotofacil modelo campeao` (mostra) e `lotofacil modelo promover` (recalcula).
- **Arquivos:** criar `src/lotofacil/servicos/promover_campeao.py`;
  `src/lotofacil/interface/cli/modelo.py`; teste unitário.
- **Dependências:** nenhuma (01 consome depois).
- **Critérios de aceite:** com histórico de validações fake, promove o correto;
  sem validações suficientes, mantém ensemble e registra motivo.
- **Commit:** `feat(modelo): selecao e promocao do modelo campeao`

### - [x] 04 — Tela hero "Próximo Concurso" no dashboard

- **Objetivo:** primeira coisa que o usuário vê = predição do próximo sorteio.
- **Descrição:** nova aba/tela inicial em `dashboard.html`: número e data do
  próximo concurso, 15 dezenas em bolas grandes (estilo do DESIGN-SYSTEM),
  nome do modelo campeão + badge de confiança, aviso de honestidade
  ("baseline aleatório: ~9 acertos"), botões **Gerar predição**, **Copiar
  dezenas** e **Ver jogos do portfolio**. Estado vazio claro quando não há
  modelo/dados ("Atualize a base e treine um modelo").
- **Arquivos:** `src/lotofacil/interface/painel/static/dashboard.html`.
- **Dependências:** 02.
- **Critérios de aceite:** ao abrir `/`, tela hero carrega de
  `/api/predicao/proxima`; funciona em mobile (bottom-nav); estado vazio testável
  apagando `saida/`.
- **Commit:** `feat(painel): tela hero de predicao do proximo concurso`

### - [x] 05 — Integrar modelo_ordem ao CLI `lotofacil lab`

- **Objetivo:** tirar o LightGBM top-15 de `scripts/` e torná-lo cidadão de
  primeira classe.
- **Descrição:** subcomandos `lotofacil lab train-ordem` (encapsula
  `scripts/train_modelo_ordem.py`: build do dataset + treino + avaliação honesta)
  e `lotofacil lab prever-ordem` (inferência top-15 do `scripts/prever_proximo.py`).
  Salvar modelo + meta.json em `saved_models/` com mesmo padrão dos neurais.
  Scripts antigos viram wrappers finos ou são deletados.
- **Arquivos:** `src/lotofacil/experimentos/main.py`,
  `src/lotofacil/experimentos/models/modelo_ordem_lgbm.py`,
  `scripts/train_modelo_ordem.py`, `scripts/prever_proximo.py`;
  teste smoke em `testes/integracao/cli/`.
- **Dependências:** nenhuma.
- **Critérios de aceite:** `lotofacil lab train-ordem --help` funciona; treino
  em dataset sample completa; predição retorna 15 dezenas válidas (1–25, únicas).
- **Commit:** `feat(lab): integra modelo_ordem (LightGBM) ao CLI`

### - [ ] 06 — modelo_ordem como candidato a campeão e abordagem do painel

- **Objetivo:** modelo_ordem participa da predição padrão e do dashboard.
- **Descrição:** registrar `ordem` como abordagem em `commands.py` (botões
  treinar/prever), incluí-lo nos candidatos de `promover_campeao` e na
  comparação de qualidade (`/api/models/quality`).
- **Arquivos:** `src/lotofacil/interface/painel/commands.py`,
  `src/lotofacil/servicos/promover_campeao.py`, `server.py`.
- **Dependências:** 03, 05.
- **Critérios de aceite:** dashboard treina e prevê com modelo_ordem; aparece no
  leaderboard de validação com p-value.
- **Commit:** `feat(painel): modelo_ordem como abordagem no dashboard`
