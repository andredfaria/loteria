# Quina — Motor Estatístico + Gerador de Jogos (design)

Data: 2026-07-09

## Contexto

A Fase 1 (Fundação, `2026-07-07-quina-fundacao-design.md`) e o Dashboard Mínimo (`2026-07-08-quina-dashboard-design.md`) já estão implementados: coleta de dados, banco SQLite, CLI `quina dados atualizar`/`status`, e um painel Flask com status/frequência/atraso/atualizar.

O roadmap original da Fundação previa, em sequência: Fase 2 (Estatística/Features), Fase 3 (Modelos ML — ensemble neural), Fase 4 (Backtest), Fase 5 (Portfólio). **Este documento substitui as Fases 2–5** por uma abordagem única e consolidada: um motor **estatístico/heurístico** (filtros combinatórios, frequência/atraso, fechamento, portfólio por orçamento), não um ensemble de ML/LSTM.

Motivo da mudança: como cada sorteio da Quina é independente (i.i.d.), um ensemble neural treinado sobre o histórico não tem fundamento estatístico para ter poder preditivo real — o mesmo vale, em menor grau, para os filtros combinatórios, mas estes têm uma vantagem genuína e diferente: **maximizar valor esperado condicional ao acerto**, evitando números populares (1–31, associados a datas) para reduzir o rateio do prêmio com outros apostadores, dado que a probabilidade de acerto é a mesma independente da escolha. Essa é a estratégia com maior chance de ter valor prático real, e é o filtro `anti_popularidade` descrito abaixo.

A UI do dashboard que expõe este motor (treino, geração, exibição de jogos) fica para um sub-projeto seguinte, com seu próprio spec.

## Escopo

Dentro do escopo:
- Regras de domínio para tamanho de aposta variável (5–15 dezenas) e cálculo de custo
- Camada de estratégias: filtros combinatórios + scoring, frequência/atraso ponderados
- Fechamento/wheeling com garantia (cobertura aproximada, greedy)
- Portfólio por orçamento (3 perfis)
- "Treino" = backtest walk-forward de estratégias contra o histórico real, com comparação a baseline aleatório
- Persistência: tabelas `estrategias_backtest` e `jogos_gerados`
- CLI (`quina modelo`, `quina jogos`, `quina portfolio`) e rotas Flask síncronas com `job_id` de gancho

Fora do escopo (fica para sub-projetos futuros):
- Dashboard/UI (telas de treino, leaderboard, exibição de jogos) — próximo spec
- Ensemble ML/LSTM — só entra se algum dia houver justificativa
- Autenticação, scheduler automático

## Regras de domínio (`dominio/regras.py`)

Adições:

```python
TAMANHO_APOSTA_MIN = 5
TAMANHO_APOSTA_MAX = 15

def custo_aposta(n: int) -> float:
    """Custo de uma aposta com n dezenas: comb(n,5) apostas de 5 dezenas embutidas."""
    if not (TAMANHO_APOSTA_MIN <= n <= TAMANHO_APOSTA_MAX):
        raise ValueError(f"Tamanho de aposta deve estar entre {TAMANHO_APOSTA_MIN} e {TAMANHO_APOSTA_MAX}")
    return round(comb(n, NUMEROS_POR_SORTEIO) * PRECO_APOSTA_MINIMA, 2)
```

`infra/config.py` ganha `PRECO_APOSTA_MINIMA = 3.00` — constante isolada, com comentário indicando que deve ser atualizada manualmente quando a Caixa reajustar o valor oficial da aposta mínima de 5 dezenas.

## Camada de estratégias (`src/quina/servicos/estrategias/`)

Novo pacote `servicos/`, mirror do padrão `lotofacil/src/lotofacil/servicos/gerar_campeao.py`, adaptado ao universo 1–80 e a tamanho de aposta variável.

### `filtros.py`

Funções puras de scoring, cada uma retornando um componente `float` em `[0, 1]` para um candidato `list[int]` de tamanho `n` (5–15):

