# Spec — Consolidação estrutural do lotofacil/

**Data:** 2026-05-12
**Tipo:** Design (refactor estrutural, sem novas funcionalidades)
**Status:** Em revisão pelo usuário
**Origem:** Brainstorming a partir de `PRD.md` (LotoIntelligence Analytics) + `docs/PRD-dashboard.md`

---

## 1. Objetivo

Transformar o estado atual do `lotofacil/` em uma implementação aderente ao PRD, **reutilizando o que existe** e **sem alterar funcionalidades**. O foco é:

- Eliminar duplicações (4 implementações de features, 3 de modelos, 2 de fetcher/loader/database, 2 cemitérios de código legacy, 2 raízes de inputs, 2 raízes de outputs).
- Adotar separação clara entre domínio, serviços, infraestrutura e interface.
- Padronizar nomes em português em todo o código (módulos, classes, flags).
- Estabelecer regras de dependência entre camadas para que a próxima divergência seja prevenida estruturalmente.

**Fora do escopo:** novos requisitos do PRD (rastreio de experimentos, ranking, comparação justa, explicabilidade). Estes ficam para um próximo ciclo, construído **em cima** desta fundação.

## 2. Estado atual e dívida diagnosticada

### 2.1 Pipelines paralelos fazendo a mesma coisa

| Capacidade | Implementações encontradas |
|---|---|
| Feature engineering | `src/features/`, `src/lotofacil_ml/features/`, `src/lotofacil_lab/features/`, `ml/features.py` |
| Modelos ML | `src/models/`, `src/lotofacil_ml/models/`, `src/lotofacil_lab/models/` |
| Avaliação | `src/evaluation/`, `src/lotofacil_ml/evaluation/`, `src/lotofacil_ml/backtest/`, `src/lotofacil_lab/evaluation/` |
| Coleta API CAIXA | `src/data/fetcher.py`, `src/lotofacil_ml/data/fetcher.py`, `legacy/coleta/` |
| Banco SQLite | `src/data/database.py`, `src/lotofacil_ml/data/database.py` |
| Loader de sorteios | `src/data/loader.py`, `src/lotofacil_ml/data/loader.py` |

### 2.2 Camadas órfãs

`src/main.py` é um segundo entry point **não registrado** em `pyproject.toml` (`[project.scripts]` aponta só para `src/cli/app.py`). Ele consome `src/core/`, `src/data/`, `src/evaluation/`, `src/models/`, `src/features/` — toda uma sub-árvore que foi tentativa de refactor "v2.0" (descrita em `docs/architecture.md`) e ficou abandonada quando o esforço migrou para `src/lotofacil_ml/`. Hoje **só `src/main.py` usa esses módulos**.

Exceção: `src/cli/app.py prever` ainda importa `src/data/loader.py` e `src/strategies/eleven_numbers/`. Essa é a **inconsistência viva**: `lotofacil prever` usa a árvore órfã enquanto `lotofacil modelo treinar` usa `lotofacil_ml/*`.

### 2.3 Arquivos arquivados

- `legacy/` (8 subpastas) — README confirma que está superado por `src/cli/` e `src/strategies/`. Nenhum import vivo aponta pra ele.
- `legado/` — só docs antigos (`Hierarquia de Estratégias...md`, `Relatório Técnico...md`, `100-cada-RELATORIO...md`, `curl.md`).
- `ml/` — pipeline de scripts standalone (`features.py` → `dataset.py` → `treino.py` → `backtest.py` → `inferencia.py`). Sem nenhum import vindo de `src/` ou `scripts/`.
- `src/sugestao/` — vazio (só `__init__.py` e cache de testes).

### 2.4 Pastas físicas duplicadas

- `data/` (interno, EN) ↔ `dados/` (symlink para `~/lotofacil-dados/`, PT)
- `output/` (EN) ↔ `saida/` (PT)
- `src/lotofacil.db` ↔ `data/lotofacil.db` (dois SQLites para o mesmo banco)
- `src/models_saved/` ↔ `output/models/` ↔ `src/lotofacil_lab/saved_models/` (três locais para modelos treinados)
- Tests espalhados: raiz `tests/`, `src/lotofacil_ml/tests/`, `src/lotofacil_lab/tests/`, `src/dashboard/tests/`

