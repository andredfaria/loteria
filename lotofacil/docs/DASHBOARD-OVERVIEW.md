# Lotofácil Dashboard — Overview Completo

**Versão:** 2026-05-29  
**Stack:** Python 3.12 + Flask · HTML/CSS/JS vanilla · SQLite · Canvas 2D  
**Acesso:** `http://localhost:5000` (uso local)  
**Tamanho atual:** ~3.571 linhas de HTML/JS · 1.350 linhas de Python (server.py)

---

## 1. Visão Geral

O dashboard é a **interface centralizada** do sistema de análise e predição da Lotofácil. Elimina o uso direto do terminal e expõe todas as capacidades do sistema via browser: coleta de dados, treinamento de modelos, geração de apostas, análise estatística e experimentos.

```
Browser (dashboard.html — single-page app)
       │
       ├── REST API  →  server.py (Flask)
       ├── Polling   →  /api/jobs/<id>/poll  (output em tempo real)
       └── Subprocess  →  CLI lotofacil + processos Python diretos
```

**Sem frameworks JS.** Todo o frontend é HTML + CSS + JavaScript vanilla com canvas 2D para gráficos.

---

## 2. Arquitetura Frontend

### Estado Global

```javascript
const STATE = {
  activeTab: 'coleta',      // aba ativa na sidebar
  runningTasks: Set,        // IDs de ações em execução
  consoleLines: Array,      // histórico do console (max 150)
  taskStartTime: {},        // actionId → timestamp
  timerIntervals: {},       // actionId → intervalId
  dadosPage: 1,             // página atual do histórico
  validacaoLastN: 120,      // janela de validação
}
```

### Layout

```
┌──────────────────────────────────────────────────────────┐
│ NAVBAR: concurso pinado (hot/warm/cold) │ stats │ online  │
├─────────┬────────────────────────────────────────────────┤
│         │  ACTIONS BAR (título + controles da aba)        │
│ SIDEBAR ├────────────────────────────────────────────────┤
│         │  CONTENT AREA (numbers, dados, modelos, etc.)   │
│ 📥      │                                                  │
│ 🗃️      ├────────────────────────────────────────────────┤
│ ✅      │  CONSOLE (output em tempo real)                  │
│ 🧠      │                                                  │
│ 🧪      │                                                  │
├─────────┴────────────────────────────────────────────────┤
│ BOTTOM NAV (mobile)                                       │
└──────────────────────────────────────────────────────────┘
```

### Fluxo de execução de comando CLI

```
[Clique no botão]
  → marca runningTasks · desabilita botão · inicia timer mm:ss
  → POST /api/generate { action }
  → recebe { task_id }
  → pollJob(task_id) — GET /api/jobs/<id>/poll a cada 500ms
  → linhas de stdout vão para o console em tempo real
  → ao finalizar: toast · refresh automático da seção relevante
```

---

## 3. Features Globais

### 3.1 Navbar — Concurso Pinado com Hot/Warm/Cold

O último sorteio aparece fixo na navbar com coloração por frequência histórica:

| Classe | Critério |
|--------|----------|
| `hot` (azul vivo) | Número sorteado ≥ 90% da frequência máxima |
| `warm` (médio) | Entre cold e hot |
| `cold` (opaco) | Número sorteado ≤ 10% acima do mínimo |

A mesma coloração se propaga para **todas as bolas em todas as abas** do dashboard — predições, jogos gerados, histórico e dados. A frequência base é carregada via `/api/dados/frequencia` na inicialização.

**Métricas da navbar** (polling a cada 30s via `/api/status`):
- Número do último concurso + data
- Total de sorteios na base
- Contagem de jogos gerados
- Indicador online (verde)

### 3.2 Console

Terminal embutido com coloração semântica:

| Cor | Trigger |
|-----|---------|
| `cmd` (cinza) | Linhas começando com `$` |
| `success` (verde) | ✅ / "sucesso" / "concluído" |
| `error` (vermelho) | ❌ / "erro" / `Traceback` |
| `warn` (amarelo) | ⚠ |
| `dim` | Mensagens de sistema |

