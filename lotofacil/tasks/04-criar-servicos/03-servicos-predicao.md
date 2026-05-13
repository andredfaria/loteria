# Task 4.3 — Serviços de predição: gerar_predicao + validar + histórico

**Onda:** 4 — Criar `servicos/`
**Prioridade:** alta
**Tempo estimado:** ~35 min
**Depende de:** 4.2

## Objetivo

Extrair lógica de `lotofacil prever`, `lotofacil modelo validar`, `lotofacil modelo historico` para três serviços.

## Arquivos envolvidos

**Criar:**
- `src/lotofacil/servicos/gerar_predicao.py`
- `src/lotofacil/servicos/validar_predicoes.py`
- `src/lotofacil/servicos/listar_historico_predicoes.py`
- `tests/test_servicos_predicao.py`

## Dependências

- 4.2

## Critérios de aceite

- [ ] 3 serviços importáveis de `lotofacil.servicos.*`
- [ ] Cada um retorna dataclass frozen
- [ ] Testes passam

## Passos detalhados

- [ ] **Passo 1:** Escrever testes

`tests/test_servicos_predicao.py`:

```python
"""Testes dos serviços de predição."""
from datetime import date
from unittest.mock import MagicMock

import pytest

from lotofacil.dominio.entidades import Sorteio, Predicao
from lotofacil.servicos.gerar_predicao import gerar_predicao
from lotofacil.servicos.validar_predicoes import validar_predicoes, RelatorioValidacao
from lotofacil.servicos.listar_historico_predicoes import listar_historico_predicoes


class TestGerarPredicao:
    def test_retorna_predicao_para_proximo_concurso(self, monkeypatch):
        banco_mock = MagicMock()
        sorteio_atual = Sorteio(concurso=3681, data=date.today(), dezenas=tuple(range(1, 16)))
        banco_mock.carregar_sorteios.return_value = [sorteio_atual]

        estrategia_mock = MagicMock()
        estrategia_mock.predict.return_value = Predicao(
            concurso_alvo=3682,
            dezenas=tuple(range(1, 12)),
            abordagem="ml",
            confianca_media=0.5,
        )

        monkeypatch.setattr("lotofacil.servicos.gerar_predicao.DatabaseManager", lambda *_: banco_mock)
        monkeypatch.setattr("lotofacil.servicos.gerar_predicao.EstrategiaOnzeDezenas", lambda: estrategia_mock)

        pred = gerar_predicao(abordagem="ml")
        assert isinstance(pred, Predicao)
        assert pred.concurso_alvo == 3682


class TestValidarPredicoes:
    def test_compara_predicao_com_resultado_real(self, monkeypatch, tmp_path):
        # ... setup mocks de leitor de predições e sorteios
        # Validar que retorna RelatorioValidacao com acertos contados
        pass  # esqueleto — completar conforme infra de leitura de predições


class TestListarHistoricoPredicoes:
    def test_retorna_lista_ordenada_por_concurso_desc(self, monkeypatch, tmp_path):
        # Criar 3 arquivos predicao_*.json em tmp_path
        # Verificar que a função retorna lista ordenada desc
        pass
```

- [ ] **Passo 2:** Implementar `src/lotofacil/servicos/gerar_predicao.py`

```python
"""Serviço: gera predição para o próximo concurso."""
from __future__ import annotations

import json
from typing import Optional

from lotofacil.dominio.entidades import Predicao
from lotofacil.infra.config import DB_PATH, JOGOS_DIR, garantir_diretorio
from lotofacil.infra.dados import DatabaseManager
from lotofacil.infra.estrategias.onze_dezenas import EstrategiaOnzeDezenas


def gerar_predicao(
    abordagem: str = "todas",
    concurso_alvo: Optional[int] = None,
    persistir: bool = True,
) -> Predicao:
    """Gera uma predição para o próximo concurso (ou o especificado)."""
    banco = DatabaseManager(DB_PATH)
    sorteios = banco.carregar_sorteios()

    if not sorteios:
        raise RuntimeError("Sem sorteios na base. Execute `lotofacil dados atualizar`.")

    estrategia = EstrategiaOnzeDezenas()
    pred = estrategia.predict(sorteios, abordagem=abordagem)

    if persistir:
        garantir_diretorio(JOGOS_DIR)
        nome_arquivo = f"predicao_{abordagem.replace('todas', 'ensemble')}_{pred.concurso_alvo}.json"
        caminho = JOGOS_DIR / nome_arquivo
        caminho.write_text(
            json.dumps({
                "concurso": pred.concurso_alvo,
                "abordagem": pred.abordagem,
                "dezenas": sorted(pred.dezenas),
                "confianca": round(pred.confianca_media, 4),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return pred
```

