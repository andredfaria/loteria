# Design — Fechamento garantido (covering design por orçamento fixo)

**Data:** 2026-06-07
**Status:** Aprovado (brainstorming) — pendente revisão do spec

## Contexto e premissa honesta

A Lotofácil é um sorteio uniforme e independente: cada dezena tem ~60% (15/25) de
chance por concurso, sem memória. **Nenhum modelo prevê os números acima do acaso** —
o `rodar_backtest` do repo já compara contra `random_game` por isso. Portanto este
trabalho **não** tenta melhorar acurácia de predição. Ele ataca o único lugar com
matemática real e provável: **fechamento (wheeling)** — dado um conjunto de N dezenas,
gerar jogos de 15 que **garantem** uma faixa de acerto se parte do pool for sorteada.

O fechamento controla a *distribuição* de prêmios de uma aposta fixa, **não** o valor
esperado (que segue negativo). A garantia é **condicional** às dezenas do pool serem
sorteadas.

## Objetivo

Modo **orçamento fixo**: o usuário informa quantos jogos de 15 pode pagar (B) e um pool
de N dezenas (auto-sugerido, com override manual). O sistema gera B jogos maximizando a
**garantia de pior caso** (covering design) e reporta a **curva de garantia**.

## Decisões tomadas no brainstorming

| Decisão | Escolha |
|---------|---------|
| Modo | Orçamento fixo (B jogos → maximizar garantia) |
| Pool | Auto-sugerido pelo score refinado + override manual (fixar/excluir) |
| Objetivo | Garantia de pior caso (covering design), não prêmios esperados |
| Algoritmo | Heurística gulosa + verificador exato (Abordagem A) |
| Integração | Serviço + CLI + botão no dashboard |

## Arquitetura (segue as 4 camadas do projeto)

```
infra/geracao/wheel.py          # núcleo combinatório (bitmask)
infra/geracao/pool_selector.py  # ranqueia/seleciona o pool de N dezenas
servicos/gerar_fechamento.py    # orquestra → ResultadoFechamento (frozen dataclass)
interface/cli/portfolio.py      # comando `portfolio fechar`
interface/painel/{commands.py,server.py,static/dashboard.html}  # botão + endpoint
testes/unidade/test_wheel.py, test_pool_selector.py
```

### Representação

Cada jogo e cada subconjunto são `int` de 25 bits (bit `n-1` = dezena `n`).
Acertos entre jogo `T` e sorteio `S` = `popcount(T & S)` (`int.bit_count()`).
Isso torna o verificador exato rápido o suficiente para N≤20.

## Componentes

### 1. `pool_selector.selecionar_pool(draws, n, fixar=(), excluir=()) -> list[int]`

- Calcula um **score composto** por dezena a partir do histórico: equilíbrio entre
  frequência (quão sorteada) e atraso (concursos desde a última aparição). Pesos com
  defaults razoáveis, configuráveis.
- Aplica override: `fixar` entram sempre no pool; `excluir` nunca; preenche o restante
  pelos maiores scores até atingir `n`.
- Garante que o pool seja "fechável": `15 <= n <= 25` e `n >= 15 + ...` validado.
- **Não promete previsão** — é refino marginal, documentado como tal.

### 2. `wheel.py`

- `acertos(jogo: int, sorteio: int) -> int` — `(jogo & sorteio).bit_count()`.
- `curva_garantia(jogos: list[int], pool: list[int]) -> dict[int, int]` — **verificador
  exato**: para cada `p` em `0..min(len(pool),15)`, retorna o `g` garantido =
  `min` sobre todos os p-subconjuntos do pool do `max` de acertos entre os jogos.
  Usa `itertools.combinations` sobre bits do pool + bitmask.
- `gerar_fechamento(pool: list[int], n_jogos: int, alvo_p: int | None) -> list[int]`:
  - `alvo_p` define para qual `p` (quantas das `N` do pool são sorteadas) a cobertura é
    otimizada. **Default: `alvo_p = min(len(pool), 15)`** (o melhor caso — assume que o
    máximo possível do pool foi sorteado). `p` válido: `0 <= alvo_p <= min(len(pool), 15)`.
  - Busca binária no nível de garantia `t`: para o `alvo_p`, covering guloso tenta cobrir
    todos os `alvo_p`-subconjuntos do pool com jogos de 15 ⊆ pool; mantém o maior `t` que
    cabe em `n_jogos`.
  - Refino por busca local: trocas de jogos que elevam a curva, dentro de um teto de
    iterações/tempo.
  - Sempre revalida o resultado com `curva_garantia` (a garantia reportada é a verificada,
    não a pretendida).

### 3. `servicos/gerar_fechamento.py`

```python
@dataclass(frozen=True)
class ResultadoFechamento:
    concurso_alvo: int
    pool: list[int]
    jogos: list[list[int]]
    curva_garantia: dict[int, int]   # p -> g garantido
    n_jogos: int
    custo_total: float               # n_jogos * COST_PER_GAME
    nota_ev: str                     # aviso honesto de EV negativo
```

Orquestra: carrega draws, seleciona pool, gera fechamento, monta a curva e o custo,
salva em `saida/jogos/`.

### 4. CLI

```
lotofacil portfolio fechar \
    --pool-size 18 --jogos 20 \
    [--fixar 7,10,25] [--excluir 13] [--alvo-p 14]
```

Imprime: pool escolhido, os B jogos, a tabela da curva de garantia, custo e a nota de EV.
Salva JSON em `saida/jogos/fechamento_<concurso>.json`.

### 5. Dashboard

Botão "Fechamento garantido" na aba Geração (`commands.py`), endpoint que chama o CLI,
exibe a curva de garantia e permite exportar os jogos. Segue o padrão de subprocess já
usado pelos outros comandos.

## Estratégia de testes (TDD)

- **Verificador exato vs força bruta** em N pequeno (ex.: pool=6, jogos de 3): conferir
  que `curva_garantia` concorda com enumeração ingênua.
- **Garantia conhecida**: caso trivial onde 1 jogo = pool de 15 → garante 15 se 15 saírem.
- **Invariante de monotonicidade**: adicionar jogos nunca reduz nenhum `g(p)`.
- **Respeito ao override**: `fixar`/`excluir` sempre honrados; pool tem tamanho `n`.
- **Cabe no orçamento**: `len(jogos) == n_jogos`; cada jogo tem 15 dezenas ⊆ pool.
- **Validação de entrada**: `n_jogos >= 1`, `15 <= pool_size <= 25`, `fixar ∩ excluir = ∅`.

## Fora de escopo (YAGNI)

- Tabelas de wheels publicados (Abordagem B) — evolução futura.
- ILP/SAT (Abordagem C).
- Otimização por prêmios esperados (modo híbrido) — o usuário escolheu pior caso.
- Modo "garantia fixa → minimizar jogos" (este spec é orçamento fixo).

## Riscos

- **Custo combinatório do verificador** para N grande e `p` intermediário
  (ex.: C(20,10)≈184k). Mitigado por bitmask+popcount e por restringir `p` à faixa
  relevante (tipicamente `p >= 11`). Se necessário, amostragem para `p` muito grande,
  mas o default fica no exato.
- **Heurística gulosa não é ótima global** — aceitável: a *garantia reportada* é exata
  (verificada), só a otimalidade do nº de jogos é heurística.
