# Task 8.5 — Atualizar `docs/architecture.md` e `docs/PRD-dashboard.md`

**Onda:** 8 — Testes + docs
**Prioridade:** média
**Tempo estimado:** ~25 min
**Depende de:** 8.4

## Objetivo

Atualizar as duas docs de arquitetura para refletir o estado final do refactor:

- `docs/architecture.md` — substituir o diagrama da "v2.0" (que era aspiracional) pelo da arquitetura realizada (camadas + capacidades)
- `docs/PRD-dashboard.md` — atualizar seção "Arquitetura do Sistema" para refletir nova estrutura interna (endpoints permanecem idênticos)

## Arquivos envolvidos

**Modificar:**
- `docs/architecture.md`
- `docs/PRD-dashboard.md`

## Dependências

- 8.4

## Critérios de aceite

- [ ] `docs/architecture.md` descreve a arquitetura realmente em uso (não a v2.0 antiga)
- [ ] `docs/architecture.md` documenta as 4 camadas + experimentos
- [ ] `docs/PRD-dashboard.md` seção "Arquitetura" reflete `interface/painel/servidor.py`
- [ ] Endpoints documentados em PRD-dashboard ainda correspondem ao que `servidor.py` expõe

## Passos detalhados

- [ ] **Passo 1:** Reescrever `docs/architecture.md`

Conteúdo proposto:

```markdown
# Arquitetura — Lotofácil Prediction System

## Visão Geral

Sistema modular para análise estatística, ML e geração de jogos da Lotofácil. Implementa o PRD ("LotoIntelligence Analytics") em 4 camadas explícitas com regras de dependência unidirecional.

## Princípios

| Princípio | Descrição |
|---|---|
| Camadas explícitas | dominio → infra → servicos → interface (depend-on-down) |
| Single source of truth | `infra/config.py` para paths; `dominio/regras.py` para constantes |
| Domínio puro | `dominio/` sem dependências externas (numpy ok) |
| Use cases tipados | `servicos/` retornam dataclass frozen |
| Interface fina | CLI e painel chamam apenas serviços |
| Experimentos isolados | `experimentos/` consome o core; core nunca importa do lab |

## Camadas

```
┌──────────────────────────────────────────────────┐
│  Interface (CLI + Painel)                        │
│    ── parse args, chama servicos, formata saída  │
├──────────────────────────────────────────────────┤
│  Servicos (use cases — 11 funções)               │
│    ── orquestra dominio + infra                  │
├──────────────────────────────────────────────────┤
│  Infra                                           │
│    dados / atributos / modelos / estrategias /   │
│    avaliacao / geracao / agendador               │
├──────────────────────────────────────────────────┤
│  Dominio (entidades puras)                       │
│    Sorteio, Predicao, Estrategia, regras,        │
│    LotofacilError + subtipos                     │
└──────────────────────────────────────────────────┘

  Experimentos (isolado)
    Consome dominio + infra + servicos;
    core NUNCA depende disso.
```

## Regras de Dependência

| Camada | Pode importar | NÃO pode importar |
|---|---|---|
| `dominio/` | stdlib, numpy, dataclasses | qualquer outra do projeto |
| `infra/` | `dominio/` | `servicos/`, `interface/` |
| `servicos/` | `dominio/`, `infra/` | `interface/` |
| `interface/` | `dominio/`, `servicos/` | `infra/` (direto) |
| `experimentos/` | `dominio/`, `infra/`, `servicos/` | `interface/` |

## Fluxo de Dados (`lotofacil prever`)

```
Usuário
   │
   ▼ lotofacil prever --abordagem ml
[interface/cli/app.py prever]
   │
   ▼ gerar_predicao(abordagem="ml")
[servicos/gerar_predicao.py]
   │ usa infra para carregar sorteios + executar estratégia
   ▼
[infra/dados/banco.py + leitor.py]    [infra/estrategias/onze_dezenas/preditor.py]
                                            │
                                            ▼ usa infra/modelos + atributos
                                       [infra/atributos/, infra/modelos/]
                                            │
                                            ▼
                                       Predicao (dominio/entidades.py)
                                            │
   ◀────────────────────────────────────────┘
[interface/cli/app.py prever]
   │ formata saída com rich + persiste em saida/jogos/
   ▼
"Predição c3682: 01 03 05 07..."
```

## Capacidades de `infra/`

| Pacote | Conteúdo |
|---|---|
| `dados/` | API CAIXA (`ColetorAPI`), SQLite (`DatabaseManager`), JSON loader, preprocessador |
| `atributos/` | `ConstrutorAtributos` (~123 features por concurso) |
| `modelos/` | `ModeloFrequencia`, `ModeloEnsembleML`, `LSTMModel`, `PreditorEnsemble` |
| `estrategias/` | `EstrategiaOnzeDezenas` (e futuras 12, 13, 14, 15) |
| `avaliacao/` | `Backtester`, `WalkForwardValidator`, `Metricas`, `GeradorRelatorio` |
| `geracao/` | `gerar_portfolio_tiered` |
| `agendador/` | APScheduler (update Mon/Wed/Fri 23h, retrain Mon 2h) |

## Extensibilidade

### Adicionar nova estratégia (ex: 13 dezenas)

1. Criar `src/lotofacil/infra/estrategias/treze_dezenas/preditor.py`
2. Implementar `EstrategiaTrezeDezenas` (satisfaz `EstrategiaBase` Protocol)
3. Adicionar use case em `servicos/` se precisar de novo comando
4. CLI consome via serviço

### Adicionar novo modelo

1. Criar `src/lotofacil/infra/modelos/<nome>.py`
2. Herdar de `ModeloBase`
3. Adicionar ao `infra/modelos/__init__.py`
4. Adicionar caso em `servicos/treinar_modelos.py`

## Convenção de nomes

Tudo em português (módulos, classes, funções, flags). Loanwords técnicos consagrados mantidos: `backtest`, `Protocol`, `dataclass`, `LSTM`, `ensemble`, `walk-forward`, `status`.
```