- [ ] **Passo 3:** Implementar `src/lotofacil/servicos/validar_predicoes.py`

```python
"""Serviço: valida predições salvas contra sorteios reais."""
from __future__ import annotations

import json
from dataclasses import dataclass

from lotofacil.dominio.entidades import Sorteio
from lotofacil.infra.config import DB_PATH, JOGOS_DIR
from lotofacil.infra.dados import DatabaseManager


@dataclass(frozen=True)
class AcertoPredicao:
    concurso: int
    abordagem: str
    dezenas_preditas: tuple[int, ...]
    dezenas_sorteadas: tuple[int, ...]
    acertos: int


@dataclass(frozen=True)
class RelatorioValidacao:
    total_validadas: int
    acerto_medio: float
    detalhes: list[AcertoPredicao]


def validar_predicoes(concurso: int | None = None) -> RelatorioValidacao:
    """Valida predições já salvas em saida/jogos/predicao_*.json contra resultados reais."""
    banco = DatabaseManager(DB_PATH)
    detalhes: list[AcertoPredicao] = []

    arquivos = sorted(JOGOS_DIR.glob("predicao_*.json"))
    for arq in arquivos:
        dados = json.loads(arq.read_text(encoding="utf-8"))
        conc = dados["concurso"]
        if concurso is not None and conc != concurso:
            continue
        sorteio = banco.buscar_sorteio(conc)
        if sorteio is None:
            continue  # ainda não saiu
        preditas = tuple(sorted(dados["dezenas"]))
        sorteadas = sorteio.dezenas
        acertos = sum(1 for d in preditas if d in sorteadas)
        detalhes.append(AcertoPredicao(
            concurso=conc,
            abordagem=dados.get("abordagem", "?"),
            dezenas_preditas=preditas,
            dezenas_sorteadas=sorteadas,
            acertos=acertos,
        ))

    acerto_medio = sum(d.acertos for d in detalhes) / len(detalhes) if detalhes else 0.0
    return RelatorioValidacao(
        total_validadas=len(detalhes),
        acerto_medio=acerto_medio,
        detalhes=detalhes,
    )
```

- [ ] **Passo 4:** Implementar `src/lotofacil/servicos/listar_historico_predicoes.py`

```python
"""Serviço: lista histórico de predições agrupadas por concurso."""
from __future__ import annotations

import json
from dataclasses import dataclass

from lotofacil.infra.config import JOGOS_DIR


@dataclass(frozen=True)
class HistoricoConcurso:
    concurso: int
    abordagens: list[dict]
    mtime: str


def listar_historico_predicoes(limite: int = 20) -> list[HistoricoConcurso]:
    """Lista predições agrupadas por concurso, ordenadas por mtime desc."""
    grupos: dict[int, HistoricoConcurso] = {}

    if not JOGOS_DIR.exists():
        return []

    arquivos = sorted(JOGOS_DIR.glob("predicao_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for arq in arquivos:
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        conc = dados.get("concurso")
        if conc is None:
            continue
        if conc not in grupos:
            grupos[conc] = HistoricoConcurso(
                concurso=conc,
                abordagens=[],
                mtime=arq.stat().st_mtime,  # type: ignore
            )
        grupos[conc].abordagens.append({
            "abordagem": dados.get("abordagem", "?"),
            "dezenas": dados.get("dezenas", []),
            "confianca": dados.get("confianca"),
        })

    return sorted(grupos.values(), key=lambda g: g.concurso, reverse=True)[:limite]
```

- [ ] **Passo 5:** Rodar testes

```bash
pytest tests/test_servicos_predicao.py -v
```

- [ ] **Passo 6:** Suite

```bash
pytest
```

- [ ] **Passo 7:** Commit

```bash
git add src/lotofacil/servicos/gerar_predicao.py src/lotofacil/servicos/validar_predicoes.py src/lotofacil/servicos/listar_historico_predicoes.py tests/test_servicos_predicao.py
git commit -m "feat(servicos): gerar_predicao + validar_predicoes + listar_historico

Três serviços extraídos da CLI:
- gerar_predicao(abordagem, concurso_alvo, persistir) → Predicao
- validar_predicoes(concurso?) → RelatorioValidacao
- listar_historico_predicoes(limite) → list[HistoricoConcurso]

CLI continua chamando lógica antiga; refactor para serviços vem na task 4.6."
```
