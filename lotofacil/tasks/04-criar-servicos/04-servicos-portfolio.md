# Task 4.4 — Serviços de portfólio: gerar + validar

**Onda:** 4 — Criar `servicos/`
**Prioridade:** alta
**Tempo estimado:** ~30 min
**Depende de:** 4.3

## Objetivo

Extrair lógica de `lotofacil portfolio` e `lotofacil portfolio validar` (hoje embutida em `src/cli/portfolio.py` que tem ~15KB) para serviços. Mover funções de geração de portfólio para `infra/geracao/`.

## Descrição técnica

`src/cli/portfolio.py` tem ~400 linhas com lógica de geração de portfólio tiered (conservador/balanceado/agressivo). Vamos separar:

- Lógica de geração → `infra/geracao/portfolio.py`
- Orquestração → `servicos/gerar_portfolio.py` + `servicos/validar_portfolio.py`
- CLI thin wrapper → continua em `cli/portfolio.py` (será movido na onda 5)

## Arquivos envolvidos

**Criar:**
- `src/lotofacil/infra/geracao/portfolio.py` — geração técnica (combinatorial, otimização, scoring)
- `src/lotofacil/servicos/gerar_portfolio.py`
- `src/lotofacil/servicos/validar_portfolio.py`
- `tests/test_servicos_portfolio.py`

## Dependências

- 4.3

## Critérios de aceite

- [ ] `from lotofacil.servicos.gerar_portfolio import gerar_portfolio, ResultadoPortfolio` funciona
- [ ] `from lotofacil.servicos.validar_portfolio import validar_portfolio, ResultadoValidacaoPortfolio` funciona
- [ ] `from lotofacil.infra.geracao.portfolio import gerar_portfolio_tiered` funciona
- [ ] Testes passam

## Passos detalhados

- [ ] **Passo 1:** Inspecionar `src/cli/portfolio.py` para identificar funções a extrair

```bash
grep -n "^def \|^class " src/cli/portfolio.py
```

Anotar funções "puras" (geração combinatorial, scoring) vs orquestração (load → generate → save).

- [ ] **Passo 2:** Extrair funções puras para `infra/geracao/portfolio.py`

```python
"""Geração de portfólios — combinatorial, scoring, otimização."""
from __future__ import annotations

import itertools
from dataclasses import dataclass

from lotofacil.dominio.entidades import Portfolio, Sorteio


@dataclass(frozen=True)
class ConfigPortfolio:
    n_jogos: int = 5
    abordagem: str = "ensemble"


def gerar_portfolio_tiered(
    sorteios: list[Sorteio],
    dezenas_provaveis: tuple[int, ...],
    config: ConfigPortfolio,
) -> Portfolio:
    """Gera um portfólio tiered (conservador/balanceado/agressivo)."""
    # Mover aqui as funções de combinatorial generation que estão em cli/portfolio.py
    ...
```

> **Nota:** copiar o miolo de geração combinatorial e scoring do `cli/portfolio.py` atual.

- [ ] **Passo 3:** Implementar `src/lotofacil/servicos/gerar_portfolio.py`

```python
"""Serviço: gera portfólio de jogos para o próximo concurso."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from lotofacil.dominio.entidades import Portfolio
from lotofacil.infra.config import DB_PATH, JOGOS_DIR, garantir_diretorio
from lotofacil.infra.dados import DatabaseManager
from lotofacil.infra.geracao.portfolio import ConfigPortfolio, gerar_portfolio_tiered
from lotofacil.servicos.gerar_predicao import gerar_predicao


@dataclass(frozen=True)
class ResultadoPortfolio:
    portfolio: Portfolio
    arquivo: str


def gerar_portfolio(
    n_jogos: int = 5,
    concurso_alvo: Optional[int] = None,
    abordagem: str = "ensemble",
) -> ResultadoPortfolio:
    """Gera N jogos para o próximo concurso baseado em predição."""
    banco = DatabaseManager(DB_PATH)
    sorteios = banco.carregar_sorteios()

    pred = gerar_predicao(abordagem=abordagem, concurso_alvo=concurso_alvo, persistir=False)

    portfolio = gerar_portfolio_tiered(
        sorteios=sorteios,
        dezenas_provaveis=pred.dezenas,
        config=ConfigPortfolio(n_jogos=n_jogos, abordagem=abordagem),
    )

    garantir_diretorio(JOGOS_DIR)
    arquivo = JOGOS_DIR / f"portfolio_{pred.concurso_alvo}.json"
    arquivo.write_text(
        json.dumps({
            "concurso": pred.concurso_alvo,
            "estrategia": portfolio.estrategia,
            "jogos": [sorted(j) for j in portfolio.jogos],
            "metadados": portfolio.metadados,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return ResultadoPortfolio(portfolio=portfolio, arquivo=str(arquivo))
```

