# Design: Backtesting de Modelos via Dashboard

**Data:** 2026-07-06
**Escopo:** Backend (serviço + CLI + API Flask) e frontend (`dashboard.html`)
**Arquivos alvo:**
- `lotofacil/src/lotofacil/servicos/rodar_backtest_lab.py` (novo)
- `lotofacil/src/lotofacil/experimentos/main.py` (novo comando `lab backtest`)
- `lotofacil/src/lotofacil/interface/painel/treino_registry.py` (nova tabela `backtests`)
- `lotofacil/src/lotofacil/interface/painel/server.py` (novas rotas `/api/backtests/*`)
- `lotofacil/src/lotofacil/interface/painel/static/dashboard.html` (nova aba "Backtest")

---

## Contexto

O dashboard hoje permite treinar modelos neurais do lab (configs `base+temp+priors`, `+lua`, `+clima`, `+lua+clima`) e gerar jogos com eles, mas não tem como simular de forma realista "como esse modelo teria se saído no passado". A aba "Comparar" existente compara métricas de um relatório KPI pré-gerado (histórico de predições reais já feitas), não uma simulação sob demanda.

O objetivo é permitir: selecionar um ou mais modelos (configs neurais do lab), um intervalo de concursos, e rodar uma simulação walk-forward — treina no concurso N, prevê N+1, sem vazamento de dados — repetindo até o fim do intervalo. Ao final, mostrar acertos por concurso, média de acertos, distribuição de resultados (11–15 pontos) e comparação entre os modelos selecionados (+ baselines de referência).

A infraestrutura de walk-forward sem vazamento já existe e é reaproveitada integralmente:
- `experimentos/evaluation/walkforward.py::walk_forward()` — treina em `draws com concurso < test_concurso`, reprevê a cada `retrain_every` passos.
- `experimentos/experiments/runner.py::ExperimentRunner` — já roda baselines (random, frequency) + múltiplas configs neurais no mesmo período e calcula `mean_hits`, `hits_distribution`, `rate_ge_11/13`, `roi_pct`, `p_value_vs_random`.

Este design é essencialmente uma camada de wiring: expor `ExperimentRunner` via dashboard, com execução assíncrona (a exemplo dos treinos) e histórico persistente.

---

## O que NÃO muda

- `walk_forward()` e `ExperimentRunner` não são alterados — só reaproveitados.
- Modelos clássicos (`infra/modelos/*`, `BacktestEngine`) ficam fora de escopo — não aparecem como opção no seletor.
- A aba "Comparar" (KPI report de predições reais) continua existindo como está; backtest é um recurso adicional, não substitui.
- Nenhuma rota de API existente é removida ou tem seu contrato alterado.

---

## Design

### 1. Serviço: `rodar_backtest_lab.py`

```python
def rodar_backtest_lab(
    configs: list[str],          # signatures, ex: ["base+temp+priors", "base+temp+priors+lua"]
    start_concurso: int,
    end_concurso: int,
    retrain_every: int = BACKTEST_RETRAIN_EVERY,  # default 50
) -> dict:
    ...
```

- Valida cada signature com `FeatureConfig.from_signature()`; levanta `ValueError` com a lista de inválidas se alguma falhar (nenhum job é iniciado).
- Carrega todos os draws (`load_draws()`), calcula `n_test` e `period_start/period_end` a partir de `start_concurso`/`end_concurso`.
- Se o intervalo não deixar `BACKTEST_MIN_TRAIN` concursos de histórico antes de `start_concurso`, desloca `start_concurso` para frente e inclui um campo `"warnings": [...]` no resultado (mesmo comportamento que `walk_forward` já tem internamente para `n_test`).
- `ExperimentRunner.run()` espera `n_test` (nº de concursos de teste) além de `period_start`/`period_end`; como o objetivo é testar **todo** o intervalo pedido, `n_test` é calculado como a contagem de draws com `start_concurso <= concurso <= end_concurso` após o filtro de período — não o default `100` do runner. Isso garante que nenhum concurso do intervalo escolhido fique de fora por causa do valor padrão.
- Delega para `ExperimentRunner(draws).run(n_test=..., configs=[...], run_neural=True, period_start=..., period_end=..., retrain_every=...)` — baselines random+frequency são sempre incluídos (comportamento padrão do runner, nada a fazer).
- Retorna o `report` do runner (já contém, por config: `mean_hits`, `hits_distribution`, `rate_ge_11`, `rate_ge_13`, `roi_pct`, `p_value_vs_random`, `raw_results` com hits por concurso), mais os `warnings` de ajuste de intervalo.

