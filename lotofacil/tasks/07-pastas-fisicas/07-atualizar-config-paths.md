# Task 7.7 — Atualizar paths em `infra/config.py` e referências

**Onda:** 7 — Pastas físicas
**Prioridade:** média
**Tempo estimado:** ~15 min
**Depende de:** 7.6

## Objetivo

Auditar `infra/config.py` e todo o código que usa paths: confirmar que tudo aponta para a estrutura `dados/` + `saida/` consolidada. Atualizar onde necessário. Documentar a convenção em docstring.

## Descrição técnica

`infra/config.py` foi criado na onda 2 com paths antecipando o estado final. As ondas 7.1-7.6 fisicamente moveram tudo. Esta task **verifica** e **cobre** quaisquer referências hardcoded perdidas.

## Arquivos envolvidos

**Modificar (potencialmente):**
- `src/lotofacil/infra/config.py` (revisar e documentar)
- Qualquer arquivo em `src/lotofacil/` com `Path` hardcoded apontando para `data/`, `output/`, `models_saved/`, etc.

## Dependências

- 7.6

## Critérios de aceite

- [ ] `grep -rn "data/raw\|data/processed\|output/models\|output/predictions\|output/reports\|models_saved\|saved_models\|lotofacil_lab/output" src/` retorna 0 ou só comentários
- [ ] `infra/config.py` exporta paths consolidados (lista completa abaixo)
- [ ] Todos os módulos usam `from lotofacil.infra.config import ...` em vez de calcular paths inline
- [ ] `pytest` passa
- [ ] Suite completa de smoke tests passa

## Estado final esperado de `infra/config.py`

```python
"""Paths globais do projeto Lotofácil — single source of truth.

Estrutura física:
  lotofacil/
    dados/              ← inputs (symlink para ~/lotofacil-dados/)
      concursos/        ← JSONs da CAIXA
      processado/       ← CSVs derivados
      lotofacil.db      ← SQLite
    saida/              ← outputs
      jogos/            ← portfolios + predições apostáveis
      predicoes/        ← relatórios de predição (confiança por dezena)
      modelos/          ← .keras / .joblib
      relatorios/       ← HTML, KPI, backtest reports
      experimentos/     ← outputs do lab
        modelos/        ← .keras do lab
      logs/             ← logs runtime

Todos os módulos da camada `infra`, `servicos`, `interface` e `experimentos`
DEVEM usar estas constantes ao invés de construir caminhos próprios.
"""
from __future__ import annotations

from pathlib import Path

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
    """Cria o diretório se não existe. Idempotente."""
    path.mkdir(parents=True, exist_ok=True)
    return path
```

## Passos detalhados

- [ ] **Passo 1:** Auditar refs hardcoded

```bash
grep -rn "data/raw\|data/processed\|output/models\|output/predictions\|output/reports\|models_saved\|saved_models\|lotofacil_lab/output" src/lotofacil/
```

Para cada resultado, decidir:
- Se está em comentário/docstring/string de log → ok, deixar
- Se é construção de Path → atualizar para usar constante de `infra/config.py`

- [ ] **Passo 2:** Atualizar `infra/config.py` com docstring completa (acima)

```bash
cat > src/lotofacil/infra/config.py <<'EOF'
"""Paths globais do projeto Lotofácil — single source of truth.
... (conteúdo acima)
EOF
```

- [ ] **Passo 3:** Verificar todos os módulos

```bash
grep -ln "PROJECT_ROOT\|PROJETO_RAIZ\|Path(__file__)" src/lotofacil/
```

Cada arquivo que calcula path inline deveria importar de `infra.config`.

- [ ] **Passo 4:** Validar

```bash
python -c "from lotofacil.infra.config import (
    DADOS_DIR, SAIDA_DIR, DB_PATH,
    CONCURSOS_DIR, PROCESSADO_DIR,
    JOGOS_DIR, PREDICOES_DIR, MODELOS_DIR, RELATORIOS_DIR,
    EXPERIMENTOS_SAIDA_DIR, LOGS_DIR,
    PROJETO_RAIZ, garantir_diretorio,
); print('All paths OK')"
```

- [ ] **Passo 5:** Smoke completo

```bash
lotofacil dados status
lotofacil prever
lotofacil portfolio --jogos 3
lotofacil modelo treinar  # ou erra DB vazio
lotofacil lab ablacao --n-test 5

lotofacil painel &
PID=$!
sleep 2
curl -s localhost:5000/api/status | jq .
curl -s localhost:5000/api/games | jq . | head -10
curl -s localhost:5000/api/models/status | jq . | head -20
kill $PID
```

- [ ] **Passo 6:** Testes

```bash
pytest
```

- [ ] **Passo 7:** Commit

```bash
git add -A
git commit -m "refactor(config): auditoria final de paths consolidados

infra/config.py documenta toda a estrutura física do projeto.
Refs hardcoded em src/lotofacil/ substituídas por constantes de
infra/config.py onde encontradas.

Última task da onda 7. dados/ + saida/ são as únicas raízes de
input/output do projeto."
```