- **`score_soma`**: soma das dezenas dentro da faixa histórica real (percentil 25–75 calculado dinamicamente a partir de `get_all_concursos()`, escalado proporcionalmente ao tamanho `n` da aposta) — não uma faixa fixa como na Lotofácil, já que o universo e o tamanho de aposta variam.
- **`score_paridade`**: proporção pares/ímpares próxima da distribuição binomial esperada para `n` sorteios de um universo com 40 pares e 40 ímpares.
- **`score_quadrantes`**: distribuição por quadrantes (1–20, 21–40, 41–60, 61–80) — penaliza concentração excessiva em um quadrante.
- **`score_primos`**: proporção de números primos entre 1–80 próxima da proporção histórica observada.
- **`score_repeticao`**: baixa repetição com o sorteio imediatamente anterior (calibrado pela taxa histórica real de repetição, não um valor arbitrário).
- **`score_consecutivos`**: penaliza sequências de números consecutivos acima da taxa histórica observada.
- **`score_anti_popularidade`**: penaliza candidatos com proporção de dezenas ≤31 acima do esperado por acaso (`31/80 ≈ 38.75%`) — a estratégia de valor esperado condicional descrita no Contexto.

### `scoring.py`

`gerar_candidatos(n: int, tamanho_aposta: int, draws: list[Sorteio]) -> list[dict]`: gera `n` candidatos aleatórios de `tamanho_aposta` dezenas, aplica todos os filtros de `filtros.py` com pesos configuráveis (default: pesos iguais), soma o score, retorna ordenado decrescente. `top_k(candidatos, k)` retorna os `k` melhores.

### `frequencia_atraso.py`

`pontuar_por_frequencia_atraso(draws, peso_freq=0.5, peso_atraso=0.5) -> dict[int, float]`: normaliza frequência (0–1) e atraso (0–1) por número, combina pelos pesos informados. Usado standalone (endpoint de sugestão de números) e como filtro adicional plugável em `scoring.py`.

## Fechamento/wheeling (`servicos/fechamento.py`)

`gerar_fechamento(pool: list[int], garantia: tuple[int, int]) -> list[list[int]]`: dado um pool de M dezenas escolhidas pelo usuário e uma garantia `(k, faixa)` (ex: `(4, 4)` = "garantir quadra se 4 das M dezenas saírem"), gera a cobertura mínima aproximada de jogos de 5 dezenas via **greedy set-cover**: a cada passo, escolhe o jogo de 5 dezenas (dentre combinações do pool) que cobre o maior número de combinações de garantia ainda não cobertas, até cobertura completa.

Documentado explicitamente como **aproximação gulosa**, não o mínimo matemático ótimo (problema de cobertura exata é NP-difícil para M grande). Retorna a lista de jogos e o custo total (`len(jogos) * custo_aposta(5)`).

## Portfólio por orçamento (`servicos/portfolio.py`)

`gerar_portfolio(orcamento: float, perfil: str, draws) -> list[dict]`: distribui o orçamento entre jogos gerados por `scoring.gerar_candidatos`, respeitando `custo_aposta(n)`:

- **conservador**: muitos jogos de 5 dezenas com score alto (maximiza cobertura de combinações distintas dentro do orçamento)
- **equilibrado**: mix de tamanhos 5–8, priorizando score
- **agressivo**: poucos jogos de tamanho maior (10–15), priorizando chance individual por jogo sobre quantidade

Para de adicionar jogos quando o próximo excederia o orçamento restante. Retorna lista de jogos + custo total + orçamento não utilizado.

## "Treino" = backtest walk-forward (`servicos/backtest.py`)

`rodar_backtest(estrategia: str, janela: int = 300, draws=None) -> dict`:

1. Para os últimos `janela` concursos (default 300, configurável), em cada passo `i`: usa os concursos `[0, i)` como histórico disponível, gera candidatos com a estratégia escolhida, mede acertos contra o resultado real do concurso `i`.
2. Roda em paralelo uma baseline de candidatos puramente aleatórios (mesma janela, mesmo tamanho de aposta) para comparação.
3. Métricas retornadas: taxa média de acertos por faixa (2, 3, 4, 5), taxa de acerto da estratégia vs. taxa de acerto da baseline aleatória (delta), tempo de execução.
4. Resultado persistido em `estrategias_backtest`.

