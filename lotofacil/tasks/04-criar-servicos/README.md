# Onda 4 — Criar `servicos/`

**Prioridade:** alta
**Risco:** médio
**Tasks:** 6
**Pré-requisitos:** Onda 3

## Objetivo

Extrair a lógica de orquestração que hoje vive dentro dos comandos CLI (em `src/cli/dados.py`, `src/cli/modelo.py`, `src/cli/portfolio.py`) para uma camada de **serviços (use cases)** em `src/lotofacil/servicos/`. Os comandos CLI passam a ser thin wrappers que parseiam args, chamam o serviço e formatam a saída.

Isso elimina a duplicação CLI ↔ painel: o painel vai consumir os mesmos serviços na onda 5.

## Padrão

Cada serviço é uma **função pública** retornando **dataclass frozen** com o resultado:

```python
# src/lotofacil/servicos/atualizar_base.py
from dataclasses import dataclass
from typing import Literal
from lotofacil.dominio.entidades import Sorteio
from lotofacil.infra.dados import api_caixa, banco

@dataclass(frozen=True)
class ResultadoAtualizacao:
    total_novos: int
    ultimo_concurso: int
    sorteios_adicionados: list[Sorteio]

def atualizar_base(escopo: Literal["todos", "novos", "ultimo"] = "novos") -> ResultadoAtualizacao:
    """Sincroniza a base local com a API CAIXA."""
    ...
```

## Os 11 serviços

| Serviço | Substitui lógica atualmente em |
|---|---|
| `atualizar_base` | `cli/dados.py atualizar` |
| `consultar_status_base` | `cli/dados.py status` |
| `treinar_modelos` | `cli/modelo.py treinar` |
| `rodar_backtest` | `cli/modelo.py backtest` |
| `gerar_predicao` | `cli/app.py prever` |
| `validar_predicoes` | `cli/modelo.py validar` |
| `listar_historico_predicoes` | `cli/modelo.py historico` |
| `gerar_portfolio` | `cli/portfolio.py` (lógica embutida) |
| `validar_portfolio` | `cli/portfolio.py validar` |
| `listar_jogos_gerados` | `dashboard/server.py _list_game_files` |
| `listar_modelos_treinados` | `dashboard/server.py _scan_models` |

## Tasks

1. `01-servicos-dados.md` — `atualizar_base` + `consultar_status_base`
2. `02-servicos-modelos.md` — `treinar_modelos` + `rodar_backtest`
3. `03-servicos-predicao.md` — `gerar_predicao` + `validar_predicoes` + `listar_historico_predicoes`
4. `04-servicos-portfolio.md` — `gerar_portfolio` + `validar_portfolio`
5. `05-servicos-listagem.md` — `listar_jogos_gerados` + `listar_modelos_treinados`
6. `06-refatorar-cli.md` — `cli/*.py` → thin wrappers usando serviços

## O que cada serviço NÃO faz

- **Não formata stdout** (rich, print). Devolve dado tipado.
- **Não captura exceções genéricas**. Re-levanta `LotofacilError` (definido em onda 2 `dominio/excecoes.py`).
- **Não chama subprocess**. Lógica de produção vive in-process.

## Critérios de aceite (onda inteira)

- [ ] `pytest` passa (cada serviço tem teste de unidade)
- [ ] Comandos CLI funcionam idênticos ao comportamento atual:
  - `lotofacil dados atualizar` (com nova flag `--escopo` ou ainda com flags antigas?) — **antigas até onda 5**
  - `lotofacil dados status`
  - `lotofacil modelo treinar`
  - `lotofacil modelo backtest`
  - `lotofacil prever`
  - `lotofacil portfolio --jogos 4`
- [ ] Imports `from lotofacil.servicos.<nome> import <funcao>` resolvem
- [ ] `grep -rn "from lotofacil.infra" src/cli/` retorna 0 (CLI só importa de servicos/dominio, não direto da infra)

## Smoke test

```bash
pytest
python -c "from lotofacil.servicos.atualizar_base import atualizar_base; print(atualizar_base.__doc__)"
lotofacil dados status
lotofacil prever
```