### 2.5 Mistura PT/EN sem convenção

Comandos CLI: `lotofacil dados` (PT) e `lotofacil prever --approach all` (mistura). Módulos: `core/`, `data/`, `evaluation/`, `features/`, `models/`, `strategies/` (EN) ao lado de `sugestao/` (PT). Pastas: tudo misturado.

## 3. Decisões consolidadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| PRD alvo | `PRD.md` primeiro, depois `docs/PRD-dashboard.md` | Plataforma analítica é a fundação; dashboard é uma das interfaces |
| Foco do ciclo | Consolidação estrutural (sem novos features) | Reduzir dívida antes de construir gaps do PRD |
| Escopo | Todo o código aberto a movimentação | Nada intocado; toda a árvore consolidada |
| Convenção de nomes | Tudo em português (módulos, classes, flags) | Coerência total com público-alvo |
| Arquitetura | Camadas + capacidades (opção C) | Honra brief de 4 camadas explícitas mantendo granularidade |
| Compatibilidade CLI | Corte limpo (sem shim de deprecation) | Projeto de uso pessoal; menos código de cola |

## 4. Arquitetura final

### 4.1 Layout de pastas

```
lotofacil/
├── pyproject.toml
├── README.md
├── CLAUDE.md
├── AGENTS.md
├── PRD.md
├── conftest.py
├── docs/
│   ├── architecture.md
│   ├── PRD-dashboard.md
│   ├── superpowers/{specs,plans}/
│   └── …
├── dados/                          # symlink → ~/lotofacil-dados/ (preservado)
│   ├── concursos/                  # JSONs da API CAIXA
│   ├── processado/                 # CSVs/Parquets derivados
│   └── lotofacil.db                # SQLite único
├── saida/
│   ├── jogos/                      # portfolios + jogos formato apostável
│   ├── predicoes/                  # JSON com confianças
│   ├── modelos/                    # .keras, .joblib treinados
│   ├── relatorios/                 # backtests, HTML, KPI
│   ├── experimentos/               # outputs do lab
│   └── logs/                       # logs runtime
├── tasks/                          # plano de execução (writing-plans gera)
├── testes/
│   ├── unidade/{dominio,infra,servicos}/
│   └── integracao/{cli,painel}/
└── src/lotofacil/
    ├── __init__.py
    ├── dominio/
    │   ├── entidades.py            # Sorteio, Predicao, Portfolio
    │   ├── regras.py               # constantes (1–25, 15 dezenas, payouts)
    │   ├── estrategia.py           # Protocol/ABC EstrategiaBase
    │   └── excecoes.py             # LotofacilError + subtipos
    ├── servicos/
    │   ├── atualizar_base.py
    │   ├── consultar_status_base.py
    │   ├── treinar_modelos.py
    │   ├── gerar_predicao.py
    │   ├── rodar_backtest.py
    │   ├── validar_predicoes.py
    │   ├── listar_historico_predicoes.py
    │   ├── gerar_portfolio.py
    │   ├── validar_portfolio.py
    │   ├── listar_jogos_gerados.py
    │   └── listar_modelos_treinados.py
    ├── infra/
    │   ├── config.py               # paths globais consolidados
    │   ├── dados/                  # API CAIXA, SQLite, JSON loader, preprocessor
    │   ├── atributos/              # feature engineering canonical
    │   ├── modelos/                # Frequencia, Ensemble, Neural
    │   ├── estrategias/
    │   │   ├── onze_dezenas/
    │   │   ├── doze_dezenas/
    │   │   ├── treze_dezenas/
    │   │   ├── quatorze_dezenas/
    │   │   └── quinze_dezenas/
    │   ├── avaliacao/              # backtest, métricas, comparação, walk-forward, relatório
    │   ├── geracao/                # portfólio, fechamentos
    │   └── agendador/              # APScheduler
    ├── interface/
    │   ├── cli/                    # Typer app (dados, modelo, prever, portfolio, lab, painel)
    │   └── painel/                 # Flask + SSE + static/
    └── experimentos/               # lab isolado
        ├── coleta/                 # backfill clima
        ├── dados/                  # loaders específicos (clima, lua)
        ├── atributos/              # blocos modulares
        ├── modelos/                # baseline, neural modular
        ├── avaliacao/              # walkforward, metrics
        ├── uso/                    # use cases do lab
        └── …
```

