# Task 3.1 — Mover `dados/` (fetcher, banco, leitor, preprocessador)

**Onda:** 3 — Migrar infra
**Prioridade:** alta
**Tempo estimado:** ~30 min
**Depende de:** 2.6

## Objetivo

Mover o canonical de acesso a dados — `src/lotofacil_ml/data/` — para `src/lotofacil/infra/dados/`. Renomear arquivos para PT. Trazer também o único arquivo de `src/data/` que é canônico (`preprocessor.py`). Atualizar todos os imports em `src/cli/*.py` no mesmo commit.

## Descrição técnica

`src/lotofacil_ml/data/` tem: `fetcher.py` (API CAIXA), `database.py` (SQLite), `loader.py` (sorteios), `preprocessor.py` (transformações).

`src/data/` tem versões mais antigas das mesmas coisas. Apenas `preprocessor.py` (no pacote `src/data/`) tem implementação canônica única, conforme spec 6.2.

## Arquivos envolvidos

**Mover (git mv):**

| De | Para |
|---|---|
| `src/lotofacil_ml/data/fetcher.py` | `src/lotofacil/infra/dados/api_caixa.py` |
| `src/lotofacil_ml/data/database.py` | `src/lotofacil/infra/dados/banco.py` |
| `src/lotofacil_ml/data/loader.py` | `src/lotofacil/infra/dados/leitor.py` |
| `src/lotofacil_ml/data/preprocessor.py` | `src/lotofacil/infra/dados/preprocessador.py` |
| `src/lotofacil_ml/data/__init__.py` | (mesclar com `src/lotofacil/infra/dados/__init__.py` já existente) |

**Renomear classes durante o move:**

| Antes | Depois |
|---|---|
| `LotofacilFetcher` | `ColetorAPI` |
| `DatabaseManager` | mantém (loanword) |
| `LotofacilPreprocessor` | `Preprocessador` |
| `load_draws` | `carregar_sorteios` |
| `load_draws_from_json` | `carregar_sorteios_de_json` |

**Modificar (atualizar imports):**

- `src/cli/dados.py` — atualizar `from lotofacil_ml.data.fetcher import LotofacilFetcher` → `from lotofacil.infra.dados.api_caixa import ColetorAPI`, etc.
- `src/cli/modelo.py` — atualizar todos os `from lotofacil_ml.data.*`
- `src/cli/portfolio.py` — atualizar
- `src/cli/app.py` — atualizar `from data.loader` → `from lotofacil.infra.dados.leitor`
- `src/dashboard/server.py` — atualizar se referenciar
- `src/lotofacil_ml/main.py`, `src/lotofacil_ml/scheduler/*` — atualizar imports internos (vão ser movidos depois, mas precisamos manter funcionando)
- `src/lotofacil_lab/*` — atualizar refs a `lotofacil_ml.data.*` (lab só será movido na onda 6)

**Deletar (resíduos órfãos):**
- `src/data/fetcher.py`, `src/data/loader.py`, `src/data/database.py` — eram duplicatas (vencedor é lotofacil_ml). Confirmar que nada importa.
- `src/data/climate_loader.py` — não é canônico aqui; move para experimentos na onda 6 (deixa por ora).

## Dependências

- 2.6 (`infra/config.py` existe)

## Critérios de aceite

- [ ] `from lotofacil.infra.dados.api_caixa import ColetorAPI` funciona
- [ ] `from lotofacil.infra.dados.banco import DatabaseManager` funciona
- [ ] `from lotofacil.infra.dados.leitor import carregar_sorteios` funciona
- [ ] `from lotofacil.infra.dados.preprocessador import Preprocessador` funciona
- [ ] `grep -rn "from lotofacil_ml.data\|from src.lotofacil_ml.data" src/cli/ src/dashboard/` retorna 0
- [ ] `lotofacil dados status` funciona
- [ ] `lotofacil dados atualizar --latest` funciona
- [ ] `pytest` passa

## Passos detalhados

- [ ] **Passo 1:** Verificar consumidores atuais

```bash
grep -rn "from lotofacil_ml.data\|from data\." src/ 2>/dev/null
```

Esperado: ver lista dos arquivos a atualizar. Anote.

- [ ] **Passo 2:** `git mv` dos arquivos canônicos

```bash
git mv src/lotofacil_ml/data/fetcher.py src/lotofacil/infra/dados/api_caixa.py
git mv src/lotofacil_ml/data/database.py src/lotofacil/infra/dados/banco.py
git mv src/lotofacil_ml/data/loader.py src/lotofacil/infra/dados/leitor.py
git mv src/lotofacil_ml/data/preprocessor.py src/lotofacil/infra/dados/preprocessador.py
```

- [ ] **Passo 3:** Renomear classes/funções dentro dos arquivos movidos

Em `src/lotofacil/infra/dados/api_caixa.py`:

```python
# class LotofacilFetcher → class ColetorAPI
sed -i 's/class LotofacilFetcher/class ColetorAPI/g' src/lotofacil/infra/dados/api_caixa.py
```

