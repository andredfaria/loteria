# Task 6.1 — Mover `src/lotofacil_lab/` → `experimentos/`

**Onda:** 6 — Experimentos
**Prioridade:** média
**Tempo estimado:** ~20 min
**Depende de:** 5.7

## Objetivo

Mover o pacote experimental inteiro (`src/lotofacil_lab/`) para `src/lotofacil/experimentos/`, preservando a estrutura interna. Atualizar imports nos consumidores externos (CLI `lab`) e dentro do próprio pacote.

## Arquivos envolvidos

**Mover (git mv da pasta inteira):**

| De | Para |
|---|---|
| `src/lotofacil_lab/coleta/` | `src/lotofacil/experimentos/coleta/` |
| `src/lotofacil_lab/data/` | `src/lotofacil/experimentos/dados/` |
| `src/lotofacil_lab/features/` | `src/lotofacil/experimentos/atributos/` |
| `src/lotofacil_lab/models/` | `src/lotofacil/experimentos/modelos/` |
| `src/lotofacil_lab/evaluation/` | `src/lotofacil/experimentos/avaliacao/` |
| `src/lotofacil_lab/experiments/` | `src/lotofacil/experimentos/uso/` |
| `src/lotofacil_lab/tests/` | `src/lotofacil/experimentos/tests/` |
| `src/lotofacil_lab/output/` | (deixa por ora; vai para `saida/experimentos/` na onda 7) |
| `src/lotofacil_lab/saved_models/` | (deixa por ora; vai para `saida/experimentos/modelos/` na onda 7) |
| `src/lotofacil_lab/config.py` | `src/lotofacil/experimentos/config.py` |
| `src/lotofacil_lab/main.py` | `src/lotofacil/experimentos/main.py` |
| `src/lotofacil_lab/__init__.py` | `src/lotofacil/experimentos/__init__.py` |

## Dependências

- 5.7

## Critérios de aceite

- [ ] `src/lotofacil_lab/` não existe mais (exceto talvez `output/` e `saved_models/`)
- [ ] `python -c "from lotofacil.experimentos.main import app"` funciona
- [ ] `lotofacil lab ablacao --n-test 5` funciona (CLI delega para `experimentos.main`)
- [ ] `pytest src/lotofacil/experimentos/tests/` passa

## Passos detalhados

- [ ] **Passo 1:** Mover pastas top-level

```bash
git mv src/lotofacil_lab/coleta src/lotofacil/experimentos/coleta
git mv src/lotofacil_lab/data src/lotofacil/experimentos/dados
git mv src/lotofacil_lab/features src/lotofacil/experimentos/atributos
git mv src/lotofacil_lab/models src/lotofacil/experimentos/modelos
git mv src/lotofacil_lab/evaluation src/lotofacil/experimentos/avaliacao
git mv src/lotofacil_lab/experiments src/lotofacil/experimentos/uso
git mv src/lotofacil_lab/tests src/lotofacil/experimentos/tests 2>/dev/null
git mv src/lotofacil_lab/config.py src/lotofacil/experimentos/config.py
git mv src/lotofacil_lab/main.py src/lotofacil/experimentos/main.py
```

(`output/` e `saved_models/` ficam — onda 7 mexe.)

- [ ] **Passo 2:** Mesclar `__init__.py`

`src/lotofacil/experimentos/__init__.py` já existe (criado na onda 2). Se `lotofacil_lab/__init__.py` tem conteúdo, mesclar:

```bash
cat src/lotofacil_lab/__init__.py >> src/lotofacil/experimentos/__init__.py 2>/dev/null
git rm src/lotofacil_lab/__init__.py 2>/dev/null
```

- [ ] **Passo 3:** Limpar `src/lotofacil_lab/`

```bash
# Sobram só output/, saved_models/ (cuidados pela onda 7)
ls src/lotofacil_lab/
# Esperado: output/, saved_models/ (não Python)
```

- [ ] **Passo 4:** Validar imports básicos

```bash
python -c "from lotofacil.experimentos.main import app"
# Esperado: pode dar erro se imports internos ainda usam 'lotofacil_lab.*'
# Próxima task corrige.
```

- [ ] **Passo 5:** Commit (sem rodar pytest ainda — imports vão falhar)

```bash
git add -A
git commit -m "refactor(experimentos): move lotofacil_lab → experimentos

Pasta inteira movida. Imports internos (lotofacil_lab.*) ainda quebrados
— task 6.2 atualiza.

Subpacotes:
- coleta/ (mantém)
- data/ → dados/
- features/ → atributos/
- models/ → modelos/
- evaluation/ → avaliacao/
- experiments/ → uso/

output/ e saved_models/ ficam para a onda 7."
```
