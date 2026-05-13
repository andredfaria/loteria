# Task 8.1 — Consolidar testes em `testes/`

**Onda:** 8 — Testes + docs
**Prioridade:** média
**Tempo estimado:** ~20 min
**Depende de:** 7.7

## Objetivo

Mover todos os testes para `testes/` na raiz, organizados em `unidade/` e `integracao/` espelhando a arquitetura por camadas. Coletar testes que ficaram espalhados:

- `tests/` (raiz) — provavelmente testes de strategies
- `tests/test_*.py` (raiz) — testes que escrevemos nas ondas 2 e 4 (provisórios)
- `src/lotofacil/experimentos/tests/` — testes do lab
- `src/lotofacil/interface/painel/tests/` — testes do painel

## Estrutura final

```
testes/
├── __init__.py
├── conftest.py                      # se necessário (provavelmente conftest da raiz fica)
├── unidade/
│   ├── __init__.py
│   ├── dominio/
│   │   ├── __init__.py
│   │   ├── test_entidades.py
│   │   ├── test_regras.py
│   │   ├── test_estrategia.py
│   │   └── test_excecoes.py
│   ├── infra/
│   │   ├── __init__.py
│   │   ├── test_config.py
│   │   ├── dados/
│   │   ├── atributos/
│   │   ├── modelos/
│   │   ├── estrategias/
│   │   └── avaliacao/
│   ├── servicos/
│   │   ├── test_atualizar_base.py
│   │   ├── test_consultar_status_base.py
│   │   ├── test_treinar_modelos.py
│   │   ├── test_rodar_backtest.py
│   │   ├── test_gerar_predicao.py
│   │   ├── test_validar_predicoes.py
│   │   ├── test_listar_historico_predicoes.py
│   │   ├── test_gerar_portfolio.py
│   │   ├── test_validar_portfolio.py
│   │   ├── test_listar_jogos_gerados.py
│   │   └── test_listar_modelos_treinados.py
│   └── experimentos/
│       └── ...
└── integracao/
    ├── __init__.py
    ├── cli/
    │   └── test_smoke_cli.py
    └── painel/
        └── test_servidor.py
```

## Arquivos envolvidos

**Mover (git mv) — categorizar cada teste:**

| Atual | Novo |
|---|---|
| `tests/test_dominio_entidades.py` (onda 2.2) | `testes/unidade/dominio/test_entidades.py` |
| `tests/test_dominio_regras.py` | `testes/unidade/dominio/test_regras.py` |
| `tests/test_dominio_estrategia.py` | `testes/unidade/dominio/test_estrategia.py` |
| `tests/test_dominio_excecoes.py` | `testes/unidade/dominio/test_excecoes.py` |
| `tests/test_infra_config.py` | `testes/unidade/infra/test_config.py` |
| `tests/test_servicos_*.py` (ondas 4.1-4.5) | `testes/unidade/servicos/*` |
| `tests/test_strategies/*` | `testes/unidade/infra/estrategias/*` |
| `src/lotofacil/experimentos/tests/*` | `testes/unidade/experimentos/*` |
| `src/lotofacil/interface/painel/tests/*` | `testes/integracao/painel/*` |

## Dependências

- 7.7

## Critérios de aceite

- [ ] `testes/` existe com estrutura `unidade/` + `integracao/`
- [ ] `tests/` (raiz) não existe mais
- [ ] `find src/ -name "tests" -type d` retorna 0 (todos os tests/ internos saíram)
- [ ] `pytest testes/` (do root) descobre e roda tudo, todos passam
- [ ] `pytest` (sem args) também funciona após task 8.2 atualizar pyproject

## Passos detalhados

- [ ] **Passo 1:** Criar estrutura

```bash
mkdir -p testes/unidade/{dominio,infra,servicos,experimentos}
mkdir -p testes/integracao/{cli,painel}
touch testes/__init__.py
touch testes/unidade/__init__.py testes/unidade/dominio/__init__.py
touch testes/unidade/infra/__init__.py testes/unidade/servicos/__init__.py
touch testes/unidade/experimentos/__init__.py
touch testes/integracao/__init__.py testes/integracao/cli/__init__.py
touch testes/integracao/painel/__init__.py
```

- [ ] **Passo 2:** Mover testes de domínio

```bash
git mv tests/test_dominio_entidades.py testes/unidade/dominio/test_entidades.py
git mv tests/test_dominio_regras.py testes/unidade/dominio/test_regras.py
git mv tests/test_dominio_estrategia.py testes/unidade/dominio/test_estrategia.py
git mv tests/test_dominio_excecoes.py testes/unidade/dominio/test_excecoes.py
```

- [ ] **Passo 3:** Mover testes de infra

```bash
git mv tests/test_infra_config.py testes/unidade/infra/test_config.py
# Se houver tests/test_strategies/ — move
git mv tests/test_strategies testes/unidade/infra/estrategias 2>/dev/null
```

- [ ] **Passo 4:** Mover testes de serviços

```bash
git mv tests/test_servicos_dados.py testes/unidade/servicos/test_atualizar_base.py
git mv tests/test_servicos_modelos.py testes/unidade/servicos/test_treinar_modelos.py
git mv tests/test_servicos_predicao.py testes/unidade/servicos/test_gerar_predicao.py
git mv tests/test_servicos_portfolio.py testes/unidade/servicos/test_gerar_portfolio.py
git mv tests/test_servicos_listagem.py testes/unidade/servicos/test_listar_jogos_gerados.py
```

(Ajustar nomes conforme arquivos reais — pode ser que um arquivo tenha múltiplos serviços.)

- [ ] **Passo 5:** Mover testes do lab

```bash
git mv src/lotofacil/experimentos/tests/* testes/unidade/experimentos/
[ -d src/lotofacil/experimentos/tests ] && rmdir src/lotofacil/experimentos/tests
```

- [ ] **Passo 6:** Mover testes do painel

```bash
git mv src/lotofacil/interface/painel/tests/test_servidor.py testes/integracao/painel/test_servidor.py
git mv src/lotofacil/interface/painel/tests/__init__.py testes/integracao/painel/__init__.py 2>/dev/null || true
[ -d src/lotofacil/interface/painel/tests ] && rmdir src/lotofacil/interface/painel/tests
```

- [ ] **Passo 7:** Limpar pasta `tests/` antiga

```bash
[ -d tests ] && rmdir tests 2>/dev/null
# Se não vazia ainda, listar:
ls tests/ 2>/dev/null
```

- [ ] **Passo 8:** Validar estrutura

```bash
find testes -name "test_*.py" | sort
```

- [ ] **Passo 9:** Rodar pytest do diretório novo

```bash
pytest testes/ -v
```

Esperado: todos passam.

- [ ] **Passo 10:** Commit

```bash
git add -A
git commit -m "test: consolida testes em testes/{unidade,integracao}/

Testes movidos:
- tests/test_dominio_*.py → testes/unidade/dominio/
- tests/test_infra_config.py → testes/unidade/infra/
- tests/test_servicos_*.py → testes/unidade/servicos/
- tests/test_strategies/ → testes/unidade/infra/estrategias/
- src/lotofacil/experimentos/tests/ → testes/unidade/experimentos/
- src/lotofacil/interface/painel/tests/ → testes/integracao/painel/

pytest configurado para descobrir testes/ na task 8.2."
```