### 4.2 Regras de camadas (dependency rules)

| Camada | Pode importar de | NÃO pode importar de | Conteúdo |
|---|---|---|---|
| `dominio/` | stdlib, numpy, dataclasses | qualquer outra camada do projeto | Entidades, Protocols, regras estatísticas puras, exceções |
| `infra/` | `dominio/` | `servicos/`, `interface/` | Implementações de IO, banco, ML, geração |
| `servicos/` | `dominio/`, `infra/` | `interface/` | Use cases — funções tipadas com resultado em dataclass |
| `interface/` | `dominio/`, `servicos/` | `infra/` (apenas via serviço) | CLI + painel — parse de args, chamada de serviço, formatação |
| `experimentos/` | `dominio/`, `infra/`, `servicos/` | `interface/` | Lab isolado; core nunca importa de cá |

Consequências:
- CLI e painel chamam os **mesmos** serviços → fim da duplicação de orquestração.
- Testes de `dominio/` rodam sem mocks.
- `experimentos/` consome o core mas nunca acopla o core a si.

### 4.3 Padrão de serviço (use case)

Cada serviço é uma **função pública** retornando **dataclass frozen**:

```python
# src/lotofacil/servicos/atualizar_base.py
from dataclasses import dataclass
from typing import Literal
from lotofacil.dominio.entidades import Sorteio
from lotofacil.infra.dados import api_caixa, banco

@dataclass(frozen=True)
class ResultadoAtualizacao:
    total_novos: int
    ultimo_concurso: int
    sorteios_adicionados: list[Sorteio]

def atualizar_base(escopo: Literal["todos", "novos", "ultimo"] = "novos") -> ResultadoAtualizacao:
    """Sincroniza a base local com a API CAIXA."""
    ...
```

CLI consome (thin wrapper):

```python
# src/lotofacil/interface/cli/dados.py
from lotofacil.servicos.atualizar_base import atualizar_base

@app.command()
def atualizar(escopo: str = typer.Option("novos", "--escopo")):
    resultado = atualizar_base(escopo=escopo)
    console.print(f"✅ {resultado.total_novos} novos. Último: {resultado.ultimo_concurso}")
```

Painel consome o mesmo serviço — sem reimplementação.

### 4.4 Padrão de exceções

`dominio/excecoes.py` define a árvore:

```python
class LotofacilError(Exception): ...
class SorteioNaoEncontrado(LotofacilError): ...
class ModeloNaoTreinado(LotofacilError): ...
class BaseDesatualizada(LotofacilError): ...
class EstrategiaInvalida(LotofacilError): ...
```

A CLI (no entry point) captura `LotofacilError` no topo e formata; exceções inesperadas propagam com stack trace para facilitar debug em ambiente pessoal.

## 5. CLI consolidada (PT)

### 5.1 Comandos finais

| Comando | Notas |
|---|---|
| `lotofacil dados atualizar [--escopo novos\|todos\|ultimo]` | substitui `--latest`, `--all` |
| `lotofacil dados status` | mantém `status` (loanword consagrado) |
| `lotofacil modelo treinar` | sem mudança |
| `lotofacil modelo backtest` | mantém `backtest` (termo técnico) |
| `lotofacil modelo historico` | sem mudança |
| `lotofacil modelo validar` | sem mudança |
| `lotofacil prever [--abordagem todas\|ml\|neural\|statistical] [--concurso N]` | flag PT |
| `lotofacil portfolio [--jogos N] [--concurso N]` | sem mudança |
| `lotofacil portfolio validar N` | sem mudança |
| `lotofacil lab ablacao` | era `ablation` |
| `lotofacil lab checar-lua --data YYYY-MM-DD` | era `lunar-check` |
| `lotofacil lab preencher-clima` | era `backfill-clima` |
| `lotofacil lab comparar` | era `compare` |
| `lotofacil lab treinar` | sem mudança |
| `lotofacil painel` | era `dashboard` |

