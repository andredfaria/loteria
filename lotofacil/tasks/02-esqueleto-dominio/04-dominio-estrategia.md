# Task 2.4 — `dominio/estrategia.py` — Protocol EstrategiaBase

**Onda:** 2 — Esqueleto + domínio
**Prioridade:** alta
**Tempo estimado:** ~15 min
**Depende de:** 2.3

## Objetivo

Definir o contrato (Protocol) que todas as estratégias devem implementar. Substitui `src/strategies/base.py` (`BaseStrategy` ABC). Como é Protocol, qualquer classe que tenha os métodos certos é estrutura compatível — não precisa herdar.

## Descrição técnica

`src/strategies/base.py` hoje define `BaseStrategy` como ABC com métodos abstratos. Vamos:

1. Inspecionar `src/strategies/base.py` para captar a API
2. Reescrever como `typing.Protocol` em `dominio/estrategia.py` com nome PT (`EstrategiaBase`)
3. Manter o conceito de `predict` retornando `Predicao` (já em `dominio/entidades.py`)

## Arquivos envolvidos

**Criar:**
- `src/lotofacil/dominio/estrategia.py`
- `tests/test_dominio_estrategia.py`

**Referência:**
- `src/strategies/base.py`

## Dependências

- 2.2 (Predicao existe)

## Critérios de aceite

- [ ] `from lotofacil.dominio.estrategia import EstrategiaBase` funciona
- [ ] `EstrategiaBase` é um `typing.Protocol`
- [ ] Uma classe concreta que implementa `predict()` e `predict_batch()` satisfaz `isinstance(obj, EstrategiaBase)` quando o Protocol é runtime-checkable
- [ ] Testes passam

## Passos detalhados

- [ ] **Passo 1:** Inspecionar `src/strategies/base.py`

```bash
cat src/strategies/base.py
```

Identificar:
- nome da classe (`BaseStrategy`)
- métodos (`predict`, `predict_batch`, propriedades `name`, `target_count`, `approaches`)
- assinatura exata

- [ ] **Passo 2:** Escrever testes

`tests/test_dominio_estrategia.py`:

```python
"""Testes do Protocol EstrategiaBase."""
from datetime import date

from lotofacil.dominio.entidades import Sorteio, Predicao
from lotofacil.dominio.estrategia import EstrategiaBase


class EstrategiaFake:
    """Implementação mínima que satisfaz EstrategiaBase estruturalmente."""

    @property
    def nome(self) -> str:
        return "fake"

    @property
    def total_dezenas(self) -> int:
        return 11

    @property
    def abordagens_suportadas(self) -> tuple[str, ...]:
        return ("statistical",)

    def predict(self, sorteios, abordagem="statistical"):
        return Predicao(
            concurso_alvo=sorteios[-1].concurso + 1,
            dezenas=tuple(range(1, 12)),
            abordagem=abordagem,
            confianca_media=0.5,
        )

    def predict_batch(self, sorteios, abordagem="statistical"):
        return [self.predict(sorteios, abordagem)]


def test_estrategia_fake_satisfaz_protocol():
    e = EstrategiaFake()
    # Protocol runtime-checkable
    assert isinstance(e, EstrategiaBase)


def test_predict_retorna_predicao():
    e = EstrategiaFake()
    sorteio = Sorteio(concurso=1, data=date.today(), dezenas=tuple(range(1, 16)))
    pred = e.predict([sorteio])
    assert isinstance(pred, Predicao)
    assert pred.concurso_alvo == 2
```

- [ ] **Passo 3:** Rodar testes (FALHA esperada)

- [ ] **Passo 4:** Implementar `src/lotofacil/dominio/estrategia.py`

```python
"""Contrato (Protocol) das estratégias de predição.

Qualquer classe que implemente os métodos abaixo satisfaz EstrategiaBase
estruturalmente — não precisa herdar (duck typing via Protocol).
"""
from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from lotofacil.dominio.entidades import Predicao, Sorteio


@runtime_checkable
class EstrategiaBase(Protocol):
    """Contrato comum a todas as estratégias de predição.

    Subclasses concretas vivem em ``lotofacil.infra.estrategias.<N>_dezenas``.
    """

    @property
    def nome(self) -> str:
        """Nome curto da estratégia (ex.: '11-dezenas')."""
        ...

    @property
    def total_dezenas(self) -> int:
        """Quantas dezenas a estratégia retorna (11-15)."""
        ...

    @property
    def abordagens_suportadas(self) -> tuple[str, ...]:
        """Identificadores das abordagens (ex.: ('statistical', 'ml', 'neural', 'todas'))."""
        ...

    def predict(
        self,
        sorteios: Sequence[Sorteio],
        abordagem: str = "todas",
    ) -> Predicao:
        """Gera uma predição para o próximo concurso após o último em ``sorteios``."""
        ...

    def predict_batch(
        self,
        sorteios: Sequence[Sorteio],
        abordagem: str = "todas",
    ) -> list[Predicao]:
        """Gera predições para múltiplos pontos no histórico (usado em backtest)."""
        ...
```

- [ ] **Passo 5:** Testes passam

```bash
pytest tests/test_dominio_estrategia.py -v
```

- [ ] **Passo 6:** Suite

```bash
pytest
```

- [ ] **Passo 7:** Commit

```bash
git add src/lotofacil/dominio/estrategia.py tests/test_dominio_estrategia.py
git commit -m "feat(dominio): adiciona Protocol EstrategiaBase

Substitui src/strategies/base.py (ABC). Protocol permite duck typing —
estratégias não precisam herdar, apenas implementar o contrato.

API expõe: nome, total_dezenas, abordagens_suportadas, predict, predict_batch.
Estratégias concretas serão movidas para lotofacil.infra.estrategias.<N>_dezenas
na onda 3 task 05."
```
