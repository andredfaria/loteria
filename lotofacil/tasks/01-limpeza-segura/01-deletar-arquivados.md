# Task 1.1 — Deletar diretórios arquivados

**Onda:** 1 — Limpeza segura
**Prioridade:** alta
**Tempo estimado:** ~10 min
**Depende de:** —

## Objetivo

Remover os três diretórios já reconhecidos como obsoletos: `legacy/` (substituído por `src/cli/` e `src/strategies/`, README do próprio diretório confirma), `legado/` (somente docs antigos — preservar 2 referências úteis), e `ml/` (pipeline de scripts standalone superada por `src/lotofacil_ml/`).

## Descrição técnica

1. Mover 2 docs úteis de `legado/docs/` para `docs/` antes de deletar.
2. `git rm -r` em `legacy/`, `legado/`, `ml/`.
3. Verificar via `grep` que nenhum import vivo aponta para eles.

## Arquivos envolvidos

**Mover (preservar conteúdo):**
- `legado/docs/Hierarquia de Estratégias na Lotofácil: Análise de Precedência e Impacto Estatístico.md` → `docs/estrategias/hierarquia-estrategias.md`
- `legado/docs/Relatório Técnico_ Estratégias Racionais para a Lotofácil.md` → `docs/estrategias/relatorio-tecnico-estrategias.md`

**Deletar:**
- `legacy/` (8 subpastas: analise, coleta, dashboard, estrategia, geracao, portfolio, scripts, validacao + README.md)
- `legado/` (após mover os 2 docs; resto descartado: `legado/banco/`, `legado/utilitarios/`, `legado/docs/curl.md`, `legado/docs/100-cada-RELATORIO_COMPLETO_VALIDACAO_ML_3500_3580.md`)
- `ml/` (analise_winners, datasets, modelos, models, tests, validacao + .py files na raiz: features.py, dataset.py, treino.py, backtest.py, inferencia.py, features_avancadas.csv, features_classificador.py, padroes_21.py, predizer_combinado.py, predizer_jogo.py, backtest_classificador.py, treino_classificador.py, recomendacao_concurso_3585.json, relatorio_backtest.json)

## Dependências

Nenhuma. Primeira task do refactor.

## Critérios de aceite

- [ ] `ls legacy/ legado/ ml/ 2>&1 | grep -i "no such"` para todos os 3
- [ ] `docs/estrategias/hierarquia-estrategias.md` existe
- [ ] `docs/estrategias/relatorio-tecnico-estrategias.md` existe
- [ ] `grep -rn "from legacy\|import legacy\|from legado\|from ml\.\|import ml\." src/` retorna 0
- [ ] `pytest` passa
- [ ] `lotofacil dados status` funciona

## Passos detalhados

- [ ] **Passo 1:** Verificar que nada importa desses diretórios

```bash
grep -rn "from legacy\|import legacy" src/ tests/ 2>/dev/null
grep -rn "from legado\|import legado" src/ tests/ 2>/dev/null
grep -rn "from ml\.\|import ml\." src/ tests/ 2>/dev/null
```

Esperado: 0 resultados em cada. Se houver, ABORTAR e revisar.

- [ ] **Passo 2:** Criar pasta de destino para docs preservados

```bash
mkdir -p docs/estrategias
```

- [ ] **Passo 3:** Mover docs úteis

```bash
git mv "legado/docs/Hierarquia de Estratégias na Lotofácil: Análise de Precedência e Impacto Estatístico.md" docs/estrategias/hierarquia-estrategias.md
git mv "legado/docs/Relatório Técnico_ Estratégias Racionais para a Lotofácil.md" docs/estrategias/relatorio-tecnico-estrategias.md
```

- [ ] **Passo 4:** Deletar `legacy/`

```bash
git rm -rf legacy/
```

- [ ] **Passo 5:** Deletar `legado/`

```bash
git rm -rf legado/
```

- [ ] **Passo 6:** Deletar `ml/`

```bash
git rm -rf ml/
```

- [ ] **Passo 7:** Verificar estado

```bash
ls legacy/ legado/ ml/ 2>&1  # 3x "No such file or directory"
ls docs/estrategias/
git status --short            # apenas D (deletes) e A (new doc moves)
```

- [ ] **Passo 8:** Rodar testes

```bash
pytest
```

Esperado: pass.

- [ ] **Passo 9:** Smoke test

```bash
lotofacil dados status
```

Esperado: retorna o status normal (último concurso, total).

- [ ] **Passo 10:** Commit

```bash
git commit -m "chore: remove código arquivado (legacy/, legado/, ml/)

Preserva 2 docs estratégicos em docs/estrategias/. Nenhum import
vivo aponta para esses diretórios — confirmado via grep.

Parte da onda 1 do refactor de consolidação estrutural.
Ref: docs/superpowers/specs/2026-05-12-consolidacao-estrutural-design.md"
```
