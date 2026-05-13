# Task 2.3 — `dominio/regras.py` — constantes e regras da Lotofácil

**Onda:** 2 — Esqueleto + domínio
**Prioridade:** alta
**Tempo estimado:** ~15 min
**Depende de:** 2.2

## Objetivo

Centralizar todas as constantes do domínio Lotofácil (intervalo de dezenas, tamanho do sorteio, payouts, filtros estatísticos) em `dominio/regras.py`. Consolida o conteúdo hoje espalhado por `src/core/config.py`, `src/core/lottery.py`, `src/lotofacil_ml/config.py` (parte de constantes) e o `CLAUDE.md` (tabela de filtros).

## Descrição técnica

`dominio/regras.py` exporta:

- `DEZENA_MIN = 1`, `DEZENA_MAX = 25`, `TOTAL_DEZENAS_POSSIVEIS = 25`
- `DEZENAS_POR_SORTEIO = 15`
- `PRIZE_TABLE` (dict de acertos → prêmio em R$)
- `COST_PER_GAME` (custo por jogo R$ 3,00)
- Constantes de filtros estatísticos (faixas de target conforme CLAUDE.md):
  - `FAIXA_PARES_IMPARES`, `FAIXA_SOMA`, `FAIXA_PRIMOS`, `FAIXA_FIBONACCI`, `FAIXA_MOLDURA`, `FAIXA_REPETICOES`, `MIN_CONSECUTIVAS`
- `PRIMOS_LOTOFACIL`, `FIBONACCI_LOTOFACIL`, `MOLDURA` (sets)
- Funções puras: `eh_primo`, `eh_fibonacci`, `e_moldura`

## Arquivos envolvidos

**Criar:**
- `src/lotofacil/dominio/regras.py`
- `tests/test_dominio_regras.py`

**Referência (inspecionar):**
- `src/core/config.py`
- `src/core/lottery.py`
- `src/lotofacil_ml/config.py` (parte de PRIZE_TABLE, COST_PER_GAME)

## Dependências

- 2.2

## Critérios de aceite

- [ ] `from lotofacil.dominio.regras import DEZENA_MIN, DEZENA_MAX, DEZENAS_POR_SORTEIO, PRIZE_TABLE, COST_PER_GAME` funciona
- [ ] Funções `eh_primo(n)`, `eh_fibonacci(n)`, `e_moldura(n)` retornam bool
- [ ] Testes passam (todos os fatos da tabela do CLAUDE.md cobertos)

## Passos detalhados

- [ ] **Passo 1:** Inspecionar fontes

```bash
cat src/core/config.py src/core/lottery.py src/lotofacil_ml/config.py | head -100
```

Identificar todos os valores numéricos e tabelas de prêmio.

- [ ] **Passo 2:** Escrever testes (TDD)

`tests/test_dominio_regras.py`:

```python
"""Testes das regras e constantes do domínio Lotofácil."""
from lotofacil.dominio.regras import (
    DEZENA_MIN,
    DEZENA_MAX,
    DEZENAS_POR_SORTEIO,
    PRIZE_TABLE,
    COST_PER_GAME,
    PRIMOS_LOTOFACIL,
    FIBONACCI_LOTOFACIL,
    MOLDURA,
    eh_primo,
    eh_fibonacci,
    e_moldura,
)


def test_dezena_min_e_um():
    assert DEZENA_MIN == 1

def test_dezena_max_e_vinte_cinco():
    assert DEZENA_MAX == 25

def test_dezenas_por_sorteio_e_quinze():
    assert DEZENAS_POR_SORTEIO == 15

def test_prize_table_tem_chaves_11_a_15():
    assert set(PRIZE_TABLE.keys()) == {11, 12, 13, 14, 15}
    for acertos, premio in PRIZE_TABLE.items():
        assert premio > 0, f"prêmio para {acertos} acertos deve ser positivo"

def test_cost_per_game_e_300():
    assert COST_PER_GAME == 3.00

def test_primos_lotofacil():
    # Primos em [1, 25]: 2, 3, 5, 7, 11, 13, 17, 19, 23
    assert PRIMOS_LOTOFACIL == frozenset({2, 3, 5, 7, 11, 13, 17, 19, 23})

def test_fibonacci_lotofacil():
    # Fibonacci em [1, 25]: 1, 2, 3, 5, 8, 13, 21
    assert FIBONACCI_LOTOFACIL == frozenset({1, 2, 3, 5, 8, 13, 21})

def test_moldura_e_borda_e_canto():
    # Moldura = 1-5 ∪ 21-25 (conforme CLAUDE.md)
    assert MOLDURA == frozenset({1, 2, 3, 4, 5, 21, 22, 23, 24, 25})

def test_eh_primo():
    assert eh_primo(2)
    assert eh_primo(13)
    assert not eh_primo(1)
    assert not eh_primo(4)

def test_eh_fibonacci():
    assert eh_fibonacci(13)
    assert eh_fibonacci(21)
    assert not eh_fibonacci(4)
    assert not eh_fibonacci(25)

def test_e_moldura():
    assert e_moldura(1)
    assert e_moldura(25)
    assert not e_moldura(10)
    assert not e_moldura(15)
```

