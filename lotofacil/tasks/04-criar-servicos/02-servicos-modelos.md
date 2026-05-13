# Task 4.2 — Serviços de modelos: treinar_modelos + rodar_backtest

**Onda:** 4 — Criar `servicos/`
**Prioridade:** alta
**Tempo estimado:** ~35 min
**Depende de:** 4.1

## Objetivo

Extrair a lógica de `lotofacil modelo treinar` e `lotofacil modelo backtest` para serviços. CLI vira thin wrapper na task 4.6.

## Descrição técnica

`treinar_modelos` orquestra: carregar sorteios → gerar atributos → instanciar modelos → fit → salvar `.keras`/`.joblib`.

`rodar_backtest` orquestra: carregar sorteios → split temporal → walk-forward → métricas → relatório.

## Arquivos envolvidos

**Criar:**
- `src/lotofacil/servicos/treinar_modelos.py`
- `src/lotofacil/servicos/rodar_backtest.py`
- `tests/test_servicos_modelos.py`

## Dependências

- 4.1 (padrão de serviços estabelecido)

## Critérios de aceite

- [ ] `from lotofacil.servicos.treinar_modelos import treinar_modelos, ResultadoTreinamento` funciona
- [ ] `from lotofacil.servicos.rodar_backtest import rodar_backtest, ResultadoBacktest` funciona
- [ ] Testes passam (com fakes para banco, atributos, modelos)
- [ ] Comportamento idêntico ao `cli/modelo.py treinar/backtest` atual

## Passos detalhados

- [ ] **Passo 1:** Escrever testes

`tests/test_servicos_modelos.py`:

```python
"""Testes dos serviços de modelos."""
from unittest.mock import MagicMock
from pathlib import Path

import pytest

from lotofacil.servicos.treinar_modelos import treinar_modelos, ResultadoTreinamento
from lotofacil.servicos.rodar_backtest import rodar_backtest, ResultadoBacktest


class TestTreinarModelos:
    def test_treina_todos_modelos_por_padrao(self, monkeypatch, tmp_path):
        # Mock infra.dados
        banco_mock = MagicMock()
        banco_mock.carregar_sorteios.return_value = [MagicMock()] * 100

        # Mock atributos
        atributos_mock = MagicMock()
        atributos_mock.construir.return_value = (MagicMock(), MagicMock())  # X, y

        # Mock modelos
        modelo_mock = MagicMock()
        modelo_mock.salvar.return_value = tmp_path / "modelo.joblib"

        monkeypatch.setattr("lotofacil.servicos.treinar_modelos.DatabaseManager", lambda *_: banco_mock)
        monkeypatch.setattr("lotofacil.servicos.treinar_modelos.ConstrutorAtributos", lambda: atributos_mock)
        monkeypatch.setattr("lotofacil.servicos.treinar_modelos.ModeloFrequencia", lambda: modelo_mock)
        monkeypatch.setattr("lotofacil.servicos.treinar_modelos.ModeloEnsembleML", lambda: modelo_mock)
        monkeypatch.setattr("lotofacil.servicos.treinar_modelos.MODELOS_DIR", tmp_path)

        resultado = treinar_modelos()
        assert isinstance(resultado, ResultadoTreinamento)
        assert len(resultado.modelos_salvos) >= 1


class TestRodarBacktest:
    def test_executa_walk_forward(self, monkeypatch):
        banco_mock = MagicMock()
        banco_mock.carregar_sorteios.return_value = [MagicMock()] * 200

        validator_mock = MagicMock()
        validator_mock.executar.return_value = {"acerto_medio": 8.5, "janelas": []}

        monkeypatch.setattr("lotofacil.servicos.rodar_backtest.DatabaseManager", lambda *_: banco_mock)
        monkeypatch.setattr("lotofacil.servicos.rodar_backtest.WalkForwardValidator", lambda **_: validator_mock)

        resultado = rodar_backtest(estrategia_nome="onze_dezenas", janela=50)
        assert isinstance(resultado, ResultadoBacktest)
        assert resultado.acerto_medio == 8.5
```

- [ ] **Passo 2:** Rodar testes (FALHA)

- [ ] **Passo 3:** Implementar `src/lotofacil/servicos/treinar_modelos.py`

