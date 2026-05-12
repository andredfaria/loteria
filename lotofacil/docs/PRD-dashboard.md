# PRD — Lotofácil Dashboard (Web)

**Versão:** 1.0  
**Data:** 2026-05-11  
**Status:** Documento de referência do sistema atual

---

## 1. Visão Geral

O **Lotofácil Dashboard** é uma interface web local que expõe todas as capacidades do sistema de análise e predição da Lotofácil através de um navegador. O objetivo é eliminar o uso direto do terminal para operações do dia a dia — coleta de dados, treinamento de modelos, geração de jogos, análise de predições e experimentos de laboratório — mantendo visibilidade em tempo real do que está sendo executado.

**Público-alvo:** usuário único (analista/desenvolvedor do próprio sistema), rodando localmente via `localhost:5000`.

**Stack:**
- Backend: Python + Flask (SSE para streaming)
- Frontend: HTML + CSS + JavaScript vanilla (sem frameworks)
- Comunicação: REST API + Server-Sent Events (EventSource)

---

## 2. Arquitetura do Sistema

```
Browser (dashboard.html)
       │
       ├── GET  /               → serve dashboard.html
       ├── GET  /api/commands   → catálogo de ações disponíveis
       ├── GET  /api/status     → métricas da navbar (sorteios, último concurso, jogos)
       ├── GET  /api/games      → lista de arquivos em saida/jogos/*.json
       ├── GET  /api/games/:f   → conteúdo de um arquivo de jogo
       ├── GET  /api/predictions→ predições agrupadas por concurso
       ├── GET  /api/models/status → modelos .keras em output/models/ e lotofacil_lab/saved_models/
       ├── POST /api/generate   → dispara comando CLI em background → retorna task_id
       └── GET  /api/stream/:id → SSE stream de stdout do processo

Backend (server.py + Flask)
       │
       ├── _run_command()       → subprocess.Popen → fila de mensagens (queue.Queue)
       ├── _last_concurso_info()→ glob de dados/concurso_*.json
       ├── _list_game_files()   → glob de saida/jogos/*.json (20 mais recentes)
       ├── _list_predictions()  → glob de saida/jogos/predicao_*.json, agrupa por concurso
       └── _scan_models()       → glob de *.keras em output/models/ e saved_models/

CLI (lotofacil — Typer)
       ├── prever               → ElevenNumbersStrategy → salva predicao_{approach}_{N}.json
       ├── dados atualizar      → LotofacilFetcher → dados/concurso_*.json
       ├── modelo treinar       → FrequencyModel + MLEnsemble + LSTM
       ├── modelo backtest      → BacktestEngine walk-forward
       ├── modelo validar       → confere predições contra resultados reais
       ├── modelo historico     → exibe últimas 20 predições
       ├── portfolio            → portfólio tiered → saida/jogos/
       └── lab *                → experimentos (clima, lua, ablation)
```

---

## 3. Layout Visual

```
┌─────────────────────────────────────────────────────────────────┐
│ NAVBAR: 🎰 Lotofácil Dashboard  │ ⏱ hora │ 🎯 Sorteios: N │ ... │
├──────────┬──────────────────────────────────────────────────────┤
│          │  ACTIONS BAR (botões da aba ativa)                    │
│ SIDEBAR  ├──────────────────────────────────────────────────────┤
│          │                                                        │
│ 📥 Coleta│  NUMBERS SECTION (cards de jogos ou predições)        │
│ 🤖 Predição│                                                     │
│ 🎯 Treino│──────────────────────────────────────────────────────│
│ 📊 Análise│                                                      │
│ 🎲 Geração│  CONSOLE (output em tempo real do processo)          │
│ 🔬 Lab   │                                                        │
│ 🏷️ Jogos │                                                        │
│ 🎯 Predições│                                                     │
│ 🧠 Modelos│                                                      │
└──────────┴──────────────────────────────────────────────────────┘
```

Em mobile (< 768px): sidebar colapsa para apenas ícones; cards de jogos viram coluna única; itens da navbar ocultam texto.

---

## 4. Componentes

### 4.1 Navbar

Exibição de métricas globais, atualizadas a cada 30 segundos via `/api/status`:

| Elemento | Dado | Fonte |
|---|---|---|
| ⏱ hora | `timestamp` ISO → `toLocaleTimeString()` | server |
| 🎯 Sorteios | `total_draws` | contagem de `dados/concurso_*.json` |
| 📌 Último | `last_concurso.concurso` + `(data)` | último arquivo JSON de dados |
| 🎲 Jogos | `games_count` | contagem de `saida/jogos/*.json` (max 20) |
| 🟢 Online | indicador fixo verde | sempre visível enquanto servidor responde |