- [ ] **Passo 3:** Rodar testes (FALHA esperada)

```bash
pytest tests/test_dominio_regras.py -v
```

- [ ] **Passo 4:** Implementar `src/lotofacil/dominio/regras.py`

```python
"""Constantes e regras puras do domínio Lotofácil.

Single source of truth para limites, payouts e classificações estatísticas.
"""
from __future__ import annotations

# === Limites do jogo ===

DEZENA_MIN: int = 1
DEZENA_MAX: int = 25
TOTAL_DEZENAS_POSSIVEIS: int = 25
DEZENAS_POR_SORTEIO: int = 15

# === Tabela de prêmios (R$) ===
# Valores aproximados; consultar CAIXA para valor exato do concurso.
PRIZE_TABLE: dict[int, float] = {
    11: 6.00,
    12: 12.00,
    13: 30.00,
    14: 1_500.00,
    15: 1_500_000.00,
}

COST_PER_GAME: float = 3.00

# === Classificações estatísticas ===

PRIMOS_LOTOFACIL: frozenset[int] = frozenset({2, 3, 5, 7, 11, 13, 17, 19, 23})
FIBONACCI_LOTOFACIL: frozenset[int] = frozenset({1, 2, 3, 5, 8, 13, 21})
MOLDURA: frozenset[int] = frozenset({1, 2, 3, 4, 5, 21, 22, 23, 24, 25})

# === Faixas-alvo para filtros (target ranges) ===
# Referência: CLAUDE.md tabela "Key Statistical Filters"
FAIXA_PARES_IMPARES: tuple[int, int] = (7, 8)         # 7-8 ímpares (ou pares)
FAIXA_SOMA: tuple[int, int] = (171, 220)              # soma de 15 dezenas
FAIXA_PRIMOS: tuple[int, int] = (4, 7)
FAIXA_FIBONACCI: tuple[int, int] = (3, 5)
FAIXA_MOLDURA: tuple[int, int] = (8, 11)
FAIXA_REPETICOES: tuple[int, int] = (8, 10)            # do sorteio anterior
MIN_CONSECUTIVAS: int = 2                              # sequências consecutivas


def eh_primo(n: int) -> bool:
    """Retorna True se n é primo dentro do range Lotofácil."""
    return n in PRIMOS_LOTOFACIL


def eh_fibonacci(n: int) -> bool:
    """Retorna True se n pertence à sequência de Fibonacci em [1, 25]."""
    return n in FIBONACCI_LOTOFACIL


def e_moldura(n: int) -> bool:
    """Retorna True se n está na moldura (1-5 ∪ 21-25) do volante."""
    return n in MOLDURA
```

- [ ] **Passo 5:** Testes passam

```bash
pytest tests/test_dominio_regras.py -v
```

- [ ] **Passo 6:** Suite completa

```bash
pytest
```

- [ ] **Passo 7:** Commit

```bash
git add src/lotofacil/dominio/regras.py tests/test_dominio_regras.py
git commit -m "feat(dominio): adiciona regras.py — constantes da Lotofácil

Consolida em um só lugar:
- Limites do jogo (DEZENA_MIN, DEZENA_MAX, DEZENAS_POR_SORTEIO)
- Tabela de prêmios e custo por jogo
- Classificações estatísticas (primos, fibonacci, moldura)
- Faixas-alvo dos filtros conforme CLAUDE.md
- Funções puras: eh_primo, eh_fibonacci, e_moldura

Substitui (parcialmente) src/core/config.py + src/core/lottery.py
+ partes de src/lotofacil_ml/config.py."
```