Este resultado é deliberadamente honesto: espera-se que a maioria das estratégias empate estatisticamente com a baseline aleatória (exceto `anti_popularidade`, cujo ganho não aparece em taxa de acerto, e sim em valor esperado de prêmio — não medido pelo backtest de acertos, e sim documentado como nota separada no resultado).

## Persistência (`infra/dados/banco.py`)

Duas tabelas novas, adicionadas ao `_init_db()` existente:

```sql
CREATE TABLE IF NOT EXISTS estrategias_backtest (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    estrategia      TEXT NOT NULL,
    janela          INTEGER NOT NULL,
    metricas_json   TEXT NOT NULL,       -- taxa por faixa, delta vs baseline, tempo
    criado_em       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jogos_gerados (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    estrategia               TEXT NOT NULL,
    tamanho_aposta            INTEGER NOT NULL,
    dezenas_json              TEXT NOT NULL,
    score                     REAL,
    custo                     REAL NOT NULL,
    criado_em                 TEXT DEFAULT (datetime('now')),
    concurso_alvo_validacao   INTEGER,   -- NULL até haver um concurso pra validar contra
    acertos                   INTEGER    -- preenchido quando o concurso sai
);
```

A tabela `predicoes` existente (criada na Fase 1, nunca usada) permanece intocada — não é removida neste sub-projeto, para não gerar uma migração destrutiva sem necessidade; fica candidata a remoção futura se confirmado que não serve para nada.

**Validação automática de acertos**: `interface/cli/dados.py` (fluxo `quina dados atualizar`) passa, após cada novo concurso sincronizado, a atualizar `jogos_gerados` onde `concurso_alvo_validacao` bate com o concurso novo — calcula `acertos` via `contar_acertos` e grava. Reaproveita o fluxo existente, sem novo comando.

## API

### CLI (novos sub-apps Typer, seguindo padrão de `lotofacil/interface/cli/modelo.py` e `portfolio.py`)

- `quina modelo treinar [--estrategia TEXT] [--janela INT]` — roda backtest, salva no leaderboard, imprime tabela `rich`
- `quina modelo leaderboard` — lista últimos backtests salvos
- `quina jogos gerar --estrategia filtros|freq-atraso --tamanho INT --n INT` — gera e persiste N jogos, imprime tabela
- `quina jogos fechamento --dezenas 1,5,12,... --garantia 4,4` — gera fechamento, imprime jogos + custo total
- `quina portfolio gerar --orcamento FLOAT --perfil conservador|equilibrado|agressivo`

### Flask (rotas síncronas, com `job_id` gerado na resposta como gancho para versão assíncrona futura — sem fila real agora)

- `POST /api/treinos/iniciar {estrategia, janela}` → roda backtest de forma síncrona, retorna `{"job_id": str, "resultado": {...}}`
- `GET /api/treinos` → leaderboard (últimos backtests)
- `POST /api/jogos/gerar {estrategia, tamanho_aposta, quantidade}` → gera, persiste e retorna jogos
- `GET /api/jogos` → lista jogos gerados persistidos (paginação simples)
- `POST /api/fechamento {dezenas, garantia}` → retorna jogos + custo
- `POST /api/portfolio {orcamento, perfil}` → retorna jogos + custo total + sobra

## Testes

- `testes/unidade/` — cada filtro de `filtros.py` isoladamente (casos conhecidos com score esperado), `custo_aposta` (valores conferidos manualmente para n=5..15), `fechamento` (cobertura garantida em pool pequeno verificável à mão)
- `testes/integracao/` — `backtest.py` contra fixtures de `sample_draws`, round-trip de `estrategias_backtest`/`jogos_gerados` no banco, validação automática de acertos após `dados atualizar` mockado, rotas Flask novas via `app.test_client()`

## Fora de escopo (reforço)

- Dashboard/UI — sub-projeto seguinte, próprio spec
- Ensemble ML/LSTM
- Autenticação, scheduler automático de treino/geração