**Features do console:**
- Filtro por nível (info / success / warn / error / cmd)
- Toggle autoscroll
- Export JSON ou TXT (download direto)
- Botão limpar (apaga localStorage)
- Persistência: últimas 150 linhas em `localStorage` → restauradas na próxima sessão com separador "— sessão anterior —"

### 3.3 Atalhos de Teclado

Modal `?` com mapa completo:

| Tecla | Ação |
|-------|------|
| `C` | Ir para Coleta |
| `D` | Ir para Dados |
| `M` | Ir para Modelos |
| `V` | Ir para Validação |
| `1–5` (em Modelos) | Sub-abas Treinar / Lista / Gerar / Comparar / Histórico |

### 3.4 Toast Notifications

Notificações temporárias (3s) no canto inferior direito com bordas coloridas por tipo: sucesso (verde), erro (vermelho), info (azul).

---

## 4. Abas do Dashboard

### 4.1 📥 Coleta

**Propósito:** monitorar e disparar a coleta de dados da API Caixa.

**Features:**
- Painel de status da base (total sorteios, último concurso, dezenas com hot/warm/cold)
- Botões de ação CLI:
  - **Atualizar Base** — `lotofacil dados atualizar`
  - **Importar Tudo** — `lotofacil dados atualizar --all`
  - **Buscar Último** — `lotofacil dados atualizar --latest`
  - **Status do DB** — `lotofacil dados status`

---

### 4.2 🗃️ Dados

**Propósito:** explorar o histórico completo de sorteios com análise de frequência.

**Features:**

#### Gráfico de Frequência Histórica (1–25)
- Barra por número (1–25) mostrando frequência absoluta nos sorteios
- Indicadores: esperado, máximo, mínimo
- **Click-to-filter:** clicar em uma barra filtra a tabela para sorteios que contêm aquele número
- Coloração hot/warm/cold nas barras

#### Tabela de Sorteios
- Paginação configurável (padrão 25 por página)
- Colunas: concurso, data, dezenas (bolas coloridas), fase lunar, clima
- **Busca por texto** (número do concurso, data)
- **Filtros** por clima (com/sem) e fase lunar
- **Jump-to-concurso:** campo numérico para ir direto a um concurso específico

#### Export
- **Export CSV** — download de todos os sorteios da base atual via `/api/dados/export-csv`

#### Stats
- Chips de contagem: total sorteios, registros com clima, registros com lua

---

### 4.3 ✅ Validação

**Propósito:** avaliar a qualidade das predições do ensemble em tempo real.

**Features:**

#### Saúde do Modelo
- **Sparkline** dos últimos 20 concursos (barras de hit rate)
- Médias móveis 20/50 concursos
- Taxa de acerto ≥11 para janelas de 20 e 50
- **Detector de drift:** alerta se houver N concursos consecutivos em queda

#### Qualidade por Abordagem
- Card por abordagem com: média de hits ±std, comparação % vs baseline, p-value estatístico, amostra (n)
- Barras de distribuição de hits (11/12/13/14/15) por abordagem
- Classificação automática (nível: bom / atenção / ruim)
- Ordenação por média de hits (desc)

#### Leaderboard
- Tabela de todas as abordagens
- **Colunas sortáveis** (clique no header): hits médios, p-value, std
- Indicador de direção (▲▼) na coluna ativa

#### Alertas
- Alertas configuráveis com dismiss individual
- Botão "Limpar todos os dismissals"
- **Controle de janela:** campo "Últimos N sorteios" com botão recalcular

---

### 4.4 🧠 Modelos

**Propósito:** ciclo completo de treino → lista → geração → comparação → histórico.

A aba tem **5 sub-abas** com navegação horizontal:

```
▶ Treinar  |  📋 Lista  |  ⚡ Gerar  |  ⚖️ Comparar  |  🕐 Histórico
```

#### Sub-aba ▶ Treinar

