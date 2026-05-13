# Task 2.2 — `dominio/entidades.py` — Sorteio e Predicao

**Onda:** 2 — Esqueleto + domínio
**Prioridade:** alta
**Tempo estimado:** ~20 min
**Depende de:** 2.1

## Objetivo

Criar as entidades de domínio principais (`Sorteio`, `Predicao`, `Portfolio`) como dataclasses frozen. Adicionar aliases temporários (`Draw = Sorteio`, `Prediction = Predicao`) para manter o código antigo funcionando até a onda 8.

## Descrição técnica

`src/core/models.py` define hoje `Draw` (com `concurso`, `data`, `dezenas`, `dezenasOrdemSorteio`) e `Prediction`. Vamos:

1. Inspecionar `src/core/models.py` para captar o contrato exato
2. Recriar como `Sorteio` e `Predicao` em `dominio/entidades.py` com nomes PT
3. Adicionar aliases temporários
4. Escrever testes TDD para as entidades

## Arquivos envolvidos

**Criar:**
- `src/lotofacil/dominio/entidades.py`
- `tests/test_dominio_entidades.py` (provisório; vai para `testes/unidade/dominio/` na onda 8)

**Não tocar:**
- `src/core/models.py` (continua existindo; só será deletado na onda 5)

## Dependências

- 2.1 (estrutura criada)

## Critérios de aceite

- [ ] `from lotofacil.dominio.entidades import Sorteio, Predicao` funciona
- [ ] `from lotofacil.dominio.entidades import Draw, Prediction` funciona (aliases)
- [ ] `Sorteio` é `frozen=True` (imutável)
- [ ] `Sorteio.dezenas` retorna `tuple[int, ...]` ordenado
- [ ] Testes passam

## Passos detalhados

- [ ] **Passo 1:** Inspecionar `src/core/models.py`

```bash
cat src/core/models.py
```

Anotar campos exatos de `Draw` e `Prediction`. Confirmar se há métodos não-triviais.

- [ ] **Passo 2:** Escrever testes (TDD — falham antes da implementação)

`tests/test_dominio_entidades.py`:

```python
"""Testes das entidades de domínio (Sorteio, Predicao, Portfolio)."""
import pytest
from datetime import date

from lotofacil.dominio.entidades import Sorteio, Predicao, Portfolio


class TestSorteio:
    def test_cria_sorteio_basico(self):
        s = Sorteio(
            concurso=3681,
            data=date(2026, 5, 9),
            dezenas=(1, 2, 3, 5, 7, 11, 13, 14, 15, 17, 19, 20, 22, 23, 25),
        )
        assert s.concurso == 3681
        assert len(s.dezenas) == 15

    def test_sorteio_e_frozen(self):
        s = Sorteio(concurso=1, data=date.today(), dezenas=tuple(range(1, 16)))
        with pytest.raises(Exception):  # FrozenInstanceError
            s.concurso = 2  # type: ignore[misc]

    def test_dezenas_devem_estar_ordenadas(self):
        with pytest.raises(ValueError):
            Sorteio(concurso=1, data=date.today(), dezenas=(15, 14, 13, *range(1, 13)))

    def test_dezenas_devem_ter_15(self):
        with pytest.raises(ValueError):
            Sorteio(concurso=1, data=date.today(), dezenas=tuple(range(1, 15)))


class TestPredicao:
    def test_cria_predicao_basica(self):
        p = Predicao(
            concurso_alvo=3682,
            dezenas=(1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21),
            abordagem="ml",
            confianca_media=0.45,
        )
        assert p.concurso_alvo == 3682
        assert p.abordagem == "ml"

    def test_predicao_e_frozen(self):
        p = Predicao(concurso_alvo=1, dezenas=tuple(range(1, 12)), abordagem="ml", confianca_media=0.5)
        with pytest.raises(Exception):
            p.confianca_media = 0.9  # type: ignore[misc]


class TestAliasesTemporarios:
    def test_draw_e_alias_de_sorteio(self):
        from lotofacil.dominio.entidades import Draw, Sorteio
        assert Draw is Sorteio

    def test_prediction_e_alias_de_predicao(self):
        from lotofacil.dominio.entidades import Prediction, Predicao
        assert Prediction is Predicao
```

- [ ] **Passo 3:** Rodar testes (devem FALHAR — entidades ainda não existem)

```bash
pytest tests/test_dominio_entidades.py -v
```

Esperado: erros de import (`ImportError: cannot import name 'Sorteio'`).

- [ ] **Passo 4:** Implementar `src/lotofacil/dominio/entidades.py`

```python
"""Entidades de domínio da Lotofácil.

Estes tipos são puros: não dependem de IO, banco, ou framework. Toda
representação de dados que atravessa as camadas usa estas classes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Sorteio:
    """Um sorteio histórico da Lotofácil.

    Sempre 15 dezenas em [1, 25], em ordem crescente.
    """
    concurso: int
    data: date
    dezenas: tuple[int, ...]
    dezenas_ordem_sorteio: tuple[int, ...] = field(default=())

    def __post_init__(self) -> None:
        if len(self.dezenas) != 15:
            raise ValueError(f"Sorteio precisa de 15 dezenas, recebeu {len(self.dezenas)}")
        if list(self.dezenas) != sorted(self.dezenas):
            raise ValueError(f"Sorteio.dezenas deve estar ordenado crescente: {self.dezenas}")
        if any(d < 1 or d > 25 for d in self.dezenas):
            raise ValueError(f"Sorteio.dezenas fora do intervalo [1, 25]: {self.dezenas}")


@dataclass(frozen=True)
class Predicao:
    """Uma predição para um concurso futuro.

    `dezenas` pode ter 11–15 elementos, dependendo da estratégia.
    """
    concurso_alvo: int
    dezenas: tuple[int, ...]
    abordagem: str
    confianca_media: float
    explicacao: Optional[dict] = None


@dataclass(frozen=True)
class Portfolio:
    """Um conjunto de jogos para um concurso."""
    concurso_alvo: int
    jogos: tuple[tuple[int, ...], ...]
    estrategia: str
    metadados: dict = field(default_factory=dict)


# Aliases temporários — código antigo (cli/app.py, lotofacil_ml/, dashboard/)
# importa Draw e Prediction. Estes aliases permitem migração gradual.
# REMOVER NA ONDA 8 task 03 (depois que todos os usos migrarem).
Draw = Sorteio
Prediction = Predicao
```

- [ ] **Passo 5:** Rodar testes (devem PASSAR agora)

```bash
pytest tests/test_dominio_entidades.py -v
```

Esperado: 7 passing.

- [ ] **Passo 6:** Rodar suite completa para garantir que nada quebra

```bash
pytest
```

- [ ] **Passo 7:** Smoke

```bash
python -c "from lotofacil.dominio.entidades import Sorteio, Predicao, Draw, Prediction; print('OK')"
```

- [ ] **Passo 8:** Commit

```bash
git add src/lotofacil/dominio/entidades.py tests/test_dominio_entidades.py
git commit -m "feat(dominio): adiciona Sorteio, Predicao, Portfolio

Entidades de domínio puras (dataclass frozen, sem dependências de IO).
Validação no __post_init__ (ordenação, intervalo, contagem).

Aliases Draw=Sorteio, Prediction=Predicao mantêm o código antigo
funcionando até a onda 8 task 03 (remoção dos aliases)."
```