### 2. CLI: `lotofacil lab backtest`

Novo comando em `experimentos/main.py`, ao lado de `train`/`predict`/`ablation`/`compare`:

```
lotofacil lab backtest --configs base+temp+priors,base+temp+priors+lua --start 3600 --end 3700 --retrain-every 25
```

- Chama `rodar_backtest_lab(...)`.
- Escreve o resultado completo em `saida/backtests/backtest_<uuid>.json`.
- Imprime `BACKTEST_RESULT_PATH: <path>` (stdout, `print()` puro — mesmo padrão de `TREINO_MODELO_PATH` em `train`) para o subprocess wrapper do dashboard capturar.
- Progresso incremental: cada config testada emite uma linha `console.print` (`[cyan]Testando config X (i/N)...[/cyan]`) que o dashboard já tem mecanismo de capturar linha a linha via `job_output`.

### 3. Persistência: tabela `backtests`

Nova tabela em `treino_registry.py` (mesma classe `TreinoRegistry`, reaproveitando `job_status`/`job_output` já genéricos por `task_id`):

```sql
CREATE TABLE IF NOT EXISTS backtests (
    id TEXT PRIMARY KEY,
    configs TEXT NOT NULL,           -- json list
    start_concurso INTEGER NOT NULL,
    end_concurso INTEGER NOT NULL,
    retrain_every INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',   -- running | completed | failed | cancelled
    resultado_path TEXT,
    criado_em TEXT NOT NULL,
    concluido_em TEXT
);
```

Métodos novos: `criar_backtest`, `registrar_resultado_backtest`, `marcar_falha_backtest`, `listar_backtests`, `buscar_backtest`, `deletar_backtest` — espelhando os métodos já existentes para `treinos`.

### 4. API Flask

Novas rotas em `server.py`, seguindo o padrão de `/api/treinos/*` (subprocess + `_procs` + `TreinoRegistry`):

| Rota | Método | Descrição |
|---|---|---|
| `/api/backtests/iniciar` | POST | Body: `{configs: [...], start: int, end: int, retrain_every: int}`. Valida configs e range contra os concursos disponíveis; cria registro `running`, spawna subprocess (`lotofacil lab backtest ...`), cria job. Retorna `{id, task_id}`. |
| `/api/backtests` | GET | Lista histórico (`listar_backtests()`), mais recentes primeiro. |
| `/api/backtests/<id>` | GET | Detalhe completo — lê `resultado_path` e retorna o JSON completo (comparação + raw hits por concurso). |
| `/api/backtests/<id>` | DELETE | Remove registro (não deleta o arquivo de resultado por padrão — mesma política leniente de `treinos`). |
| `/api/jobs/<task_id>/poll` | GET | Reaproveitado sem alteração. |
| `/api/jobs/<task_id>/cancel` | POST | Reaproveitado sem alteração — mata o subprocess, marca `backtests.status = 'cancelled'`. |

O subprocess wrapper que hoje escuta por `TREINO_MODELO_PATH:` ganha um branch equivalente para `BACKTEST_RESULT_PATH:`, chamando `registrar_resultado_backtest(id, path)` ao final.

### 5. Frontend: nova aba "🧪 Backtest"