### 5.2 Entry point

```toml
# pyproject.toml
[project.scripts]
lotofacil = "lotofacil.interface.cli.app:app"

[tool.setuptools.packages.find]
where = ["src"]
include = ["lotofacil*"]
```

Imports passam a usar nome qualificado completo: `from lotofacil.servicos.atualizar_base import atualizar_base`. Sem `sys.path.insert` em código de produção.

## 6. Mapeamento código atual → novo

### 6.1 Deleções (sem migração)

| Caminho atual | Razão |
|---|---|
| `legacy/` (8 subpastas) | README admite superado; 0 imports vivos |
| `legado/` | só docs antigos — preservar 1-2 relevantes em `docs/` antes |
| `ml/` (pipeline scripts) | substituído por `src/lotofacil_ml/*`; 0 imports |
| `src/main.py` | entry point órfão, não registrado em `pyproject.toml` |
| `src/core/`, `src/data/`, `src/features/`, `src/models/`, `src/evaluation/` | camada órfã v2.0; só `src/main.py` usa |
| `src/sugestao/` | vazio |
| `src/lotofacil.db` | duplicata de `data/lotofacil.db` |
| `src/models_saved/` | duplicata de `output/models/` |
| `lotofacil_prediction.egg-info/` | build artifact |
| `portfolio_*.txt`, `portfolio_*.json` na raiz | outputs vazados; mover histórico relevante para `saida/jogos/` |

### 6.2 Escolhas canônicas (onde há duplicação real)

Em cada par, vence o módulo mais completo e mais usado:

| Função | Vencedor | Destino |
|---|---|---|
| API CAIXA fetcher | `src/lotofacil_ml/data/fetcher.py` | `infra/dados/api_caixa.py` |
| SQLite manager | `src/lotofacil_ml/data/database.py` | `infra/dados/banco.py` |
| Loader de sorteios | `src/lotofacil_ml/data/loader.py` | `infra/dados/leitor.py` |
| Pré-processamento | `src/data/preprocessor.py` (única) | `infra/dados/preprocessador.py` |
| Feature engineering | `src/lotofacil_ml/features/` | `infra/atributos/` |
| Modelos base | `src/lotofacil_ml/models/` | `infra/modelos/` |
| Backtest engine | `src/lotofacil_ml/backtest/engine.py` | `infra/avaliacao/backtest.py` |
| Métricas | `src/lotofacil_ml/evaluation/metrics.py` | `infra/avaliacao/metricas.py` |
| Walk-forward validator | `src/lotofacil_ml/evaluation/walk_forward.py` | `infra/avaliacao/walk_forward.py` |
| Strategy abstraction | `src/strategies/base.py` | `dominio/estrategia.py` (vira Protocol) |
| Geração de portfólio | Extrair de `src/cli/portfolio.py` | `infra/geracao/portfolio.py` + serviço |
| Comparação de abordagens | `src/evaluation/comparison.py` | `infra/avaliacao/comparacao.py` |
| Scheduler | `src/lotofacil_ml/scheduler/` | `infra/agendador/` |
| Report HTML | `src/lotofacil_ml/report/` | `infra/avaliacao/relatorio.py` |

### 6.3 Movimentações puras

| Atual | Novo |
|---|---|
| `src/strategies/eleven_numbers/` | `infra/estrategias/onze_dezenas/` |
| `src/strategies/quinze_numbers/` | `infra/estrategias/quinze_dezenas/` |
| `src/strategies/future/twelve_numbers/` | `infra/estrategias/doze_dezenas/` |
| `src/strategies/future/thirteen_numbers/` | `infra/estrategias/treze_dezenas/` |
| `src/strategies/future/fourteen_numbers/` | `infra/estrategias/quatorze_dezenas/` |
| `src/cli/{app,dados,modelo,portfolio,lab}.py` | `interface/cli/*.py` |
| `src/dashboard/server.py` + `static/` | `interface/painel/servidor.py` + `static/` |
| `src/core/models.py` (`Draw`, `Prediction`) | `dominio/entidades.py` (`Sorteio`, `Predicao`) |
| `src/core/config.py` + `src/core/lottery.py` | `dominio/regras.py` |
| `src/lotofacil_ml/config.py` (paths) | `infra/config.py` |
| `src/lotofacil_lab/` (todo) | `experimentos/` |
| `tests/`, `src/lotofacil_ml/tests/`, `src/lotofacil_lab/tests/`, `src/dashboard/tests/` | `testes/{unidade,integracao}/` |