Formulário de configuração de treino:

**1. Tipo de configuração** (cards visuais):
| Config | Features |
|--------|---------|
| `base` 📊 | Histórico + temporal + priors |
| `+ Lua` 🌙 | base + fase lunar |
| `+ Clima` 🌤️ | base + clima SP |
| `+ Lua+Clima` 🔭 | base + lua + clima |

**2. Identificação:** campo de nome livre para o treino (ex: `lua_100ep_v2`)

**3. Hiperparâmetros:** épocas, learning rate, seed, etc.

- Modal de progresso em tempo real com barra de progresso e ETA
- Notificação em background se o treino terminar enquanto estiver em outra aba

#### Sub-aba 📋 Lista

- Cards de modelos com: nome, tipo de config, status (running/completed/failed), val_loss final, épocas, data de criação
- **Expand por modelo:** detalha hiperparâmetros, métricas e distribuição de hits do backtest
- **Backtest embutido:** qualidade por abordagem com barras de distribuição
  - Controle de janela (último N sorteios)
  - Botão recalcular
- **🏆 Melhor Modelo:** seleciona automaticamente o modelo com mais hits médios no backtest
- **Renomear modelo** (PATCH inline)
- **Bulk-delete de modelos failed**
- Indicador "Última atualização"

#### Sub-aba ⚡ Gerar

Geração de apostas a partir de um modelo treinado:

| Campo | Opções |
|-------|--------|
| Modelo treinado | dropdown de modelos completed |
| Nº de jogos | 1–20 |
| Números por jogo | 11 / 12 / 13 / 14 / 15 |
| Concurso alvo | próximo (padrão) ou qualquer número |

- Botão **🏆 Melhor Modelo** (auto-seleciona se backtest disponível)
- Aviso de caráter experimental
- **Comparação com sorteio real:** se o concurso alvo já aconteceu, exibe dezenas reais e acertos por jogo
- **Jogos Recentes:** lista dos últimos jogos gerados para aquele modelo

#### Sub-aba ⚖️ Comparar

Comparação direta entre dois modelos treinados:

- Seleção de Modelo A e Modelo B
- Métricas comparadas: val_loss, hits médios, melhoria % vs baseline, p-value
- Delta de val_loss com indicador ▼ (melhor) / ▲ (pior)
- Cópia de configuração para clipboard

#### Sub-aba 🕐 Histórico

Registro persistente de todos os jogos gerados:

**Stats no topo:**
- Total de gerações e jogos
- Média de acertos (com resultado real disponível)
- Melhor resultado (N/15)
- Jogos premiados (≥11 acertos)

**Filtros:**
- Por modelo (dropdown)
- Toggle "Só premiados" (mostra apenas gerações com ≥11 acertos)

**Por geração:**
- Nome do modelo, concurso alvo, data, nº de jogos
- Bolas coloridas de cada jogo
- Acertos por jogo vs sorteio real (badge verde quando premiado)
- Dezenas reais do sorteio (quando disponível)

**Export:**
- **Export CSV** com todas as gerações filtradas (nome, concurso, jogos, acertos)

---

### 4.5 🧪 ROI Lab

**Propósito:** descoberta experimental de estratégias estatísticas que perdem menos que o aleatório.

> **Meta:** não é possível ROI positivo puro (house edge ~35%). O objetivo é encontrar combinações de filtros que historicamente produzem distribuições de acertos melhores que jogos 100% aleatórios.

#### Configurar Estratégia

Filtros estatísticos com checkbox de ativação e range [min, max]:

| Filtro | Range padrão | Cobertura histórica |
|--------|-------------|---------------------|
| Soma das dezenas | [171, 220] | ~84% dos sorteios |
| Pares | [6, 9] | ~90% |
| Primos | [4, 7] | ~70% |
| Fibonacci | [3, 5] | ~65% |
| Moldura (borda do volante) | [8, 11] | ~55% |
| Repetições (concurso ant.) | [8, 10] | ~70% |
| Consecutivos mín. | 2 | ~80% |