Em `src/lotofacil/infra/dados/preprocessador.py`:

```python
sed -i 's/class LotofacilPreprocessor/class Preprocessador/g' src/lotofacil/infra/dados/preprocessador.py
```

Em `src/lotofacil/infra/dados/leitor.py`:

```python
sed -i 's/def load_draws\b/def carregar_sorteios/g' src/lotofacil/infra/dados/leitor.py
sed -i 's/def load_draws_from_json\b/def carregar_sorteios_de_json/g' src/lotofacil/infra/dados/leitor.py
```

- [ ] **Passo 4:** Atualizar imports internos (entre os arquivos movidos)

Em `src/lotofacil/infra/dados/*.py`, substituir `from lotofacil_ml.data.*` por imports relativos:

```bash
sed -i 's|from lotofacil_ml\.data\.fetcher import LotofacilFetcher|from .api_caixa import ColetorAPI|g' src/lotofacil/infra/dados/*.py
sed -i 's|from lotofacil_ml\.data\.database import|from .banco import|g' src/lotofacil/infra/dados/*.py
sed -i 's|from lotofacil_ml\.data\.loader import|from .leitor import|g' src/lotofacil/infra/dados/*.py
```

Também substituir `Draw`/`Prediction` por `Sorteio`/`Predicao` (aliases existem, mas seguir convenção):

```bash
sed -i 's|from lotofacil_ml\.[a-z_]*\.[a-z_]* import.*Draw|from lotofacil.dominio.entidades import Sorteio as Draw|g' src/lotofacil/infra/dados/*.py
# OU melhor: substituir uso para usar Sorteio diretamente
```

Conferir manualmente cada arquivo.

- [ ] **Passo 5:** Atualizar `src/lotofacil/infra/dados/__init__.py` para reexportar a API pública

```python
"""Camada de acesso a dados — API CAIXA, SQLite, JSON loader, preprocessamento."""
from .api_caixa import ColetorAPI
from .banco import DatabaseManager
from .leitor import carregar_sorteios, carregar_sorteios_de_json
from .preprocessador import Preprocessador

__all__ = [
    "ColetorAPI",
    "DatabaseManager",
    "carregar_sorteios",
    "carregar_sorteios_de_json",
    "Preprocessador",
]
```

- [ ] **Passo 6:** Atualizar `src/cli/dados.py`

Substituir cada import antigo:

```python
# ANTES:
from lotofacil_ml.data.fetcher import LotofacilFetcher
from lotofacil_ml.data.database import DatabaseManager
from lotofacil_ml.data.loader import load_draws

# DEPOIS:
from lotofacil.infra.dados import ColetorAPI, DatabaseManager, carregar_sorteios
```

E substituir usos no corpo (`LotofacilFetcher()` → `ColetorAPI()`, `load_draws(...)` → `carregar_sorteios(...)`).

- [ ] **Passo 7:** Atualizar `src/cli/modelo.py`, `src/cli/portfolio.py`, `src/cli/app.py`

Procurar e ajustar todos os `from lotofacil_ml.data.*` e `from data.*`:

```bash
grep -ln "from lotofacil_ml.data\|from data\." src/cli/
# Para cada arquivo, fazer as substituições com sed ou editor
```

- [ ] **Passo 8:** Validar imports

```bash
python -c "from lotofacil.infra.dados import ColetorAPI, DatabaseManager, carregar_sorteios, Preprocessador"
python -c "from cli.app import app"
python -c "from cli.dados import app as dados_app"
python -c "from cli.modelo import app as modelo_app"
```

Esperado: sem erros.

- [ ] **Passo 9:** Verificar que nenhum `lotofacil_ml.data` resta em cli/dashboard

```bash
grep -rn "from lotofacil_ml.data\|from data\." src/cli/ src/dashboard/
# 0 resultados esperados
```

- [ ] **Passo 10:** Deletar `src/data/` (resíduos órfãos — só preprocessor era canônico, já movido)

NÃO deletar nesta task. Esse pacote ainda pode ter `climate_loader.py` que vai pra experimentos na onda 6. Deletar definitivo na onda 5 task 07.

- [ ] **Passo 11:** Testes

```bash
pytest
```

- [ ] **Passo 12:** Smoke

```bash
lotofacil dados status
lotofacil dados atualizar --latest
```

- [ ] **Passo 13:** Commit

```bash
git add -A
git commit -m "refactor(infra): move lotofacil_ml/data → infra/dados (PT)

Movido:
- fetcher.py → api_caixa.py  (LotofacilFetcher → ColetorAPI)
- database.py → banco.py     (DatabaseManager mantido)
- loader.py → leitor.py      (load_draws → carregar_sorteios)
- preprocessor.py → preprocessador.py (LotofacilPreprocessor → Preprocessador)

Imports atualizados em cli/dados.py, cli/modelo.py, cli/portfolio.py,
cli/app.py. Resíduos vazios (src/data/) serão deletados na onda 5."
```