### 4.2 Sidebar — Abas de Navegação

Cada aba ativa a renderização de botões de ação correspondentes na `actions-bar`.

| Aba | ID | Tipo |
|---|---|---|
| 📥 Coleta | `coleta` | ações CLI |
| 🤖 Predição | `predicao` | ações CLI |
| 🎯 Treinamento | `treinamento` | ações CLI |
| 📊 Análise | `analise` | ações CLI |
| 🎲 Geração | `geracao` | ações CLI |
| 🔬 Lab | `lab` | ações CLI |
| 🏷️ Jogos | `jogos` | visualização de arquivos |
| 🎯 Predições | `predicoes` | visualização agrupada |
| 🧠 Modelos | `modelos` | inventário de modelos |

### 4.3 Actions Bar

Renderiza os botões da aba ativa. Para abas de ações CLI, os dados vêm de `/api/commands` (COMMANDS dict definido em `commands.py`). Para as abas especiais (Jogos, Predições, Modelos) renderiza apenas botão "Atualizar".

**Comportamento de botão em execução:**
- Classe CSS `running` → borda pulsa entre amarelo e laranja
- Botão fica `disabled` enquanto o processo corre
- Timer `mm:ss` aparece dentro do botão, incrementado a cada segundo via `setInterval`
- Ao concluir: toast de sucesso + refresh automático da seção relevante

### 4.4 Numbers Section

Exibe cards com os jogos mais recentes de `saida/jogos/` (máx. 12 visíveis). Cada card:
- Título: nome do arquivo JSON
- Bolas coloridas: números 01–12 em azul (`#1e3a5f`), números 13–25 em amarelo (`#2d1f00`)
- Clique → abre modal com todos os jogos do arquivo + JSON bruto

**Extração de números (`extractNumbers`):** suporta múltiplos formatos de arquivo:

| Formato | Exemplo |
|---|---|
| Array plano | `[1, 5, 12, ...]` |
| Array de arrays | `[[1,5,...], [2,6,...]]` |
| Array de objetos | `[{dezenas: [...]}, ...]` |
| Objeto simples | `{dezenas: [...]}` |
| Portfólio tiered | `{jogos: {conservador: [...], ...}}` |

Quando a aba ativa é **Predições**, a mesma `numbers-section` exibe grupos por concurso, ordenados do mais recente ao mais antigo. Cada grupo mostra linhas `pred-row` com: `abordagem`, bolas e badge de `confianca`.

Quando a aba ativa é **Modelos**, exibe `model-card` com nome, grupo (core/lab), data de treinamento, épocas, val_loss final e tamanho em MB.

### 4.5 Console

Output em tempo real, estilo terminal:

| Classe CSS | Trigger |
|---|---|
| `cmd` | linhas começando com `$` |
| `success` | linhas com `✅` / "sucesso" / "concluído" |
| `error` | linhas com `❌` / "erro" / `Traceback` / `Exception` |
| `warn` | linhas com `⚠` |
| `sep` | separadores visuais entre execuções |
| `dim` | mensagens de sistema |

**Persistência:** as últimas 150 linhas são salvas em `localStorage` (`lotofacil_console_v1`) e restauradas na próxima sessão com separador "— sessão anterior —".

**Botão limpar:** remove DOM, apaga `STATE.consoleLines` e `localStorage`.

### 4.6 Modal

Exibe todos os jogos de um arquivo ao clicar em um game-card. Mostra:
1. Grupos de bolas numerados ("Jogo 1", "Jogo 2", ...)
2. JSON bruto completo em `<pre>` para debug

Fecha ao clicar no overlay ou no botão `×`.

### 4.7 Toast

Notificação temporária (3s) no canto inferior direito. Tipos: `success` (borda verde), `error` (borda vermelha), `info` (borda azul).

---

## 5. Catálogo de Ações CLI

### 5.1 Coleta

| ID | Label | Comando |
|---|---|---|
| `collect_sync` | Atualizar Base | `lotofacil dados atualizar` |
| `collect_all` | Importar Tudo | `lotofacil dados atualizar --all` |
| `collect_latest` | Buscar Último | `lotofacil dados atualizar --latest` |
| `status` | Status do DB | `lotofacil dados status` |
| `historico` | Histórico de Predições | `lotofacil modelo historico` |

### 5.2 Predição

