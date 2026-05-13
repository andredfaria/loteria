# Task 6.3 — Renomear arquivos do lab para PT

**Onda:** 6 — Experimentos
**Prioridade:** média
**Tempo estimado:** ~15 min
**Depende de:** 6.2

## Objetivo

Renomear arquivos internos do `experimentos/` para PT, conforme convenção do projeto (PT total).

## Renomeações

| De | Para |
|---|---|
| `experimentos/coleta/backfill_clima_archive.py` | `experimentos/coleta/preencher_clima_archive.py` |
| `experimentos/dados/draws_loader.py` | `experimentos/dados/leitor_sorteios.py` |
| `experimentos/dados/climate_loader.py` | `experimentos/dados/clima.py` |
| `experimentos/dados/lunar_loader.py` | `experimentos/dados/lua.py` |
| `experimentos/dados/feature_flags.py` | `experimentos/dados/flags_atributos.py` |
| `experimentos/uso/runner.py` | `experimentos/uso/rodar_ablacao.py` |
| `experimentos/uso/ablation_grid.py` | `experimentos/uso/grade_ablacao.py` |
| `experimentos/uso/report.py` | `experimentos/uso/relatorio.py` |
| `experimentos/models/baseline_random.py` | `experimentos/modelos/baseline_aleatorio.py` |
| `experimentos/models/baseline_frequency.py` | `experimentos/modelos/baseline_frequencia.py` |
| `experimentos/models/neural_modular.py` | `experimentos/modelos/neural_modular.py` (mantém) |

Atualizar todos os imports que referem aos nomes antigos.

## Arquivos envolvidos

**Mover (git mv) + atualizar imports.**

## Dependências

- 6.2

## Critérios de aceite

- [ ] `grep -rn "draws_loader\|climate_loader\|lunar_loader\|feature_flags\|backfill_clima_archive\|ablation_grid" src/` retorna 0
- [ ] `lotofacil lab ablacao --n-test 5` funciona
- [ ] `lotofacil lab checar-lua --data 2026-05-13` retorna fase lunar
- [ ] `pytest src/lotofacil/experimentos/tests/` passa

## Passos detalhados

- [ ] **Passo 1:** Listar arquivos a renomear

```bash
ls src/lotofacil/experimentos/coleta/
ls src/lotofacil/experimentos/dados/
ls src/lotofacil/experimentos/uso/
ls src/lotofacil/experimentos/modelos/
```

- [ ] **Passo 2:** `git mv` em batch

```bash
# Coleta
git mv src/lotofacil/experimentos/coleta/backfill_clima_archive.py src/lotofacil/experimentos/coleta/preencher_clima_archive.py 2>/dev/null

# Dados
git mv src/lotofacil/experimentos/dados/draws_loader.py src/lotofacil/experimentos/dados/leitor_sorteios.py 2>/dev/null
git mv src/lotofacil/experimentos/dados/climate_loader.py src/lotofacil/experimentos/dados/clima.py 2>/dev/null
git mv src/lotofacil/experimentos/dados/lunar_loader.py src/lotofacil/experimentos/dados/lua.py 2>/dev/null
git mv src/lotofacil/experimentos/dados/feature_flags.py src/lotofacil/experimentos/dados/flags_atributos.py 2>/dev/null

# Uso
git mv src/lotofacil/experimentos/uso/runner.py src/lotofacil/experimentos/uso/rodar_ablacao.py 2>/dev/null
git mv src/lotofacil/experimentos/uso/ablation_grid.py src/lotofacil/experimentos/uso/grade_ablacao.py 2>/dev/null
git mv src/lotofacil/experimentos/uso/report.py src/lotofacil/experimentos/uso/relatorio.py 2>/dev/null

# Modelos
git mv src/lotofacil/experimentos/modelos/baseline_random.py src/lotofacil/experimentos/modelos/baseline_aleatorio.py 2>/dev/null
git mv src/lotofacil/experimentos/modelos/baseline_frequency.py src/lotofacil/experimentos/modelos/baseline_frequencia.py 2>/dev/null
```

- [ ] **Passo 3:** Atualizar imports nos arquivos do lab

```bash
find src/lotofacil/experimentos -name "*.py" -exec sed -i \
  -e 's|backfill_clima_archive|preencher_clima_archive|g' \
  -e 's|draws_loader|leitor_sorteios|g' \
  -e 's|climate_loader|clima|g' \
  -e 's|lunar_loader|lua|g' \
  -e 's|feature_flags|flags_atributos|g' \
  -e 's|\bruner\b|rodar_ablacao|g' \
  -e 's|ablation_grid|grade_ablacao|g' \
  -e 's|baseline_random|baseline_aleatorio|g' \
  -e 's|baseline_frequency|baseline_frequencia|g' \
  {} +
```

- [ ] **Passo 4:** Verificar referências

```bash
grep -rn "draws_loader\|climate_loader\|lunar_loader\|feature_flags\|backfill_clima_archive\|ablation_grid\|baseline_random\|baseline_frequency" src/
```

Esperado: 0.

- [ ] **Passo 5:** Validar imports

```bash
python -c "from lotofacil.experimentos.main import app; print('OK')"
python -c "from lotofacil.experimentos.dados.lua import *"
python -c "from lotofacil.experimentos.dados.clima import *"
```

- [ ] **Passo 6:** Testes

```bash
pytest src/lotofacil/experimentos/tests/
pytest    # suite completa
```

- [ ] **Passo 7:** Smoke

```bash
lotofacil lab ablacao --n-test 5
lotofacil lab checar-lua --data 2026-05-13
lotofacil lab preencher-clima --ultimos 3
```

- [ ] **Passo 8:** Commit

```bash
git add -A
git commit -m "refactor(experimentos): renomeia arquivos internos para PT

- draws_loader.py → leitor_sorteios.py
- climate_loader.py → clima.py
- lunar_loader.py → lua.py
- feature_flags.py → flags_atributos.py
- backfill_clima_archive.py → preencher_clima_archive.py
- runner.py → rodar_ablacao.py
- ablation_grid.py → grade_ablacao.py
- baseline_random.py → baseline_aleatorio.py
- baseline_frequency.py → baseline_frequencia.py
- (neural_modular.py mantém — termo técnico)

Última task da onda 6. Experimentos completamente consolidados em PT,
usando o core de lotofacil.infra.*."
```
