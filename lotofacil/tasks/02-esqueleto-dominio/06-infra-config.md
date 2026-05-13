# Task 2.6 — `infra/config.py` — paths globais

**Onda:** 2 — Esqueleto + domínio
**Prioridade:** alta
**Tempo estimado:** ~10 min
**Depende de:** 2.5

## Objetivo

Centralizar todos os paths do projeto em um único módulo `infra/config.py`. Substitui (na onda 3) `src/lotofacil_ml/config.py` e os `Path(__file__).resolve().parent.parent.parent / "dados"` espalhados.

Inicialmente aponta para as estruturas físicas ATUAIS (`data/`, `output/`, `saida/`). Na onda 7 esses paths mudam quando consolidamos para `dados/` e `saida/` únicos.

## Descrição técnica

`infra/config.py` expõe:

- `PROJETO_RAIZ` — calculado via `Path(__file__).resolve().parents[N]`
- Paths de entrada: `DADOS_DIR`, `CONCURSOS_DIR`, `PROCESSADO_DIR`, `DB_PATH`
- Paths de saída: `SAIDA_DIR`, `JOGOS_DIR`, `PREDICOES_DIR`, `MODELOS_DIR`, `RELATORIOS_DIR`, `EXPERIMENTOS_SAIDA_DIR`, `LOGS_DIR`
- Função utilitária: `garantir_diretorio(path)`

## Arquivos envolvidos

**Criar:**
- `src/lotofacil/infra/config.py`
- `tests/test_infra_config.py`

## Dependências

- 2.1 (estrutura `infra/` existe)

## Critérios de aceite

- [ ] `from lotofacil.infra.config import DADOS_DIR, SAIDA_DIR, DB_PATH` funciona
- [ ] Todos os paths são `pathlib.Path`
- [ ] `PROJETO_RAIZ` resolve corretamente (deve apontar para `lotofacil/`, não `lotofacil/src/`)
- [ ] `garantir_diretorio(p)` cria diretório sem erro se já existe
- [ ] Testes passam

## Passos detalhados

- [ ] **Passo 1:** Verificar profundidade do arquivo

```bash
# src/lotofacil/infra/config.py → 3 níveis abaixo de lotofacil/
# Path(__file__).resolve().parents[3] = lotofacil/
realpath src/lotofacil/infra/  # confirmar nível
```

- [ ] **Passo 2:** Escrever testes

`tests/test_infra_config.py`:

```python
"""Testes do módulo infra/config.py — paths globais."""
from pathlib import Path

from lotofacil.infra.config import (
    PROJETO_RAIZ,
    DADOS_DIR,
    SAIDA_DIR,
    DB_PATH,
    CONCURSOS_DIR,
    JOGOS_DIR,
    PREDICOES_DIR,
    MODELOS_DIR,
    RELATORIOS_DIR,
    LOGS_DIR,
    garantir_diretorio,
)


def test_projeto_raiz_aponta_para_lotofacil():
    # lotofacil/ deve conter pyproject.toml e src/
    assert (PROJETO_RAIZ / "pyproject.toml").exists()
    assert (PROJETO_RAIZ / "src").is_dir()


def test_todos_os_paths_sao_pathlib_path():
    for p in (DADOS_DIR, SAIDA_DIR, DB_PATH, CONCURSOS_DIR, JOGOS_DIR,
              PREDICOES_DIR, MODELOS_DIR, RELATORIOS_DIR, LOGS_DIR):
        assert isinstance(p, Path), f"{p} deve ser pathlib.Path"


def test_dados_dir_dentro_de_projeto_raiz():
    assert DADOS_DIR.parent == PROJETO_RAIZ or PROJETO_RAIZ in DADOS_DIR.parents


def test_saida_dir_dentro_de_projeto_raiz():
    assert SAIDA_DIR.parent == PROJETO_RAIZ


def test_garantir_diretorio_idempotente(tmp_path):
    novo = tmp_path / "subdir"
    assert not novo.exists()
    garantir_diretorio(novo)
    assert novo.is_dir()
    # idempotente
    garantir_diretorio(novo)
    assert novo.is_dir()
```

- [ ] **Passo 3:** Rodar testes (FALHA)

- [ ] **Passo 4:** Implementar `src/lotofacil/infra/config.py`

```python
"""Paths globais do projeto Lotofácil.

Single source of truth para localização de dados, saídas e artefatos.
Todos os módulos de infra, servicos e interface DEVEM usar estes paths
em vez de construir caminhos próprios.

Após a onda 7, todos os paths apontarão para `dados/` (input) e `saida/`
(output) consolidados; antes disso, alguns ainda apontam para `data/` e
`output/` legados.
"""
from __future__ import annotations

from pathlib import Path

# src/lotofacil/infra/config.py → parents[3] = lotofacil/ (root)
PROJETO_RAIZ: Path = Path(__file__).resolve().parents[3]

# === Entradas (inputs) ===

DADOS_DIR: Path = PROJETO_RAIZ / "dados"
CONCURSOS_DIR: Path = DADOS_DIR / "concursos"
PROCESSADO_DIR: Path = DADOS_DIR / "processado"
DB_PATH: Path = DADOS_DIR / "lotofacil.db"

# === Saídas (outputs) ===

SAIDA_DIR: Path = PROJETO_RAIZ / "saida"
JOGOS_DIR: Path = SAIDA_DIR / "jogos"
PREDICOES_DIR: Path = SAIDA_DIR / "predicoes"
MODELOS_DIR: Path = SAIDA_DIR / "modelos"
RELATORIOS_DIR: Path = SAIDA_DIR / "relatorios"
EXPERIMENTOS_SAIDA_DIR: Path = SAIDA_DIR / "experimentos"
LOGS_DIR: Path = SAIDA_DIR / "logs"


def garantir_diretorio(path: Path) -> Path:
    """Garante que o diretório existe (cria se necessário). Idempotente."""
    path.mkdir(parents=True, exist_ok=True)
    return path
```

- [ ] **Passo 5:** Testes passam

```bash
pytest tests/test_infra_config.py -v
```

- [ ] **Passo 6:** Suite

```bash
pytest
```

- [ ] **Passo 7:** Validar PROJETO_RAIZ manualmente

```bash
python -c "from lotofacil.infra.config import PROJETO_RAIZ, DADOS_DIR; print(PROJETO_RAIZ); print(DADOS_DIR)"
```

Esperado: imprime `.../loteria/lotofacil` e `.../loteria/lotofacil/dados`.

- [ ] **Passo 8:** Commit

```bash
git add src/lotofacil/infra/config.py tests/test_infra_config.py
git commit -m "feat(infra): adiciona config.py — paths globais consolidados

Single source of truth para todos os paths do projeto. Substitui na onda 3:
- src/lotofacil_ml/config.py (paths)
- Path(__file__).resolve().parent.parent.parent / 'dados' espalhados

Função garantir_diretorio() para criação idempotente.

Paths apontam para estrutura final (dados/ + saida/); ondas 3 e 7
atualizam consumidores e movem conteúdo físico."
```

Última task da onda 2. Próxima onda: migrar a infra canônica.