| ID | Label | Comando |
|---|---|---|
| `predict_all` | Prever (ensemble) | `lotofacil prever` |
| `predict_ml` | Prever (só ML) | `lotofacil prever --approach ml` |
| `predict_portfolio` | Gerar Portfólio | `lotofacil portfolio` |
| `predict_portfolio_8` | Gerar Portfólio (8 jogos) | `lotofacil portfolio --jogos 8` |

### 5.3 Treinamento & Validação

| ID | Label | Comando |
|---|---|---|
| `ml_train` | Treinar Modelos | `lotofacil modelo treinar` |
| `ml_backtest` | Backtest | `lotofacil modelo backtest` |
| `ml_validar` | Validar Predições | `lotofacil modelo validar` |

### 5.4 Análise

| ID | Label | Comando |
|---|---|---|
| `analise_historico` | Histórico de Predições | `lotofacil modelo historico` |
| `analise_validar` | Validar Predições | `lotofacil modelo validar` |
| `analise_status` | Status do Banco | `lotofacil dados status` |
| `analise_backtest` | Backtest | `lotofacil modelo backtest` |

### 5.5 Geração de Jogos

| ID | Label | Comando |
|---|---|---|
| `geracao_portfolio` | Gerar Portfólio | `lotofacil portfolio` |
| `geracao_portfolio_8` | Gerar Portfólio (8 jogos) | `lotofacil portfolio --jogos 8` |
| `geracao_prever` | Prever (ensemble) | `lotofacil prever` |

### 5.6 Lab (Experimentos)

| ID | Label | Comando |
|---|---|---|
| `lab_backfill_clima` | Backfill Clima | `lotofacil lab backfill-clima` |
| `lab_lunar_check` | Lunar Check (hoje) | `lotofacil lab lunar-check --data <hoje>` |
| `lab_ablation` | Ablation Study | `lotofacil lab ablation --n-test 50` |

---

## 6. Fluxo de Execução de Comando

```
[Usuário clica botão]
        │
        ▼
runCommand(actionId)
  → marca runningTasks.add(actionId)
  → desabilita botão + inicia timer mm:ss
  → addConsoleLine("▶ Executando: ...", 'cmd')
        │
        ▼
POST /api/generate  { action: actionId }
  → Flask: localiza item em COMMANDS
  → cria task_id único
  → inicia Thread: _run_command(task_id, queue, cmd, cwd)
  → retorna { task_id }
        │
        ▼
listenStream(task_id)  ← EventSource /api/stream/{task_id}
  → data.type === 'stdout'  → addConsoleLine(text)
  → data.type === 'heartbeat' → no-op (keep-alive 0.5s)
  → event 'done'
      → fecha EventSource
      → remove runningTasks
      → para timer
      → addConsoleLine("✅ ... concluído", 'success')
      → showToast(sucesso)
      → refresh automático (loadGames / loadPredictions / loadModels / loadStatus)
```

**Tratamento de erro:** se `onerror` dispara, exibe warn no console e toast de erro. Botão volta ao estado normal.

---

## 7. API — Contratos de Dados

### `GET /api/status`
```json
{
  "last_concurso": { "concurso": 3681, "data": "09/05/2026" },
  "total_draws": 3681,
  "games_count": 5,
  "timestamp": "2026-05-11T10:30:00.000"
}
```

### `GET /api/games`
```json
[
  { "filename": "portfolio_3682.json", "concurso": "3682",
    "size": 1234, "mtime": "2026-05-10T22:00:00" },
  ...
]
```
Máximo 20 arquivos, ordenados por mtime desc.

### `GET /api/games/:filename`
Retorna conteúdo JSON do arquivo. O filename é sanitizado com `Path(filename).name` para evitar path traversal.

### `GET /api/predictions`
```json
[
  {
    "concurso": 3682,
    "mtime": "2026-05-10T22:00:00",
    "abordagens": [
      { "abordagem": "ensemble", "dezenas": [1,3,5,...], "confianca": 0.4512 },
      { "abordagem": "ml", "dezenas": [2,4,6,...], "confianca": null }
    ]
  }
]
```
Agrupado por concurso, múltiplas abordagens por grupo.

### `GET /api/models/status`
```json
[
  {
    "name": "lstm_attention.keras",
    "group": "core",
    "size_mb": 12.3,
    "trained_at": "2026-05-10T18:00:00",
    "epochs_trained": 80,
    "val_loss_final": 0.23456,
    "config": {}
  }
]
```
Modelos de `output/models/` (group: `core`) e `src/lotofacil_lab/saved_models/` (group: `lab`).

