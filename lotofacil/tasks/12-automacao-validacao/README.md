# Onda 12 — Automação do Ciclo: Sorteio → Validação → Retreino → Campeão

**Prioridade: 🟢 Média-baixa** (depende das ondas 09 e 11). Fecha o loop: hoje
`validar_predicoes` é manual e não há retreino agendado, embora a infra exista
(`infra/agendador/` com APScheduler e constantes `SCHEDULE_*` em `infra/config.py`
— sorteios seg–sáb, atualização configurada para seg/qua/sex 23h).

Objetivo final: o usuário abre o dashboard na manhã seguinte ao sorteio e vê,
sem ter feito nada: resultado real, acertos de cada predição, métricas
atualizadas e o campeão re-eleito.

## Smoke test da onda

```bash
pytest
lotofacil dados atualizar --escopo ultimo   # dispara validação automática no final
# dashboard: card "último sorteio validado" na tela hero com acertos da predição
```

---

## Tasks

### - [x] 01 — Validação automática após atualização de dados

- **Objetivo:** nunca mais rodar `validar_predicoes` na mão.
- **Descrição:** ao final de `atualizar_base` (quando chegam concursos novos),
  chamar `validar_todas_pendentes()` automaticamente e logar o resumo
  ("3 predições validadas para o concurso 3701: 10, 9 e 11 acertos").
  Flag `--sem-validar` para desligar.
- **Arquivos:** `src/lotofacil/servicos/atualizar_base.py`,
  `src/lotofacil/servicos/validar_predicoes.py`; teste unitário com DB fake.
- **Dependências:** nenhuma.
- **Critérios de aceite:** teste prova que predições pendentes do concurso novo
  ficam validadas após o update; `--sem-validar` pula a etapa.
- **Commit:** `feat(servicos): validacao automatica de predicoes pos-atualizacao`

### - [ ] 02 — Agendador ativo no container do dashboard

- **Objetivo:** coleta + validação rodam sozinhas nos dias de sorteio.
- **Descrição:** ativar `infra/agendador/atualizador.py` (APScheduler) dentro do
  processo Gunicorn (apenas 1 worker agenda — usar lock por arquivo ou
  `BackgroundScheduler` guardado por env `SCHEDULER_ENABLED=1`). Jobs: atualizar
  base ~30 min após o horário do sorteio (todos os dias de sorteio, não só
  seg/qua/sex — revisar `SCHEDULE_UPDATE_DAYS`), com retry. Registrar execuções
  no SQLite para o painel exibir.
- **Arquivos:** `src/lotofacil/infra/agendador/atualizador.py`,
  `src/lotofacil/interface/painel/server.py`, `src/lotofacil/infra/config.py`,
  `Dockerfile`/`docker-compose.yml` (env); teste de configuração dos jobs.
- **Dependências:** 01.
- **Critérios de aceite:** com `SCHEDULER_ENABLED=1`, jobs aparecem agendados em
  endpoint de status; com 2 workers Gunicorn, apenas um agenda (sem dupla coleta).
- **Commit:** `feat(agendador): coleta e validacao agendadas no painel`

### - [ ] 03 — Predição automática pós-validação

- **Objetivo:** sempre existe predição fresca para o próximo concurso.
- **Descrição:** após validar um concurso novo (task 01/02), gerar
  automaticamente a predição do próximo usando o campeão (serviço da onda 09
  task 01) e registrá-la no histórico — assim a tela hero nunca está vazia e
  toda predição é registrada *antes* do sorteio (auditável, sem retro-predição).
  Configurável por env `AUTO_PREVER=1`.
- **Arquivos:** `src/lotofacil/servicos/atualizar_base.py` (orquestração),
  `src/lotofacil/servicos/predicao_proximo_concurso.py`; teste.
- **Dependências:** 01; onda 09 tasks 01 e 03.
- **Critérios de aceite:** ciclo simulado em teste: novo sorteio → validação →
  nova predição registrada para concurso+1 com timestamp anterior ao sorteio.
- **Commit:** `feat(servicos): predicao automatica do proximo concurso pos-validacao`

### - [ ] 04 — Re-eleição automática do campeão

- **Objetivo:** o campeão reflete sempre a performance validada mais recente.
- **Descrição:** após cada lote de validações, rodar `promover_campeao`
  (onda 09 task 03). Logar mudanças ("campeão trocou de X para Y:
  mean_hits 9.8→10.1, p=0.03") e manter histórico de promoções em
  `saida/campeao_historico.json` para auditoria. Histerese: só troca se o
  desafiante superar o atual por margem mínima (ex.: +0.1 mean_hits) para
  evitar flip-flop.
- **Arquivos:** `src/lotofacil/servicos/promover_campeao.py`, orquestração em
  `atualizar_base.py`; teste de histerese.
- **Dependências:** 01; onda 09 task 03.
- **Critérios de aceite:** teste: desafiante marginalmente melhor NÃO troca;
  desafiante acima da margem troca e registra no histórico.
- **Commit:** `feat(servicos): re-eleicao automatica do campeao com histerese`

### - [ ] 05 — Card "Último sorteio" e linha do tempo de automação no painel

- **Objetivo:** dar visibilidade ao que a automação fez.
- **Descrição:** na tela hero (onda 09 task 04): card com o último sorteio real,
  as dezenas preditas vs sorteadas (acertos destacados) e o delta vs baseline.
  Nova seção "Automação" (pode viver na aba Coleta): timeline das últimas
  execuções agendadas (coleta, validação, predição, promoção) com status e
  duração, lidas do registro da task 02.
- **Arquivos:** `static/dashboard.html`, `server.py` (endpoint
  `/api/automacao/execucoes`).
- **Dependências:** 02, 03, 04.
- **Critérios de aceite:** após ciclo completo (pode ser disparado manualmente),
  hero mostra acertos do último concurso e a timeline lista as 4 etapas.
- **Commit:** `feat(painel): card ultimo sorteio e timeline de automacao`