**Parâmetros de simulação:**
- Jogos por sorteio (1–20, padrão 5)
- Janela histórica: Todos / Últimos 500 / 1000 / 2000 sorteios

**Botão ▶ Rodar Backtest:** desativa durante execução com spinner "⏳ Calculando…"

#### Resultado

Quatro cards comparativos (estratégia vs baseline aleatório):

| Card | Cor |
|------|-----|
| ROI% | Verde se melhor que baseline, vermelho se pior |
| Sharpe ratio | Verde se melhor |
| Drawdown máximo | Verde se menor |
| Hit rate ≥13 | Verde se maior |

**Equity curve (canvas 2D):**
- Linha sólida azul (#4fc3f7) = estratégia
- Linha tracejada cinza = baseline aleatório
- Linha zero pontilhada de referência
- Legenda embutida

**Tabela de distribuição de acertos:** 11/12/13/14/15 — estratégia vs baseline

**Resumo:** total de jogos simulados, custo, receita, lucro/prejuízo líquido

#### Salvar e Comparar Estratégias

- Campo de nome + botão 💾 salva a configuração atual com resultados em `saida/roi_strategies.json`
- Tabela de estratégias salvas com: ROI%, Sharpe, Hit≥13, Drawdown
- Botão 🗑 por linha para deletar
- Persiste entre sessões

---

## 5. API REST — Catálogo Completo

### Core

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Serve `dashboard.html` |
| GET | `/api/status` | Métricas navbar (último concurso, total, jogos) |
| GET | `/api/commands` | Catálogo de ações CLI disponíveis |
| POST | `/api/generate` | Dispara comando CLI em background → `{task_id}` |
| GET | `/api/jobs/<id>/poll?offset=N` | Polling de stdout da task (linhas desde offset N) |
| POST | `/api/jobs/<id>/cancel` | Cancela task em execução |

### Dados Históricos

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/dados?page&per_page` | Sorteios paginados com clima/lua |
| GET | `/api/dados/frequencia` | Frequência histórica de cada número (1–25) |
| GET | `/api/dados/export-csv` | Download CSV completo |
| GET | `/api/dados/page-for-concurso?concurso=N` | Número de página para um concurso |

### Jogos e Predições

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/games` | Lista de arquivos de jogos (20 mais recentes) |
| GET | `/api/games/previews` | Previews de bolas por arquivo |
| GET | `/api/games/<filename>` | Conteúdo JSON de um arquivo de jogo |
| GET | `/api/predictions` | Predições agrupadas por concurso |

### Modelos (legacy / ensemble)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/models/status` | Inventário de modelos .keras |
| GET | `/api/models/quality?last_n=N` | Qualidade/backtest por abordagem |
| GET | `/api/models/trend` | Sparkline e métricas de drift |
| GET | `/api/leaderboard` | Ranking de modelos por hits |
| GET | `/api/compare?a=&b=` | Comparação entre dois modelos |
| GET | `/api/alerts` | Alertas ativos do sistema |
| GET | `/api/alerts/history` | Histórico de alertas |

### Treinos (ciclo ML gerenciado)

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/treinos/iniciar` | Inicia treino com configuração e hiperparâmetros |
| GET | `/api/treinos` | Lista todos os treinos com status |
| GET | `/api/treinos/<id>` | Detalhes de um treino |
| PATCH | `/api/treinos/<id>` | Renomear treino |
| DELETE | `/api/treinos/<id>` | Deletar treino |
| GET | `/api/treinos/comparar?a=&b=` | Comparação de métricas entre dois treinos |
| POST | `/api/treinos/<id>/gerar` | Gerar jogos a partir de um modelo treinado |
| GET | `/api/jogos-gerados` | Histórico de todos os jogos gerados |

### ROI Lab

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/roi/backtest` | Roda backtest com filtros → `{estrategia, baseline}` |
| GET | `/api/roi/strategies` | Lista estratégias salvas |
| POST | `/api/roi/strategies` | Salva/atualiza estratégia nomeada |
| DELETE | `/api/roi/strategies/<nome>` | Remove estratégia |

---

## 6. Serviços Backend

### `roi_lab.py` (`src/lotofacil/servicos/roi_lab.py`)

Novo serviço puro (sem I/O de rede, sem Flask):

```python
rodar_backtest_roi(filtros, n_jogos_por_sorteio=5, janela=None)
  → {"estrategia": FinancialResult, "baseline": FinancialResult}
```

- Filtros: soma, pares, primos, fibonacci, moldura, repeticoes, consecutivos
- Geração por rejeição: 200 tentativas por jogo — None se impossível
- Usa `FinancialSimulator` existente (roi_pct, equity_curve, sharpe, drawdown)
- Constantes importadas de `dominio.regras` (MOLDURA, PRIMOS, FIBONACCI)
- Baseline usa `random.Random(42)` independente da estratégia

### `FinancialSimulator` (`src/lotofacil/infra/avaliacao/financeiro.py`)

Motor financeiro pré-existente:

```
FinancialResult:
  n_games, total_cost, total_revenue, net_profit, roi_pct
  max_drawdown, sharpe, equity_curve, hits_distribution, rate_ge
```

Tabela de prêmios usada: R$3,50/jogo · 11pts→R$7 · 12pts→R$14 · 13pts→R$35 · 14pts→R$2.000 · 15pts→R$1.500.000

---

## 7. Segurança

| Ponto | Implementação |
|-------|--------------|
| Path traversal | `Path(filename).name` em todas as rotas de arquivo |
| XSS | Função `esc()` em todos os `innerHTML` com dados do servidor |
| Injeção de comando | Ações CLI whitelisted em `COMMANDS` — nenhum input chega ao subprocess |
| ANSI injection | `_strip_ansi()` antes de enviar ao frontend |
| Estratégias (DELETE) | Nome usado apenas como comparador de string, não em filesystem ou SQL |

**Sem autenticação** — uso local exclusivo. Não expor em rede pública.

---

## 8. Estado do Desenvolvimento

### Implementado e em produção

| Feature | Status |
|---------|--------|
| Coleta de dados (CLI) | ✅ |
| Histórico paginado + busca | ✅ |
| Gráfico de frequência histórica | ✅ |
| Hot/warm/cold balls (global) | ✅ |
| Concurso pinado na navbar | ✅ |
| Validação com sparkline + leaderboard | ✅ |
| Alertas de drift | ✅ |
| Treino configurável (4 configs) | ✅ |
| Lista de modelos com backtest | ✅ |
| Geração de jogos (ML) | ✅ |
| Comparação A vs B | ✅ |
| Histórico de jogos gerados | ✅ |
| Comparação com sorteio real | ✅ |
| Export CSV (dados + histórico) | ✅ |
| Atalhos de teclado | ✅ |
| Console com persistência | ✅ |
| ROI Lab (filtros + backtest + equitycurve) | ✅ |
| Salvar/comparar estratégias ROI | ✅ |

### Limitações conhecidas

| Item | Descrição |
|------|-----------|
| Sem auth | Uso local. Não expor em rede pública. |
| Cleanup de tasks | `TASKS` dict não purgado se cliente desconectar antes do `done` |
| Polling vs SSE | Polling a 500ms em vez de Server-Sent Events — funcional mas não ideal |
| ROI positivo impossível | Dashboard deixa explícito: meta é eficiência relativa, não lucro |
| Backtest ROI não walk-forward | Janela estática, não previne data leakage entre filtros e resultado |

---

## 9. Como Iniciar

```bash
cd lotofacil
source venv/bin/activate

# Via CLI (recomendado)
lotofacil dashboard

# Ou direto
python -m lotofacil.interface.painel.server

# Acesse
open http://localhost:5000
```

**Variáveis de ambiente:**
- `DASHBOARD_HOST` (padrão: `0.0.0.0`)
- `DASHBOARD_PORT` (padrão: `5000`)
