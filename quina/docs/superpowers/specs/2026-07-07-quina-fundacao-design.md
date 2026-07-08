# Quina — Fase 1: Fundação (design)

Data: 2026-07-07

## Contexto

O usuário quer replicar o dashboard completo da Lotofácil (`lotofacil/src/lotofacil/interface/painel/`) para a **Quina**. O dashboard da Lotofácil não é uma camada isolada: é uma view fina sobre um pipeline completo (coleta de dados, banco, feature engineering, ensemble de modelos ML, backtest, geração de portfólio, registry de treinos). Não existe nenhum código de Quina no monorepo hoje.

Dado o tamanho, o trabalho foi decomposto em sub-projetos, cada um com seu próprio ciclo design → plano → implementação:

1. **Fundação** (este documento) — scaffold do projeto `quina/`, regras de domínio, coleta de dados, banco, CLI básica
2. **Estatística/Features** — frequência, atraso, feature engineering adaptados às regras da Quina
3. **Modelos ML** — ensemble (frequência, probabilístico, neural, ML), treino
4. **Backtest** — motor de avaliação, métricas, relatórios
5. **Portfólio** — geração de jogos, filtros estatísticos
6. **CLI completa** — comandos `modelo treinar`, `prever`, `portfolio gerar`, `lab`
7. **Dashboard** — servidor Flask + UI, ligado a tudo acima (status, treinos, backtest, portfólio, alertas)

### Decisão de estrutura de código

`quina/` é um **projeto irmão independente** de `lotofacil/`, `super-sete/` e `dia-de-sorte/`, seguindo a convenção já estabelecida no monorepo (pyproject.toml, venv e banco próprios, sem dependência entre pacotes). A arquitetura de 4 camadas da Lotofácil (`dominio/servicos/infra/interface`) é copiada e adaptada às regras da Quina, não extraída para uma lib compartilhada — evita refatorar a Lotofácil antes de começar, e mantém os projetos desacoplados como já são hoje.

## Regras do jogo — Quina

Confirmado ao vivo via `https://loteriascaixa-api.herokuapp.com/api/quina/latest`:

- 5 números sorteados de um universo de 1 a 80 (`TOTAL_NUMEROS=80`, `NUMEROS_POR_SORTEIO=5`)
- Faixas de premiação: **2, 3, 4 e 5 acertos** (`FAIXAS_ACERTOS=[2,3,4,5]`) — diferente da Lotofácil, que só paga a partir de 11 acertos
- Os valores de prêmio por faixa são **variáveis** (rateio proporcional do valor arrecadado), não fixos como as faixas 11–14 da Lotofácil. Por isso a Fase 1 **não** define uma `TABELA_PREMIOS` estática — isso é responsabilidade da Fase 4 (Backtest) / Fase 5 (Portfólio), que vão calcular a partir de dados históricos reais de premiação.

## Arquitetura — Fase 1

```
quina/
├── src/quina/
│   ├── dominio/
│   │   ├── entidades.py    # Sorteio (Pydantic), SorteioBruto
│   │   ├── regras.py       # constantes + validações puras
│   │   └── excecoes.py
│   ├── infra/
│   │   ├── config.py       # paths, constantes do jogo, config de API
│   │   └── dados/
│   │       ├── api_caixa.py   # fetch com retry (tenacity)
│   │       ├── banco.py       # DatabaseManager (SQLite)
│   │       └── leitor.py
│   └── interface/
│       └── cli/
│           ├── app.py          # Typer root
│           └── dados.py        # `quina dados atualizar` / `quina dados status`
├── dados/ → symlink para ~/quina-dados/
│   └── sample/                 # ~100 concursos mais recentes, comitados no repo
├── testes/
│   ├── unidade/
│   └── integracao/
├── docs/superpowers/specs/     # este arquivo
└── pyproject.toml              # entry point: `quina`
```

## Componentes e fluxo de dados