### 6.4 Pastas físicas

| Atual | Novo | Operação |
|---|---|---|
| `data/raw/concursos/*.json` | `dados/concursos/` | mover |
| `data/processed/` | `dados/processado/` | mover |
| `data/lotofacil.db` | `dados/lotofacil.db` | mover |
| `output/models/*.keras` | `saida/modelos/` | mover |
| `output/predictions/` | `saida/predicoes/` | mover |
| `output/reports/` | `saida/relatorios/` | mover |
| `src/models_saved/` | `saida/modelos/` (consolidar) | mover + remover pasta |
| `src/lotofacil_lab/saved_models/` | `saida/experimentos/modelos/` | mover |
| `src/lotofacil_lab/output/` | `saida/experimentos/` | mover |
| `saida/jogos/` | `saida/jogos/` | mantém |
| `saida/jogos_otimizados/` | `saida/jogos/` (com sufixo `_otimizado`) | consolidar |
| `saida/sugestao/` | `saida/jogos/` se tiver conteúdo; senão deletar | inspecionar antes |
| `logs/` | `saida/logs/` | mover |
| symlink `dados/` → `~/lotofacil-dados/` | preservado | — |

Único local de paths em `infra/config.py`:

```python
PROJETO_RAIZ = Path(__file__).resolve().parent.parent.parent.parent
DADOS_DIR = PROJETO_RAIZ / "dados"
SAIDA_DIR = PROJETO_RAIZ / "saida"
DB_PATH = DADOS_DIR / "lotofacil.db"
MODELOS_DIR = SAIDA_DIR / "modelos"
JOGOS_DIR = SAIDA_DIR / "jogos"
PREDICOES_DIR = SAIDA_DIR / "predicoes"
RELATORIOS_DIR = SAIDA_DIR / "relatorios"
EXPERIMENTOS_DIR = SAIDA_DIR / "experimentos"
```

Substitui `src/lotofacil_ml/config.py` e os `Path(__file__).resolve().parent.parent.parent / "dados"` espalhados.

## 7. Estratégia de migração — 8 ondas

Cada onda é commit atomico; cada onda termina com `pytest` verde + smoke test de pelo menos um comando CLI.