- [ ] **Passo 2:** Atualizar `docs/PRD-dashboard.md` — seção 2 (Arquitetura do Sistema)

Substituir o diagrama da arquitetura para refletir nova localização e fluxo via serviços:

```markdown
## 2. Arquitetura do Sistema

```
Browser (painel.html)
       │
       ├── GET  /               → serve painel.html
       ├── GET  /api/commands   → catálogo de ações
       ├── GET  /api/status     → consultar_status_base()
       ├── GET  /api/games      → listar_jogos_gerados()
       ├── GET  /api/games/:f   → listar_jogos_gerados(filename=f)
       ├── GET  /api/predictions → listar_historico_predicoes()
       ├── GET  /api/models/status → listar_modelos_treinados()
       ├── POST /api/generate   → dispara comando CLI em background → retorna task_id
       └── GET  /api/stream/:id → SSE stream de stdout do processo

Backend (src/lotofacil/interface/painel/servidor.py + Flask)
       │
       ├── Endpoints de leitura → chamam diretamente servicos/*
       └── Endpoints de ação (POST /api/generate) → subprocess para SSE streaming

Serviços consumidos:
  lotofacil.servicos.consultar_status_base
  lotofacil.servicos.listar_jogos_gerados
  lotofacil.servicos.listar_historico_predicoes
  lotofacil.servicos.listar_modelos_treinados

CLI (lotofacil — Typer, em src/lotofacil/interface/cli/)
  Mesmos serviços que o painel — sem duplicação.
       ├── prever               → gerar_predicao()
       ├── dados atualizar      → atualizar_base()
       ├── dados status         → consultar_status_base()
       ├── modelo treinar       → treinar_modelos()
       ├── modelo backtest      → rodar_backtest()
       ├── modelo validar       → validar_predicoes()
       ├── modelo historico     → listar_historico_predicoes()
       ├── portfolio            → gerar_portfolio()
       ├── portfolio validar    → validar_portfolio()
       ├── painel               → sobe servidor Flask
       └── lab <subcmd>         → experimentos
```

Atualizar também na seção 5 (Catálogo de Ações CLI) os comandos do lab (`ablacao`, `checar-lua`, `preencher-clima`, `comparar`).

- [ ] **Passo 3:** Validar referências cruzadas

```bash
grep -rn "src/coleta\|src/geracao\|src/lotofacil_ml\|src/lotofacil_lab\|src/strategies\b\|src/data\b" docs/
# Esperado: 0 (todas as docs apontam para a nova estrutura)
```

Se houver, corrigir.

- [ ] **Passo 4:** Smoke final do refactor inteiro

```bash
# Pipeline completo de verificação:
pytest                                          # ✓
pip install -e .                                # ✓
lotofacil --version 2>/dev/null || lotofacil --help | head -5
lotofacil dados status
lotofacil prever
lotofacil portfolio --jogos 3
lotofacil modelo backtest --janela 30  # se base tiver dados
lotofacil lab ablacao --n-test 5
lotofacil painel &
PID=$!
sleep 2
curl -s localhost:5000/api/status | jq .
curl -s localhost:5000/api/games | jq . | head -10
kill $PID

# Estrutura
ls src/  # apenas src/lotofacil/
ls dados/ saida/
test ! -d data/ && test ! -d output/ && test ! -d legacy/ && test ! -d legado/ && test ! -d ml/ && echo "✅ Limpeza completa"
```

- [ ] **Passo 5:** Commit final

```bash
git add docs/architecture.md docs/PRD-dashboard.md
git commit -m "docs: alinha architecture.md e PRD-dashboard.md à arquitetura realizada

- docs/architecture.md: substituído diagrama 'v2.0' aspiracional pelo
  diagrama de 4 camadas + experimentos realizado
- docs/PRD-dashboard.md: seção 'Arquitetura do Sistema' atualizada para
  refletir uso de servicos/ pelo painel (endpoints de leitura) e CLI
  movida para interface/cli/

🎯 Refactor de consolidação estrutural completo.
   Spec: docs/superpowers/specs/2026-05-12-consolidacao-estrutural-design.md
   Plano: docs/superpowers/plans/2026-05-13-consolidacao-estrutural.md
   Tasks: tasks/ (42 tasks em 8 ondas)"
```

## Critério final do refactor

Após esta task, o refactor está oficialmente completo:

- ✅ `pytest` passa
- ✅ `pip install -e .` instala
- ✅ Todos os comandos PT funcionam
- ✅ Painel sobe e endpoints respondem
- ✅ Lab opera com core consolidado
- ✅ Sem pastas duplicadas (`data/`, `output/`, `legacy/`, `legado/`, `ml/`, `src/main.py`, `src/sugestao/`, sub-árvore órfã v2.0)
- ✅ Convenção PT total
- ✅ 4 camadas explícitas com regras de dependência
- ✅ Docs alinhadas

Próximo ciclo: implementar os gaps do PRD (rastreio de experimentos, ranking, comparação justa, explicabilidade) **em cima** desta fundação.