- **`dominio/regras.py`** — `TOTAL_NUMEROS=80`, `NUMEROS_POR_SORTEIO=5`, `VALID_NUMBERS=set(range(1,81))`, `FAIXAS_ACERTOS=[2,3,4,5]`, e funções puras: `validar_dezenas`, `contar_acertos`, `contar_pares`/`contar_impares`, `soma_dezenas`. Conceitos específicos da Lotofácil que não fazem sentido ainda para Quina (moldura, quadrantes, primos, fibonacci) ficam para a Fase 2 (Features), quando forem recalibrados para o universo 1–80.
- **`dominio/entidades.py`** — `Sorteio` (Pydantic): `concurso: int`, `data: str`, `dezenas: list[int]` com validador (5 números únicos, 1–80, ordenados). `SorteioBruto` para o payload cru da API.
- **`infra/config.py`** — `PROJETO_RAIZ`, `DADOS_DIR` (symlink), `DB_PATH = DADOS_DIR / "quina.db"`, `SAIDA_DIR`, `API_BASE_URL`, `API_QUINA = f"{API_BASE_URL}/quina"`, `API_TIMEOUT`, `API_RETRIES`, `API_RETRY_MIN/MAX`, `USER_AGENT`. Mesmos valores de retry/timeout da Lotofácil.
- **`infra/dados/api_caixa.py`** — `QuinaFetcher`, espelhando `LotofacilFetcher`: `fetch_latest()`, `fetch_by_concurso(n)`, `sync_new_draws()`. Retry via `tenacity` (5 tentativas, backoff exponencial 1–10s). Validação de payload: exatamente 5 dezenas, todas em 1–80; registros inválidos são logados (`logger.warning`) e descartados sem interromper o sync. Salva o JSON bruto em `dados/concurso_{N}.json` (não sobrescreve se já existir).
- **`infra/dados/banco.py`** — `DatabaseManager` (SQLite), tabela `concursos` (schema idêntico à Lotofácil: `concurso INTEGER PRIMARY KEY, data TEXT, dezenas TEXT, raw_json TEXT`, upsert idempotente por `concurso`). Tabela `predicoes` é criada no schema desde já (custo zero) mas só passa a ser usada a partir da Fase 3 (Modelos ML).
- **`interface/cli/dados.py`** — `quina dados atualizar` (sync incremental: busca `latest` na API, compara com o último concurso local, busca sequencialmente os que faltam) e `quina dados status` (contagem total, último concurso, gaps na sequência).

Fluxo de `quina dados atualizar`:
1. Busca `latest` na API (`GET /api/quina/latest`)
2. Compara com `get_latest_concurso()` do banco local
3. Para cada concurso faltante, busca individualmente (`GET /api/quina/{n}`), valida, faz upsert no SQLite e grava o JSON bruto em `dados/`
4. Falha de rede em um concurso não interrompe o loop nem corrompe concursos já persistidos (commit por concurso)

## Tratamento de erros

- `tenacity` com backoff exponencial (5 tentativas, 1–10s) para todas as chamadas HTTP à API da Caixa
- Registros malformados (contagem de dezenas ≠ 5, valores fora de 1–80, campos ausentes) são descartados com log de warning, não geram exceção que interrompa o comando
- Upsert idempotente por `concurso` — reexecutar `dados atualizar` é seguro
- Sem rede / API fora do ar em `sync_new_draws`: retorna 0 novos concursos sincronizados, sem tocar no banco existente

## Testes

- `testes/unidade/` — `regras.py` (validação de dezenas, contagem de acertos, soma), `entidades.py` (validadores Pydantic: quantidade errada, duplicatas, fora do range)
- `testes/integracao/` — `banco.py` (upsert/consulta round-trip, idempotência), comando `quina dados atualizar` com API mockada via `responses` (mesmo padrão de teste já usado no projeto Lotofácil)

## Dependências (`pyproject.toml`)

Enxuto para a Fase 1 — sem ML/Flask, que entram nas fases seguintes:

```toml
dependencies = [
    "requests>=2.31.0",
    "tenacity>=8.2.0",
    "pydantic>=2.0.0",
    "typer>=0.9.0",
    "rich>=13.0.0",
]
[project.optional-dependencies]
dev = ["pytest>=7.4.0", "responses>=0.23.0"]
[project.scripts]
quina = "quina.interface.cli.app:app"
```

## Dados de amostra

`dados/sample/` com os ~100 concursos mais recentes da Quina, comitados no repositório — mesma convenção descrita no `CLAUDE.md` da raiz do monorepo.

## Fora de escopo (Fase 1)

- Feature engineering (moldura, quadrantes, primos, fibonacci recalibrados para 1–80) → Fase 2
- Qualquer modelo ML / ensemble → Fase 3
- Backtest, métricas financeiras, tabela de prêmios → Fase 4
- Geração de portfólio / filtros estatísticos → Fase 5
- Comandos CLI além de `dados atualizar`/`status` → Fase 6
- Dashboard Flask / UI → Fase 7
- Scheduler (APScheduler) para atualização automática → Fase 6+ (a Lotofácil atualiza seg/qua/sex 23h; a Quina sorteia de segunda a sábado, então a cadência de agendamento precisa ser revisitada quando chegarmos lá)
