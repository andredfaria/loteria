# Task 4.5 — Serviços de listagem: jogos + modelos

**Onda:** 4 — Criar `servicos/`
**Prioridade:** alta
**Tempo estimado:** ~25 min
**Depende de:** 4.4

## Objetivo

Extrair lógica de listagem de arquivos do painel (`/api/games`, `/api/games/:f`, `/api/models/status`) para serviços que tanto o painel quanto a CLI (futura) podem consumir.

Hoje `src/dashboard/server.py` tem `_list_game_files()` e `_scan_models()`. Vão para `lotofacil.servicos.*`.

## Arquivos envolvidos

**Criar:**
- `src/lotofacil/servicos/listar_jogos_gerados.py`
- `src/lotofacil/servicos/listar_modelos_treinados.py`
- `tests/test_servicos_listagem.py`

## Dependências

- 4.4

## Critérios de aceite

- [ ] 2 serviços importáveis
- [ ] `listar_jogos_gerados(limite, filename)` retorna lista ou conteúdo
- [ ] `listar_modelos_treinados()` retorna lista de `ModeloTreinado` com `nome`, `grupo` (core/lab), `tamanho_mb`, `treinado_em`, `epocas`, `val_loss`
- [ ] Sanitização de filename contra path traversal preservada (`Path(filename).name`)
- [ ] Testes passam

## Passos detalhados

- [ ] **Passo 1:** Inspecionar funções atuais em dashboard/server

```bash
grep -A 30 "_list_game_files\|_scan_models" src/dashboard/server.py | head -100
```

- [ ] **Passo 2:** Implementar `src/lotofacil/servicos/listar_jogos_gerados.py`

```python
"""Serviço: lista arquivos de jogos gerados em saida/jogos/."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from lotofacil.infra.config import JOGOS_DIR


@dataclass(frozen=True)
class JogoArquivo:
    filename: str
    concurso: Optional[str]
    size: int
    mtime: str  # ISO 8601


def listar_jogos_gerados(
    limite: int = 20,
    filename: Optional[str] = None,
) -> Union[list[JogoArquivo], dict]:
    """Lista arquivos em saida/jogos/ ou retorna conteúdo de um arquivo específico.

    Se ``filename`` é passado, retorna o conteúdo JSON desse arquivo (apenas).
    Caso contrário, retorna lista dos ``limite`` arquivos mais recentes.

    Sanitização contra path traversal: usa ``Path(filename).name``.
    """
    if not JOGOS_DIR.exists():
        return [] if filename is None else {}

    if filename is not None:
        nome_seguro = Path(filename).name  # remove diretórios
        caminho = JOGOS_DIR / nome_seguro
        if not caminho.exists():
            return {}
        return json.loads(caminho.read_text(encoding="utf-8"))

    arquivos = sorted(JOGOS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limite]
    resultado = []
    for arq in arquivos:
        st = arq.stat()
        nome = arq.stem
        # Extrair concurso do nome (ex.: portfolio_3681 → "3681", predicao_ml_3682 → "3682")
        partes = nome.split("_")
        concurso = partes[-1] if partes[-1].isdigit() else None
        resultado.append(JogoArquivo(
            filename=arq.name,
            concurso=concurso,
            size=st.st_size,
            mtime=datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        ))
    return resultado
```

- [ ] **Passo 3:** Implementar `src/lotofacil/servicos/listar_modelos_treinados.py`

```python
"""Serviço: lista modelos treinados (core + lab)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from lotofacil.infra.config import MODELOS_DIR, EXPERIMENTOS_SAIDA_DIR


@dataclass(frozen=True)
class ModeloTreinado:
    nome: str
    grupo: str  # 'core' ou 'lab'
    tamanho_mb: float
    treinado_em: Optional[str] = None
    epocas: Optional[int] = None
    val_loss_final: Optional[float] = None
    config: Optional[dict] = None


def listar_modelos_treinados() -> list[ModeloTreinado]:
    """Lista todos os arquivos .keras/.joblib em modelos/ (core) e experimentos/modelos/ (lab)."""
    resultado: list[ModeloTreinado] = []

    for grupo, base in [
        ("core", MODELOS_DIR),
        ("lab", EXPERIMENTOS_SAIDA_DIR / "modelos"),
    ]:
        if not base.exists():
            continue
        for arq in sorted(base.glob("*.keras")) + sorted(base.glob("*.joblib")):
            st = arq.stat()
            meta = {}
            arq_meta = arq.with_suffix(".meta.json")
            if arq_meta.exists():
                try:
                    meta = json.loads(arq_meta.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass
            resultado.append(ModeloTreinado(
                nome=arq.name,
                grupo=grupo,
                tamanho_mb=round(st.st_size / 1024 / 1024, 1),
                treinado_em=datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                epocas=meta.get("epocas") or meta.get("epochs_trained"),
                val_loss_final=meta.get("val_loss_final"),
                config=meta.get("config"),
            ))

    return resultado
```