### `POST /api/generate`
```json
// request
{ "action": "predict_all" }

// response
{ "task_id": "task_1715430000000_predict_all" }

// error
{ "error": "Unknown action: foo" }
```

### `GET /api/stream/:task_id` (SSE)
```
data: {"type": "stdout", "text": "$ lotofacil prever\n"}
data: {"type": "heartbeat"}
data: {"type": "stdout", "text": "✅ Comando concluído com sucesso."}
event: done
data: {"type": "done"}
```

---

## 8. Segurança

| Ponto | Implementação atual |
|---|---|
| Path traversal em `/api/games/:f` | `Path(filename).name` extrai apenas o basename |
| XSS em renderização de nomes | função `esc()` escapa `&`, `<`, `>`, `"` antes de injetar HTML |
| Injeção de comando | ações CLI são whitelisted em `COMMANDS` — nenhum input do usuário é passado diretamente ao subprocess |
| ANSI injection no console | `_strip_ansi()` remove sequências de escape antes de enviar ao frontend |

**Nota:** o servidor não tem autenticação. Por design, é para uso local (`0.0.0.0:5000`). Não expor em rede pública sem proxy autenticado.

---

## 9. State Management (Frontend)

```javascript
const STATE = {
  activeTab: 'coleta',          // aba selecionada na sidebar
  runningTasks: Set,            // IDs de ações em execução
  consoleLines: Array,          // histórico do console (max 150)
  games: Array,                 // lista atual de game files
  taskStartTime: {},            // actionId → Date.now() (para timer)
  timerIntervals: {},           // actionId → intervalId setInterval
};
```

`COMMANDS_DATA` é carregado uma vez na inicialização via `fetchCommands()` e reutilizado para renderização de botões sem novas requests.

---

## 10. Inicialização

`DOMContentLoaded` → `init()`:
1. `buildSidebar()` — renderiza as 9 abas na sidebar
2. `fetchCommands()` — carrega catálogo de ações e renderiza botões da aba inicial (Coleta)
3. `loadGames()` — popula a numbers-section
4. `restoreConsole()` — recupera últimas linhas do localStorage
5. `loadStatus()` — atualiza navbar
6. `setInterval(loadStatus, 30000)` — polling de status a cada 30s

---

## 11. Comportamento de Refresh Automático Pós-Tarefa

Ao concluir uma tarefa via SSE `done`, o dashboard atualiza automaticamente a seção correta:

| Aba ativa ao concluir | Ação de refresh |
|---|---|
| `jogos` | `loadGames()` |
| `geracao` | `loadGames()` |
| `predicao` | `loadGames()` |
| `predicoes` | `loadPredictions()` |
| `modelos` | `loadModels()` |
| qualquer outra | `loadGames()` |

Sempre executa também `loadStatus()` para atualizar os contadores da navbar.

---

## 12. Configuração do Servidor

| Variável de ambiente | Padrão | Descrição |
|---|---|---|
| `DASHBOARD_HOST` | `0.0.0.0` | endereço de bind |
| `DASHBOARD_PORT` | `5000` | porta HTTP |

Para iniciar: `lotofacil dashboard` (via CLI) ou diretamente `python src/dashboard/server.py`.

---

## 13. Dependências de Diretório em Runtime

| Diretório | Uso |
|---|---|
| `dados/concurso_*.json` | fonte dos sorteios históricos |
| `saida/jogos/*.json` | jogos gerados e predições |
| `output/models/*.keras` | modelos treinados (core) |
| `src/lotofacil_lab/saved_models/*.keras` | modelos treinados (lab) |
| `src/lotofacil_lab/saved_models/*.meta.json` | metadados de treinamento |

Todos os diretórios são verificados com `.exists()` antes de globbing — ausência não causa erro, apenas retorna lista vazia.

---

## 14. Limitações Conhecidas / Pontos de Melhoria

| Item | Descrição |
|---|---|
| Concorrência | Uma única tarefa por `actionId` pode rodar de cada vez. Não há limite global de tarefas paralelas. |
| Cleanup de tasks | `TASKS` dict não é purgado se o cliente desconectar antes do `done` (processo continua rodando). |
| Refresh manual | Navbar só atualiza por polling (30s) ou ao fim de tarefa. Não há WebSocket bidirecional. |
| Abas Análise e Coleta | Compartilham alguns comandos idênticos (historico, validar, status, backtest). |
| Numbers section dual-use | A mesma `#gamesGrid` serve jogos, predições e modelos — CSS e lógica mudam por aba. |
| Sem paginação | Máximo 12 game-cards renderizados; modelos sem limite de cards. |
