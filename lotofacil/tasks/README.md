# Tasks — Consolidação Estrutural do lotofacil/

Plano de execução do refactor descrito em:
- **Spec:** `docs/superpowers/specs/2026-05-12-consolidacao-estrutural-design.md`
- **Plano:** `docs/superpowers/plans/2026-05-13-consolidacao-estrutural.md`

## Como ler este diretório

Cada subpasta `NN-<onda>/` representa uma onda de refactor. Dentro de cada onda há um `README.md` (visão geral + critérios) e arquivos `NN-<task>.md` com tasks atômicas.

Cada task contém os campos exigidos pelo brief:
- **Objetivo** — uma frase
- **Descrição técnica** — resumo do que mudar
- **Arquivos envolvidos** — paths exatos (deletar / criar / mover / modificar)
- **Dependências** — outras tasks que devem estar feitas antes
- **Critérios de aceite** — comandos/testes que validam o resultado
- **Prioridade** — alta / média / baixa
- **Passos detalhados** — checkboxes acionáveis (TDD onde aplica, refactor + verificação caso contrário)
- **Commit** — mensagem de commit padronizada

## Ordem de execução

Tasks devem ser executadas em ordem numérica:

```
01-limpeza-segura/         (3 tasks — alta prioridade)
02-esqueleto-dominio/      (6 tasks — alta prioridade)
03-migrar-infra/           (5 tasks — alta prioridade, médio-alto risco)
04-criar-servicos/         (6 tasks — alta prioridade)
05-mover-interface/        (7 tasks — alta prioridade)
06-experimentos/           (3 tasks — média prioridade)
07-pastas-fisicas/         (7 tasks — média prioridade)
08-testes-docs/            (5 tasks — média prioridade)
```

Total: **42 tasks**.

## Dependências entre ondas

```
1 → 2 → 3 → 4 → 5 ─┬─→ 6
                   ├─→ 7
                   └─→ 8 (depende de 6 e 7)
```

Tasks dentro de uma onda **podem** ter dependências internas (ver campo "Dependências" de cada task).

## Modo de execução

Cada task é um commit atomico. Após cada task:

1. Rodar `pytest` (deve passar)
2. Rodar smoke test da onda (ver README da onda)
3. Commit com mensagem do campo "Commit" da task

Se uma task falha, `git reset --hard HEAD` volta ao estado anterior e nenhum trabalho posterior é perdido.

## Convenção de nomes (regra geral do refactor)

Todo módulo, classe, função, flag e comando criado/renomeado é **em português**:

- Módulos: `dominio/`, `servicos/`, `infra/`, `interface/`, `experimentos/`
- Sub-módulos: `dados/`, `atributos/`, `modelos/`, `estrategias/`, `avaliacao/`, `geracao/`, `agendador/`, `cli/`, `painel/`
- Classes: `Sorteio`, `Predicao`, `Portfolio`, `EstrategiaBase`, `LotofacilError`, ...
- Flags CLI: `--todos`, `--ultimo`, `--abordagem`, `--concurso`, `--jogos`, ...
- Loanwords técnicos consagrados ficam: `backtest`, `status`, `Protocol`, `dataclass`

## Estado das tasks

Use o checkbox `- [ ]` em cada task como tracker. Marque `- [x]` quando completar.

## Smoke tests comuns

Após cada onda, mínimo:

```bash
pytest                            # passa
python -c "import lotofacil"      # importa (após onda 2 em diante)
```

Smoke tests específicos por onda estão no `README.md` de cada subpasta.
