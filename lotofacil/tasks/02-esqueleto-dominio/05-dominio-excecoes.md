# Task 2.5 — `dominio/excecoes.py` — árvore de exceções

**Onda:** 2 — Esqueleto + domínio
**Prioridade:** alta
**Tempo estimado:** ~10 min
**Depende de:** 2.4

## Objetivo

Definir a árvore de exceções de domínio. CLI vai capturar `LotofacilError` no topo e formatar; exceções inesperadas (`TypeError`, `IOError`, etc.) propagam com stack trace para facilitar debug.

## Descrição técnica

Substitui o uso espalhado de `console.print("[red]erro...[/red]")` + `raise typer.Exit(1)` por levantamento de exceções tipadas. Cada erro de regra de negócio é uma subclasse de `LotofacilError`.

## Arquivos envolvidos

**Criar:**
- `src/lotofacil/dominio/excecoes.py`
- `tests/test_dominio_excecoes.py`

## Dependências

- 2.4

## Critérios de aceite

- [ ] `from lotofacil.dominio.excecoes import LotofacilError, SorteioNaoEncontrado, ModeloNaoTreinado, BaseDesatualizada, EstrategiaInvalida` funciona
- [ ] Cada subclasse herda de `LotofacilError`
- [ ] Cada exceção carrega contexto útil no `__init__` (ex: concurso, abordagem)
- [ ] Testes passam

## Passos detalhados

- [ ] **Passo 1:** Escrever testes

`tests/test_dominio_excecoes.py`:

```python
"""Testes da árvore de exceções de domínio."""
import pytest

from lotofacil.dominio.excecoes import (
    LotofacilError,
    SorteioNaoEncontrado,
    ModeloNaoTreinado,
    BaseDesatualizada,
    EstrategiaInvalida,
)


def test_lotofacil_error_e_exception():
    assert issubclass(LotofacilError, Exception)


def test_subclasses_herdam_de_lotofacil_error():
    for cls in (SorteioNaoEncontrado, ModeloNaoTreinado, BaseDesatualizada, EstrategiaInvalida):
        assert issubclass(cls, LotofacilError), f"{cls.__name__} deve herdar de LotofacilError"


def test_sorteio_nao_encontrado_carrega_concurso():
    e = SorteioNaoEncontrado(concurso=9999)
    assert e.concurso == 9999
    assert "9999" in str(e)


def test_modelo_nao_treinado_carrega_nome():
    e = ModeloNaoTreinado(modelo="LSTM")
    assert e.modelo == "LSTM"
    assert "LSTM" in str(e)


def test_base_desatualizada_carrega_diferenca():
    e = BaseDesatualizada(local=3680, remoto=3685)
    assert e.local == 3680
    assert e.remoto == 3685
    assert "3680" in str(e) and "3685" in str(e)


def test_estrategia_invalida_carrega_nome():
    e = EstrategiaInvalida(nome="strategy_x")
    assert e.nome == "strategy_x"
    assert "strategy_x" in str(e)


def test_pode_capturar_subtipo_via_lotofacil_error():
    with pytest.raises(LotofacilError):
        raise SorteioNaoEncontrado(concurso=1)
```

- [ ] **Passo 2:** Rodar testes (FALHA)

- [ ] **Passo 3:** Implementar `src/lotofacil/dominio/excecoes.py`

```python
"""Árvore de exceções do domínio Lotofácil.

A CLI captura LotofacilError no topo e formata humanamente.
Exceções desconhecidas (TypeError, IOError, etc.) propagam com stack trace
para facilitar debug.
"""
from __future__ import annotations


class LotofacilError(Exception):
    """Erro de regra de negócio do domínio Lotofácil."""


class SorteioNaoEncontrado(LotofacilError):
    """Sorteio solicitado não existe na base local."""

    def __init__(self, concurso: int) -> None:
        self.concurso = concurso
        super().__init__(f"Sorteio do concurso {concurso} não encontrado na base local.")


class ModeloNaoTreinado(LotofacilError):
    """Tentativa de predição com modelo que ainda não foi treinado."""

    def __init__(self, modelo: str) -> None:
        self.modelo = modelo
        super().__init__(f"Modelo '{modelo}' não foi treinado. Execute `lotofacil modelo treinar` primeiro.")


class BaseDesatualizada(LotofacilError):
    """Base local está atrás da API por mais de N concursos."""

    def __init__(self, local: int, remoto: int) -> None:
        self.local = local
        self.remoto = remoto
        super().__init__(f"Base local no concurso {local}, remoto disponível até {remoto}. Execute `lotofacil dados atualizar`.")


class EstrategiaInvalida(LotofacilError):
    """Estratégia solicitada não está registrada."""

    def __init__(self, nome: str) -> None:
        self.nome = nome
        super().__init__(f"Estratégia '{nome}' não está registrada.")
```

- [ ] **Passo 4:** Testes passam

```bash
pytest tests/test_dominio_excecoes.py -v
```

- [ ] **Passo 5:** Suite

```bash
pytest
```

- [ ] **Passo 6:** Commit

```bash
git add src/lotofacil/dominio/excecoes.py tests/test_dominio_excecoes.py
git commit -m "feat(dominio): adiciona árvore de exceções LotofacilError

Substitui o uso espalhado de console.print(erro) + typer.Exit(1) por
exceções tipadas. CLI captura LotofacilError no topo.

Subtipos: SorteioNaoEncontrado, ModeloNaoTreinado, BaseDesatualizada,
EstrategiaInvalida. Cada um carrega contexto estruturado."
```