| # | Onda | Escopo | Critério de aceite |
|---|---|---|---|
| 1 | **Limpeza segura** | Deletar `legacy/`, `legado/` (preservando docs úteis em `docs/`), `ml/`, `src/sugestao/`, `src/main.py`, `src/lotofacil.db`, artefatos raiz (`portfolio_*.txt/json`, `egg-info`, `__pycache__`) | `pytest` passa igual; nenhum import quebra |
| 2 | **Esqueleto + domínio** | Criar `src/lotofacil/{dominio,servicos,infra,interface,experimentos}/`. Implementar `dominio/entidades.py`, `dominio/regras.py`, `dominio/estrategia.py` (Protocol), `dominio/excecoes.py`, `infra/config.py` | Domínio importável; testes de `dominio/` rodam sem dependência externa |
| 3 | **Migrar infra** | Mover canonicals para `infra/{dados,atributos,modelos,estrategias,avaliacao,agendador}/`. No mesmo commit, atualizar imports em `src/cli/modelo.py`, `src/cli/portfolio.py`, `src/cli/app.py prever` (e quaisquer outros) para os novos paths (`lotofacil.infra.*`). Resíduos vazios de `src/lotofacil_ml/`, `src/strategies/`, `src/data/`, `src/features/`, `src/models/`, `src/evaluation/`, `src/core/` ficam para a onda 5 deletar | CLI atual funciona; testes verdes |
| 4 | **Criar `servicos/`** | Extrair lógica de `cli/{dados,modelo,portfolio}.py` para `servicos/*.py` (11 use cases). Comandos CLI viram thin wrappers | Cada serviço com teste de unidade; comandos CLI funcionam idênticos |
| 5 | **Mover interface + renomear CLI** | `src/cli/` → `interface/cli/`; `src/dashboard/` → `interface/painel/`. Renomear comandos PT (`--all` → `--todos`, `lab ablation` → `lab ablacao`, etc.). Atualizar `pyproject.toml` (`[project.scripts] lotofacil = "lotofacil.interface.cli.app:app"` + `[tool.setuptools.packages.find] where = ["src"]`). Painel passa a chamar `servicos.*` em endpoints de leitura (`/api/status`, `/api/games`, `/api/predictions`, `/api/models/status`). Deletar resíduos vazios deixados pela onda 3 (`src/lotofacil_ml/`, `src/strategies/`, `src/data/`, `src/features/`, `src/models/`, `src/evaluation/`, `src/core/`) | `lotofacil <cmd-novo>` funciona; painel localhost:5000 funciona |
| 6 | **Experimentos** | Mover `src/lotofacil_lab/` → `src/lotofacil/experimentos/`. Ajustar imports | `lotofacil lab <cmd>` funciona |
| 7 | **Pastas dados/saida** | Consolidar pastas físicas (ver 6.4). Atualizar paths em `infra/config.py`. Preservar symlink externo | Comandos que leem/gravam dados funcionam |
| 8 | **Testes + docs** | Consolidar testes em `testes/{unidade,integracao}/`. Atualizar `pyproject.toml [tool.pytest.ini_options]`. Atualizar `CLAUDE.md`, `AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/PRD-dashboard.md` | `pytest` do root descobre tudo; docs alinhadas |

### 7.1 Pontos críticos por onda

- **Onda 3** é a mais arriscada (muitos imports). Estratégia: `git mv` para mover diretórios preservando história + atualização sincronizada de imports em `cli/*.py` no mesmo commit. Validação obrigatória antes do commit: `python -c "from lotofacil.interface.cli.app import app"` e `pytest`.
- **Onda 5** é a mais visível (muda comandos CLI). README, CLAUDE.md, AGENTS.md atualizados no mesmo commit.
- **Onda 7** mexe em `.keras` grandes. Usar `git mv` (preserva história, não duplica blob). Validar `du -sh .git/` antes/depois.

### 7.2 Estrutura de `tasks/`

A onda 1–8 vira a base de `tasks/` (gerada pelo writing-plans):

```
tasks/
├── 01-limpeza-segura/
│   ├── README.md
│   └── 01-deletar-legacy.md
│   └── 02-deletar-legado.md
│   └── …
├── 02-esqueleto-dominio/
├── 03-migrar-infra/
├── 04-criar-servicos/
├── 05-mover-interface/
├── 06-experimentos/
├── 07-pastas-fisicas/
└── 08-testes-docs/
```

Cada task contém:
- **Objetivo:** o que deve estar pronto ao final
- **Descrição técnica:** passos concretos
- **Arquivos envolvidos:** lista de paths que vão mudar
- **Dependências:** quais tasks precisam estar feitas antes
- **Critérios de aceite:** comando(s) a executar para validar
- **Prioridade:** alta/média/baixa

## 8. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Rename de classes (`Draw` → `Sorteio`, `Prediction` → `Predicao`) espalha em testes | Onda 2 cria aliases temporários `Draw = Sorteio`, `Prediction = Predicao` em `dominio/entidades.py`; onda 8 remove |
| Symlink `dados/` aponta pra fora do repo; testes podem assumir path interno | `infra/config.py` resolve via `Path.resolve()`; teste de smoke em onda 2 valida que paths existem |
| Painel quebra ao mover `static/` | Onda 5 atualiza `Flask(static_folder=...)` no mesmo commit |
| Histórico git "pesado" após renames massivos | Sempre `git mv`; `git log --follow` mantém rastreabilidade |
| TensorFlow opcional; modelos LSTM podem falhar em ambiente sem TF | Manter regra atual de `try/except ImportError` em `infra/modelos/__init__.py` |
| `pyproject.toml` muda namespace de pacote | Reinstalar em dev: `pip install -e .` após onda 5 — anotar no `tasks/05-…/README.md` |
| Painel hoje dispara CLI por `subprocess`; serviços precisam ser thread-safe quando chamados in-process | Manter `subprocess` para ações longas (treino, backtest); usar serviços diretos apenas em endpoints de leitura (`/api/status`, `/api/games`, `/api/predictions`, `/api/models/status`) |

