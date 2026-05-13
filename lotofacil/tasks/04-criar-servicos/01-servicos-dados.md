# Task 4.1 — Serviços de dados: atualizar_base + consultar_status_base

**Onda:** 4 — Criar `servicos/`
**Prioridade:** alta
**Tempo estimado:** ~30 min
**Depende de:** 3.5

## Objetivo

Extrair a lógica de orquestração dos comandos `lotofacil dados atualizar` e `lotofacil dados status` para serviços em `lotofacil.servicos.*`. CLI vira thin wrapper.

## Descrição técnica

Hoje a lógica vive **dentro** de `src/cli/dados.py` (handlers Typer fazem fetch + DB insert + formatação rich). Os serviços extraem o miolo (sem `console.print` / `typer.Exit`) e a CLI passa a chamá-los.

## Arquivos envolvidos

**Criar:**
- `src/lotofacil/servicos/atualizar_base.py`
- `src/lotofacil/servicos/consultar_status_base.py`
- `tests/test_servicos_dados.py`

**Modificar (na task 4.6, não aqui):**
- `src/cli/dados.py` — usar os serviços (depois que todos estiverem criados)

## Dependências

- 3.5 (infra/dados disponível)

## Critérios de aceite

- [ ] `from lotofacil.servicos.atualizar_base import atualizar_base, ResultadoAtualizacao` funciona
- [ ] `from lotofacil.servicos.consultar_status_base import consultar_status_base, StatusBase` funciona
- [ ] Serviços retornam dataclass frozen com resultado tipado
- [ ] Serviços NÃO chamam `console.print`, `typer.Exit`, nem capturam exceções genéricas
- [ ] Testes de unidade passam (usando fakes para API CAIXA e banco)

## Passos detalhados

- [ ] **Passo 1:** Escrever testes (TDD)

`tests/test_servicos_dados.py`:

```python
"""Testes dos serviços de dados (atualizar_base, consultar_status_base)."""
from datetime import date
from unittest.mock import MagicMock

import pytest

from lotofacil.dominio.entidades import Sorteio
from lotofacil.dominio.excecoes import BaseDesatualizada
from lotofacil.servicos.atualizar_base import atualizar_base, ResultadoAtualizacao
from lotofacil.servicos.consultar_status_base import consultar_status_base, StatusBase


class TestAtualizarBase:
    def test_atualiza_com_novos_sorteios(self, monkeypatch):
        sorteio_fake = Sorteio(
            concurso=3682,
            data=date(2026, 5, 10),
            dezenas=tuple(range(1, 16)),
        )
        coletor_mock = MagicMock()
        coletor_mock.buscar_pendentes.return_value = [sorteio_fake]
        banco_mock = MagicMock()
        banco_mock.ultimo_concurso.return_value = 3681
        banco_mock.inserir_sorteios.return_value = 1

        monkeypatch.setattr("lotofacil.servicos.atualizar_base.ColetorAPI", lambda: coletor_mock)
        monkeypatch.setattr("lotofacil.servicos.atualizar_base.DatabaseManager", lambda *_: banco_mock)

        resultado = atualizar_base(escopo="novos")
        assert isinstance(resultado, ResultadoAtualizacao)
        assert resultado.total_novos == 1
        assert resultado.ultimo_concurso == 3682
        assert resultado.sorteios_adicionados == [sorteio_fake]

    def test_escopo_invalido_levanta_value_error(self):
        with pytest.raises(ValueError):
            atualizar_base(escopo="banana")  # type: ignore[arg-type]


class TestConsultarStatusBase:
    def test_retorna_status_com_total(self, monkeypatch):
        banco_mock = MagicMock()
        banco_mock.total_sorteios.return_value = 3681
        banco_mock.ultimo_sorteio.return_value = Sorteio(
            concurso=3681, data=date(2026, 5, 9), dezenas=tuple(range(1, 16))
        )
        monkeypatch.setattr(
            "lotofacil.servicos.consultar_status_base.DatabaseManager", lambda *_: banco_mock
        )

        status = consultar_status_base()
        assert isinstance(status, StatusBase)
        assert status.total_sorteios == 3681
        assert status.ultimo_concurso == 3681
```