Nova entrada de topo na sidebar (ao lado de Modelos, ROI Lab, Geração, Jogos), renderizada por `renderBacktestPage()`:

**Formulário:**
- Checkboxes para as 4 configs conhecidas (Padrão, +Lua, +Clima, +Lua+Clima) — pelo menos 1 obrigatória.
- Dois campos numéricos: concurso inicial e concurso final (com min/max vindos de `/api/status`, validação inline se fora do range disponível).
- Campo `retrain_every` (número, default 50), com texto de ajuda: "concursos entre cada retreino — menor = mais realista, mais lento".
- Texto dinâmico de estimativa: `~{(end-start)/retrain_every} retreinos por modelo selecionado`.
- Botão **Iniciar Backtest**, desabilitado se nenhuma config marcada ou range inválido.

**Progresso:** reaproveita o modal/log-tail de treino já existente (título trocado para "Rodando backtest…", uma linha de log por config concluída).

**Resultados** (após conclusão, ou ao reabrir um item do histórico):
- Tabela de comparação: modelo | concursos testados (`n_evaluated`) | média de acertos (`mean_hits`) | taxa ≥11 (`rate_ge_11`) | taxa ≥13 (`rate_ge_13`) | ROI% (`roi_pct`) | p-valor vs. aleatório (`p_value_vs_random`) — ordenada por média de acertos desc (mesma ordenação que o `report` já traz). Só `rate_ge_11`/`rate_ge_13` são calculados pelo runner hoje; taxas ≥12/≥14/≥15 (se exibidas) são derivadas no frontend a partir de `hits_distribution`.
- Gráfico de acertos por concurso: uma série por modelo selecionado + baselines, eixo X = concurso (dados vêm de `raw_results` de cada entry).
- Histograma de distribuição de acertos (11 a 15) por modelo, lado a lado — construído a partir de `hits_distribution` (dict `{hits: contagem}`) de cada entry.

**Histórico:** lista de execuções passadas (data, intervalo, configs, retrain_every, status), clicável para recarregar os resultados sem rodar de novo.

---

## Componentes Afetados

| Componente | Mudança |
|---|---|
| `servicos/rodar_backtest_lab.py` | Novo — wrapper de validação + `ExperimentRunner` |
| `experimentos/main.py` | Novo comando `lab backtest` |
| `treino_registry.py` | Nova tabela `backtests` + métodos CRUD |
| `server.py` | Novas rotas `/api/backtests/*`; branch de captura de `BACKTEST_RESULT_PATH:` no subprocess wrapper |
| `dashboard.html` | Nova aba "Backtest" (sidebar + `renderBacktestPage()` + CSS de gráfico/histograma) |

---

## Critérios de Sucesso

1. Usuário seleciona 1+ configs neurais, um intervalo de concursos e um `retrain_every`, e dispara o backtest pelo dashboard.
2. O treino em cada passo usa apenas concursos anteriores ao concurso previsto (garantia herdada de `walk_forward`, coberta por teste).
3. Baselines (random, frequency) aparecem sempre nos resultados, sem ação extra do usuário.
4. Resultado final mostra: acertos por concurso, média de acertos, distribuição 11–15, e tabela comparativa entre os modelos rodados.
5. Execução roda em background (subprocess) com progresso pollável e opção de cancelar.
6. Cada execução fica salva e é revisível depois pelo histórico, sem precisar rodar de novo.
7. Signatures de config inválidas ou intervalo de concursos fora do range disponível são rejeitados antes de iniciar o job, com mensagem clara.

---

## Fora de Escopo

- Backtesting de modelos clássicos (`infra/modelos/*`, `BacktestEngine`) — só os neurais do lab.
- Mudanças em `walk_forward()` ou `ExperimentRunner` além de reaproveitá-los como estão.
- Alteração da aba "Comparar" existente (KPI de predições reais).
- Definição de novos configs de features além dos 4 já treináveis hoje.