- [ ] **Passo 4:** Implementar `src/lotofacil/servicos/validar_portfolio.py`

```python
"""Serviço: valida portfólio gerado contra sorteio real."""
from __future__ import annotations

import json
from dataclasses import dataclass

from lotofacil.dominio.excecoes import SorteioNaoEncontrado
from lotofacil.infra.config import DB_PATH, JOGOS_DIR
from lotofacil.infra.dados import DatabaseManager


@dataclass(frozen=True)
class AcertoJogo:
    indice: int
    dezenas: tuple[int, ...]
    acertos: int
    premio: float


@dataclass(frozen=True)
class ResultadoValidacaoPortfolio:
    concurso: int
    jogos: list[AcertoJogo]
    total_premio: float
    roi: float


def validar_portfolio(concurso: int) -> ResultadoValidacaoPortfolio:
    """Valida o portfólio gerado para o concurso contra o sorteio real."""
    banco = DatabaseManager(DB_PATH)
    sorteio = banco.buscar_sorteio(concurso)
    if sorteio is None:
        raise SorteioNaoEncontrado(concurso=concurso)

    arquivo = JOGOS_DIR / f"portfolio_{concurso}.json"
    if not arquivo.exists():
        raise FileNotFoundError(f"Portfólio para concurso {concurso} não foi gerado: {arquivo}")

    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    jogos_data = dados.get("jogos", [])

    # Tabela de prêmios (importar de dominio/regras.py)
    from lotofacil.dominio.regras import PRIZE_TABLE, COST_PER_GAME

    acertos_jogos: list[AcertoJogo] = []
    total_premio = 0.0
    for i, jogo in enumerate(jogos_data):
        dezenas = tuple(sorted(jogo))
        n_acertos = sum(1 for d in dezenas if d in sorteio.dezenas)
        premio = PRIZE_TABLE.get(n_acertos, 0.0)
        total_premio += premio
        acertos_jogos.append(AcertoJogo(
            indice=i,
            dezenas=dezenas,
            acertos=n_acertos,
            premio=premio,
        ))

    custo_total = COST_PER_GAME * len(jogos_data)
    roi = (total_premio - custo_total) / custo_total if custo_total > 0 else 0.0

    return ResultadoValidacaoPortfolio(
        concurso=concurso,
        jogos=acertos_jogos,
        total_premio=total_premio,
        roi=roi,
    )
```

- [ ] **Passo 5:** Escrever testes (esqueleto)

`tests/test_servicos_portfolio.py`:

```python
"""Testes dos serviços de portfólio."""
from datetime import date
from unittest.mock import MagicMock

import pytest

from lotofacil.dominio.entidades import Sorteio
from lotofacil.dominio.excecoes import SorteioNaoEncontrado
from lotofacil.servicos.validar_portfolio import validar_portfolio


def test_validar_portfolio_sorteio_inexistente(monkeypatch, tmp_path):
    banco_mock = MagicMock()
    banco_mock.buscar_sorteio.return_value = None
    monkeypatch.setattr("lotofacil.servicos.validar_portfolio.DatabaseManager", lambda *_: banco_mock)

    with pytest.raises(SorteioNaoEncontrado) as exc:
        validar_portfolio(concurso=99999)
    assert exc.value.concurso == 99999


def test_validar_portfolio_arquivo_inexistente(monkeypatch, tmp_path):
    banco_mock = MagicMock()
    banco_mock.buscar_sorteio.return_value = Sorteio(
        concurso=1, data=date.today(), dezenas=tuple(range(1, 16))
    )
    monkeypatch.setattr("lotofacil.servicos.validar_portfolio.DatabaseManager", lambda *_: banco_mock)
    monkeypatch.setattr("lotofacil.servicos.validar_portfolio.JOGOS_DIR", tmp_path)

    with pytest.raises(FileNotFoundError):
        validar_portfolio(concurso=1)
```

- [ ] **Passo 6:** Rodar testes

```bash
pytest tests/test_servicos_portfolio.py -v
```

- [ ] **Passo 7:** Suite

```bash
pytest
```

- [ ] **Passo 8:** Commit

```bash
git add src/lotofacil/infra/geracao/ src/lotofacil/servicos/gerar_portfolio.py src/lotofacil/servicos/validar_portfolio.py tests/test_servicos_portfolio.py
git commit -m "feat(servicos+infra): gerar_portfolio + validar_portfolio

- Lógica combinatorial extraída para infra/geracao/portfolio.py
- gerar_portfolio(n_jogos, concurso_alvo, abordagem) → ResultadoPortfolio
- validar_portfolio(concurso) → ResultadoValidacaoPortfolio

cli/portfolio.py vira thin wrapper na task 4.6."
```