- [ ] **Passo 2:** Rodar testes (FALHA)

- [ ] **Passo 3:** Implementar `src/lotofacil/servicos/atualizar_base.py`

```python
"""Serviço: atualiza a base local de sorteios via API CAIXA."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lotofacil.dominio.entidades import Sorteio
from lotofacil.infra.config import DB_PATH
from lotofacil.infra.dados import ColetorAPI, DatabaseManager

Escopo = Literal["todos", "novos", "ultimo"]


@dataclass(frozen=True)
class ResultadoAtualizacao:
    total_novos: int
    ultimo_concurso: int
    sorteios_adicionados: list[Sorteio]


def atualizar_base(escopo: Escopo = "novos") -> ResultadoAtualizacao:
    """Sincroniza a base local com a API CAIXA.

    Args:
        escopo: "todos" (re-importa histórico), "novos" (só os faltantes),
                "ultimo" (apenas o sorteio mais recente).

    Returns:
        ResultadoAtualizacao com contagem e último concurso.
    """
    if escopo not in ("todos", "novos", "ultimo"):
        raise ValueError(f"Escopo inválido: {escopo}. Use 'todos', 'novos' ou 'ultimo'.")

    coletor = ColetorAPI()
    banco = DatabaseManager(DB_PATH)

    if escopo == "todos":
        novos = coletor.buscar_todos()
    elif escopo == "ultimo":
        novos = [coletor.buscar_ultimo()]
    else:  # novos
        ultimo_local = banco.ultimo_concurso()
        novos = coletor.buscar_pendentes(desde=ultimo_local)

    banco.inserir_sorteios(novos)
    ultimo_apos = max((s.concurso for s in novos), default=banco.ultimo_concurso())

    return ResultadoAtualizacao(
        total_novos=len(novos),
        ultimo_concurso=ultimo_apos,
        sorteios_adicionados=novos,
    )
```

> **Nota:** os métodos `buscar_todos()`, `buscar_pendentes()`, `buscar_ultimo()` do `ColetorAPI` provavelmente já existem com nomes EN (`fetch_all`, etc.). Ajuste conforme o que está em `infra/dados/api_caixa.py` após a onda 3.

- [ ] **Passo 4:** Implementar `src/lotofacil/servicos/consultar_status_base.py`

```python
"""Serviço: consulta status da base local de sorteios."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from lotofacil.infra.config import DB_PATH
from lotofacil.infra.dados import DatabaseManager


@dataclass(frozen=True)
class StatusBase:
    total_sorteios: int
    ultimo_concurso: Optional[int]
    ultimo_data: Optional[date]


def consultar_status_base() -> StatusBase:
    """Retorna métricas básicas da base local."""
    banco = DatabaseManager(DB_PATH)
    total = banco.total_sorteios()
    ultimo = banco.ultimo_sorteio()

    return StatusBase(
        total_sorteios=total,
        ultimo_concurso=ultimo.concurso if ultimo else None,
        ultimo_data=ultimo.data if ultimo else None,
    )
```

- [ ] **Passo 5:** Testes passam

```bash
pytest tests/test_servicos_dados.py -v
```

- [ ] **Passo 6:** Suite

```bash
pytest
```

- [ ] **Passo 7:** Commit

```bash
git add src/lotofacil/servicos/atualizar_base.py src/lotofacil/servicos/consultar_status_base.py tests/test_servicos_dados.py
git commit -m "feat(servicos): atualizar_base + consultar_status_base

Extrai lógica de orquestração de src/cli/dados.py:
- atualizar_base(escopo) → ResultadoAtualizacao
- consultar_status_base() → StatusBase

Funções tipadas, dataclass frozen, sem console.print/typer.Exit/sys.exit.
Domain exceptions (BaseDesatualizada, etc.) propagam — CLI captura no topo.

CLI ainda chama lógica antiga; refactor para usar serviços vem na task 4.6."
```
