# Onda 10 — Usabilidade do Dashboard

**Prioridade: 🟡 Média-alta.** Polimento da experiência: feedback de erro,
progresso de treino com ETA, validação de formulários, persistência de estado e
visualização do histórico de acertos. Pode rodar em paralelo com a onda 11.

Base dos achados: `dashboard.html` (3745 linhas), `server.py` (1648 linhas).
Não há TODOs no código — os gaps abaixo vêm de análise de comportamento.

## Smoke test da onda

```bash
pytest src/lotofacil/interface/painel/tests/ -v
# manual: iniciar treino com epochs=0 → erro claro no formulário, sem request
# manual: derrubar API Caixa → toast de erro distinto de erro de validação
```

---

## Tasks

### - [x] 01 — Sistema de toasts e classificação de erros

- **Objetivo:** o usuário sempre distingue "você errou o input" de "o sistema falhou".
- **Descrição:** componente único de toast (sucesso/aviso/erro) em
  `dashboard.html`. Backend padroniza erros como
  `{erro: {tipo: "validacao"|"execucao", mensagem, detalhe?}}` com status HTTP
  coerente (400 vs 500). Modal de treino mostra a última linha de erro do
  TensorFlow resumida, com botão "ver log completo".
- **Arquivos:** `static/dashboard.html`, `server.py`.
- **Critérios de aceite:** POST inválido em `/api/treinos/iniciar` retorna 400 com
  `tipo: validacao`; toast aparece e some sozinho; teste de endpoint cobre o formato.
- **Commit:** `feat(painel): toasts e formato padronizado de erros`

### - [x] 02 — Validação de formulários no frontend

- **Objetivo:** impedir requests inválidas antes de sair do navegador.
- **Descrição:** validar no JS os ranges já impostos no backend: epochs [1,1000],
  window_size [5,500], `n_draws == 0 || n_draws >= window_size + 20`, nome
  (max 60 chars, slug-safe), n_jogos [1,20], n_numeros [11,15]. Campo inválido
  ganha borda vermelha + mensagem inline; botão submit desabilitado.
- **Arquivos:** `static/dashboard.html`.
- **Dependências:** 01 (usa o mesmo padrão visual de erro).
- **Critérios de aceite:** nenhum request sai com valores fora de range; mensagens
  inline aparecem ao digitar valor inválido.
- **Commit:** `feat(painel): validacao de formularios no frontend`

### - [x] 03 — Progresso real e ETA no modal de treino

- **Objetivo:** treino longo deixa de ser caixa-preta.
- **Descrição:** o stdout do Keras já traz `Epoch N/M` — parsear no backend
  (em `_run_command` ou no poll) e devolver `{epoch_atual, epoch_total,
  val_loss_atual, eta_segundos}` no payload do poll (ETA = média móvel do tempo
  por época × épocas restantes). Barra de progresso passa a ser proporcional
  real; exibir val_loss ao vivo e ETA formatada ("~4 min restantes").
- **Arquivos:** `server.py`, `treino_registry.py` (campo opcional de progresso),
  `static/dashboard.html`; teste do parser de época.
- **Critérios de aceite:** durante treino real, barra avança proporcional à época;
  parser coberto por teste unitário com linhas de exemplo do Keras.
- **Commit:** `feat(painel): progresso por epoca e ETA no modal de treino`

### - [x] 04 — Timeout e recuperação do polling

- **Objetivo:** polling nunca fica girando para sempre.
- **Descrição:** se o poll não recebe linha nova por N minutos (default 15,
  configurável), frontend mostra aviso "treino sem output há X min" com ações
  **Continuar aguardando** / **Cancelar job** (`/api/jobs/<id>/cancel` já existe).
  Reconexão automática em falha de rede com backoff (2s→30s) em vez de erro silencioso.
- **Arquivos:** `static/dashboard.html`.
- **Critérios de aceite:** matar o processo de treino na mão → aviso aparece;
  derrubar o servidor por 10s durante poll → reconecta sozinho.
- **Commit:** `feat(painel): timeout e reconexao no polling de jobs`

### - [x] 05 — Persistência de estado da UI (localStorage)

- **Objetivo:** refresh não joga fora o contexto do usuário.
- **Descrição:** persistir em localStorage: aba ativa, filtros do histórico
  (modelo, só premiados), página da tabela de dados, janela da validação,
  últimos parâmetros usados no formulário de treino e de geração de jogos.
- **Arquivos:** `static/dashboard.html`.
- **Critérios de aceite:** F5 mantém aba, filtros e últimos parâmetros de treino.
- **Commit:** `feat(painel): persistencia de filtros e aba em localStorage`

### - [x] 06 — Gráfico de acertos por modelo ao longo do tempo

- **Objetivo:** ver se um modelo melhora, piora ou empata com o acaso.
- **Descrição:** na sub-aba Histórico, gráfico de linha (canvas, mesmo estilo do
  ROI Lab): eixo X = concurso, Y = acertos médios por geração, uma série por
  modelo (selecionáveis), linha horizontal de referência em 9 (baseline
  aleatório) e em 11 (menor prêmio). Endpoint agregando `jogos_gerados` por
  modelo×concurso.
- **Arquivos:** `server.py` (novo endpoint `/api/jogos-gerados/series`),
  `static/dashboard.html`; teste do endpoint.
- **Critérios de aceite:** gráfico renderiza com ≥2 modelos; linha de baseline
  visível; endpoint testado.
- **Commit:** `feat(painel): grafico de acertos por modelo vs baseline`

### - [ ] 07 — Indicadores de frescor de cache e loading states

- **Objetivo:** o usuário sabe quando o dado é cacheado e quando algo está carregando.
- **Descrição:** cards servidos por cache (`/api/models/quality` TTL 120s,
  frequência TTL 300s) ganham selo "atualizado há Xs" + botão refresh que
  invalida (`?refresh=1`). Toda chamada fetch sem loader ganha skeleton/spinner
  padrão (Dados, Validação, Comparar).
- **Arquivos:** `server.py` (suporte a `?refresh=1`), `static/dashboard.html`.
- **Critérios de aceite:** selo mostra idade real do cache; refresh força recálculo;
  nenhuma aba abre "congelada" sem indicador.
- **Commit:** `feat(painel): frescor de cache e loading states`