## 9. Testes

### 9.1 Estrutura

```
testes/
├── unidade/
│   ├── dominio/         # puro, sem mocks (numpy ok)
│   ├── infra/           # cada infra com fakes do contrato
│   └── servicos/        # use cases com infra fake/in-memory
└── integracao/
    ├── cli/             # smoke tests dos comandos via CliRunner do Typer
    └── painel/          # endpoints via test client do Flask
```

### 9.2 Cobertura por onda

| Onda | Testes que entram/migram |
|---|---|
| 2 | Novos: testes de `dominio/entidades.py`, `dominio/regras.py` |
| 3 | Migram: `src/lotofacil_ml/tests/` → `testes/unidade/infra/` |
| 4 | Novos: um teste de unidade por serviço |
| 5 | Novos: smoke tests de CLI (substituem `tests/test_strategies/`) |
| 6 | Migram: `src/lotofacil_lab/tests/` → `testes/unidade/experimentos/` |
| 8 | Consolidação final: `pyproject.toml [tool.pytest.ini_options] testpaths = ["testes"]`; rodar tudo do root |

### 9.3 Smoke tests obrigatórios após cada onda

```bash
pytest                              # passa
lotofacil dados status              # responde sem erro
lotofacil prever                    # gera predição (ou erra se DB vazio — esperado)
```

## 10. Documentação a atualizar (onda 8)

- `README.md` — instalação, comandos PT, estrutura
- `CLAUDE.md` — paths novos, convenção PT
- `AGENTS.md` — substituir referências a `src/coleta/`, `src/geracao/`, `ml/` por nova árvore
- `docs/architecture.md` — substituir o diagrama de "v2.0" pelo de camadas + capacidades
- `docs/PRD-dashboard.md` — atualizar seção "arquitetura do sistema" para refletir nova estrutura (endpoints continuam idênticos)

## 11. Critérios de "pronto" do refactor

1. ✅ `pyproject.toml` aponta para `lotofacil.interface.cli.app:app`; pacote instalável (`pip install -e .`)
2. ✅ `pytest` do root descobre todos os testes e passa
3. ✅ `lotofacil dados status && lotofacil prever && lotofacil portfolio --jogos 4` rodam sem erro
4. ✅ `lotofacil painel` sobe; navegação em `localhost:5000` funciona; endpoints `/api/{status,games,predictions,models/status}` retornam dados
5. ✅ `lotofacil lab ablacao --n-test 50` roda
6. ✅ Não há mais pastas duplicadas (`data/`, `output/`, `legacy/`, `legado/`, `ml/`, `src/main.py`, `src/sugestao/`, `src/core/`, `src/models/`, `src/evaluation/`, `src/features/`, `src/data/`)
7. ✅ Não há mais inconsistência entre comandos CLI usando árvores diferentes
8. ✅ `docs/architecture.md` descreve a arquitetura realizada
9. ✅ `tasks/` documenta o que foi feito em 8 grupos de tasks

## 12. O que NÃO está neste spec

- Implementação dos gaps do PRD (rastreio de experimentos, ranking, comparação justa, explicabilidade). Ficam para o próximo ciclo, **construídos em cima** desta fundação.
- Mudanças no formato de dados persistidos (`Sorteio`/`Predicao` mantêm a mesma serialização JSON; SQLite schema inalterado).
- Mudanças nos endpoints do painel (contratos `/api/*` ficam idênticos).
- Mudanças no que cada modelo prediz ou no que cada estratégia entrega.