```python
"""Serviço: treina os modelos (Frequência + Ensemble ML + LSTM)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from lotofacil.infra.atributos import ConstrutorAtributos
from lotofacil.infra.config import DB_PATH, MODELOS_DIR, garantir_diretorio
from lotofacil.infra.dados import DatabaseManager
from lotofacil.infra.modelos import (
    ModeloFrequencia,
    ModeloEnsembleML,
    LSTMModel,
    PreditorEnsemble,
)


@dataclass(frozen=True)
class ResultadoTreinamento:
    modelos_salvos: dict[str, Path]
    metricas_finais: dict[str, float] = field(default_factory=dict)


def treinar_modelos(modelos: Optional[list[str]] = None) -> ResultadoTreinamento:
    """Treina os modelos selecionados (padrão: todos disponíveis).

    Args:
        modelos: lista de nomes ("frequencia", "ensemble_ml", "lstm");
                 None significa todos disponíveis.
    """
    garantir_diretorio(MODELOS_DIR)
    banco = DatabaseManager(DB_PATH)
    sorteios = banco.carregar_sorteios()

    atributos = ConstrutorAtributos()
    X, y = atributos.construir(sorteios)

    selecao = modelos or ["frequencia", "ensemble_ml"] + (["lstm"] if LSTMModel else [])
    salvos: dict[str, Path] = {}
    metricas: dict[str, float] = {}

    for nome in selecao:
        if nome == "frequencia":
            modelo = ModeloFrequencia()
        elif nome == "ensemble_ml":
            modelo = ModeloEnsembleML()
        elif nome == "lstm":
            if LSTMModel is None:
                continue  # TF não instalado
            modelo = LSTMModel()
        else:
            continue

        modelo.fit(X, y)
        caminho = modelo.salvar(MODELOS_DIR)
        salvos[nome] = caminho

    return ResultadoTreinamento(modelos_salvos=salvos, metricas_finais=metricas)
```

> **Nota:** API real de `Modelo.fit()` e `Modelo.salvar()` está em `infra/modelos/`. Ajustar conforme implementação efetiva pós-onda 3.

- [ ] **Passo 4:** Implementar `src/lotofacil/servicos/rodar_backtest.py`

```python
"""Serviço: roda backtest walk-forward de uma estratégia."""
from __future__ import annotations

from dataclasses import dataclass

from lotofacil.dominio.excecoes import EstrategiaInvalida
from lotofacil.infra.avaliacao import WalkForwardValidator
from lotofacil.infra.config import DB_PATH
from lotofacil.infra.dados import DatabaseManager


@dataclass(frozen=True)
class ResultadoBacktest:
    estrategia: str
    acerto_medio: float
    janelas: list[dict]
    relatorio_path: str | None = None


def rodar_backtest(
    estrategia_nome: str = "onze_dezenas",
    janela: int = 50,
    abordagem: str = "todas",
) -> ResultadoBacktest:
    """Roda backtest walk-forward de uma estratégia.

    Args:
        estrategia_nome: 'onze_dezenas', 'doze_dezenas', etc.
        janela: tamanho da janela de treino.
        abordagem: 'statistical', 'ml', 'neural', 'todas'.
    """
    estrategias_validas = {"onze_dezenas", "doze_dezenas", "treze_dezenas", "quatorze_dezenas", "quinze_dezenas"}
    if estrategia_nome not in estrategias_validas:
        raise EstrategiaInvalida(nome=estrategia_nome)

    banco = DatabaseManager(DB_PATH)
    sorteios = banco.carregar_sorteios()

    validator = WalkForwardValidator(janela=janela)
    relatorio = validator.executar(sorteios, estrategia_nome=estrategia_nome, abordagem=abordagem)

    return ResultadoBacktest(
        estrategia=estrategia_nome,
        acerto_medio=relatorio.get("acerto_medio", 0.0),
        janelas=relatorio.get("janelas", []),
        relatorio_path=relatorio.get("path"),
    )
```

- [ ] **Passo 5:** Testes passam

```bash
pytest tests/test_servicos_modelos.py -v
```

- [ ] **Passo 6:** Suite

```bash
pytest
```

- [ ] **Passo 7:** Commit

```bash
git add src/lotofacil/servicos/treinar_modelos.py src/lotofacil/servicos/rodar_backtest.py tests/test_servicos_modelos.py
git commit -m "feat(servicos): treinar_modelos + rodar_backtest

Extrai a orquestração de ML de cli/modelo.py:
- treinar_modelos(modelos) → ResultadoTreinamento
- rodar_backtest(estrategia, janela, abordagem) → ResultadoBacktest

Ambos chamam infra (atributos, modelos, avaliacao) e retornam dataclass
frozen. Sem efeitos colaterais de UI."
```