- [ ] **Passo 4:** Escrever testes

`tests/test_servicos_listagem.py`:

```python
"""Testes dos serviços de listagem."""
import json

import pytest

from lotofacil.servicos.listar_jogos_gerados import listar_jogos_gerados, JogoArquivo
from lotofacil.servicos.listar_modelos_treinados import listar_modelos_treinados, ModeloTreinado


def test_listar_jogos_vazio(monkeypatch, tmp_path):
    monkeypatch.setattr("lotofacil.servicos.listar_jogos_gerados.JOGOS_DIR", tmp_path)
    assert listar_jogos_gerados() == []


def test_listar_jogos_com_arquivos(monkeypatch, tmp_path):
    monkeypatch.setattr("lotofacil.servicos.listar_jogos_gerados.JOGOS_DIR", tmp_path)
    (tmp_path / "portfolio_3681.json").write_text(json.dumps({"jogos": []}))
    (tmp_path / "predicao_ml_3682.json").write_text(json.dumps({"dezenas": []}))

    resultado = listar_jogos_gerados()
    assert len(resultado) == 2
    assert all(isinstance(j, JogoArquivo) for j in resultado)


def test_listar_jogos_path_traversal_bloqueado(monkeypatch, tmp_path):
    monkeypatch.setattr("lotofacil.servicos.listar_jogos_gerados.JOGOS_DIR", tmp_path)
    # Tentativa de path traversal
    resultado = listar_jogos_gerados(filename="../../../etc/passwd")
    # Deve retornar dict vazio (arquivo "passwd" não existe em tmp_path)
    assert resultado == {}


def test_listar_modelos_vazio(monkeypatch, tmp_path):
    monkeypatch.setattr("lotofacil.servicos.listar_modelos_treinados.MODELOS_DIR", tmp_path)
    monkeypatch.setattr("lotofacil.servicos.listar_modelos_treinados.EXPERIMENTOS_SAIDA_DIR", tmp_path / "exp")
    assert listar_modelos_treinados() == []


def test_listar_modelos_com_keras_e_meta(monkeypatch, tmp_path):
    modelos_dir = tmp_path / "modelos"
    modelos_dir.mkdir()
    (modelos_dir / "lstm.keras").write_bytes(b"\x00" * 1024)
    (modelos_dir / "lstm.meta.json").write_text(json.dumps({"epocas": 80, "val_loss_final": 0.23}))

    monkeypatch.setattr("lotofacil.servicos.listar_modelos_treinados.MODELOS_DIR", modelos_dir)
    monkeypatch.setattr("lotofacil.servicos.listar_modelos_treinados.EXPERIMENTOS_SAIDA_DIR", tmp_path / "exp")

    resultado = listar_modelos_treinados()
    assert len(resultado) == 1
    assert resultado[0].nome == "lstm.keras"
    assert resultado[0].grupo == "core"
    assert resultado[0].epocas == 80
    assert resultado[0].val_loss_final == 0.23
```

- [ ] **Passo 5:** Rodar testes

```bash
pytest tests/test_servicos_listagem.py -v
```

- [ ] **Passo 6:** Suite

```bash
pytest
```

- [ ] **Passo 7:** Commit

```bash
git add src/lotofacil/servicos/listar_jogos_gerados.py src/lotofacil/servicos/listar_modelos_treinados.py tests/test_servicos_listagem.py
git commit -m "feat(servicos): listar_jogos_gerados + listar_modelos_treinados

Extrai lógica de _list_game_files() e _scan_models() do
src/dashboard/server.py. Painel passa a chamar estes serviços na onda 5
task 03 (painel-usa-servicos).

Sanitização contra path traversal preservada via Path(filename).name."
```
