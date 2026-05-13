# Onda 2 — Esqueleto + domínio

**Prioridade:** alta
**Risco:** baixo
**Tasks:** 6
**Pré-requisitos:** Onda 1

## Objetivo

Criar a estrutura nova `src/lotofacil/` com a camada de **domínio** pronta (entidades, regras, exceções, protocols) e `infra/config.py` com paths globais. Nada do código antigo é movido ainda — esta onda apenas **adiciona** arquivos novos.

## Escopo

Cria:

```
src/lotofacil/
├── __init__.py
├── dominio/
│   ├── __init__.py
│   ├── entidades.py          # Sorteio, Predicao (+ aliases Draw, Prediction)
│   ├── regras.py             # constantes da loteria
│   ├── estrategia.py         # Protocol EstrategiaBase
│   └── excecoes.py           # LotofacilError + subtipos
├── servicos/__init__.py
├── infra/
│   ├── __init__.py
│   └── config.py             # paths globais (DADOS_DIR, SAIDA_DIR, DB_PATH, ...)
├── interface/__init__.py
└── experimentos/__init__.py
```

## O que NÃO fazer nesta onda

- Não mover nada de `src/lotofacil_ml/`, `src/strategies/`, etc.
- Não atualizar `pyproject.toml` (entry point continua `src.cli.app:app`)
- Não deletar `src/core/models.py` (ele ainda existe; só ficamos com o conteúdo PORTADO)

## Tasks

1. `01-estrutura-pastas.md` — criar pastas e `__init__.py` vazios
2. `02-dominio-entidades.md` — `Sorteio`, `Predicao` (com aliases temporários `Draw`, `Prediction`)
3. `03-dominio-regras.md` — constantes (1–25, 15 dezenas, payouts, regras de filtros)
4. `04-dominio-estrategia.md` — Protocol `EstrategiaBase`
5. `05-dominio-excecoes.md` — `LotofacilError` + 4 subtipos
6. `06-infra-config.md` — paths globais consolidados

## Critérios de aceite (onda inteira)

- [ ] `pytest` passa (testes novos do domínio inclusos)
- [ ] `python -c "from lotofacil.dominio.entidades import Sorteio, Predicao"` funciona
- [ ] `python -c "from lotofacil.infra.config import DADOS_DIR, SAIDA_DIR, DB_PATH"` funciona
- [ ] Imports antigos (`from data.loader import ...`) continuam funcionando

## Smoke test

```bash
pytest
python -c "from lotofacil.dominio.entidades import Sorteio; print(Sorteio.__mro__)"
python -c "from lotofacil.infra.config import DADOS_DIR; print(DADOS_DIR)"
lotofacil dados status                     # ainda funciona (CLI inalterada)
```

## Aliases temporários

`dominio/entidades.py` exporta:

```python
@dataclass(frozen=True)
class Sorteio: ...

@dataclass(frozen=True)
class Predicao: ...

# Aliases temporários — REMOVER NA ONDA 8 task 03
Draw = Sorteio
Prediction = Predicao
```

Permitem que código antigo (`from core.models import Draw`) continue funcionando até a onda 8.
