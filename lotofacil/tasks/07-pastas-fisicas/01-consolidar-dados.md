# Task 7.1 — Consolidar pasta `dados/` (inputs)

**Onda:** 7 — Pastas físicas
**Prioridade:** média
**Tempo estimado:** ~15 min
**Depende de:** 6.3

## Objetivo

Mover conteúdo de `data/raw/concursos/`, `data/processed/`, `data/lotofacil.db` para `dados/concursos/`, `dados/processado/`, `dados/lotofacil.db`. Preservar o symlink `dados/ → ~/lotofacil-dados/`.

## Arquivos envolvidos

**Mover:**

| De | Para |
|---|---|
| `data/raw/concursos/*.json` | `dados/concursos/` |
| `data/processed/all_draws.json` | `dados/processado/all_draws.json` |
| `data/lotofacil.db` | `dados/lotofacil.db` |

**Deletar (após mover):**
- `data/raw/`
- `data/processed/`
- `data/` (vazio)

## Dependências

- 6.3

## Critérios de aceite

- [ ] `ls dados/concursos/` lista os JSONs
- [ ] `dados/lotofacil.db` existe
- [ ] `dados/processado/all_draws.json` existe
- [ ] `data/` não existe mais
- [ ] `lotofacil dados status` continua mostrando contagem correta
- [ ] `pytest` passa

## Passos detalhados

- [ ] **Passo 1:** Verificar symlink

```bash
ls -la dados
# Esperado: dados -> /home/andre/lotofacil-dados
readlink dados
```

Se for um symlink, o destino é `~/lotofacil-dados/` — então criar lá dentro:

```bash
mkdir -p ~/lotofacil-dados/concursos ~/lotofacil-dados/processado
```

- [ ] **Passo 2:** Mover concursos

```bash
# Os JSONs estão em data/raw/concursos/
ls data/raw/concursos/ | head -5
# Mover individualmente ou em batch com git mv
git mv data/raw/concursos/* dados/concursos/
```

> **Atenção:** se `git mv` falhar com "destination is symlink", usar `mv` direto:
>
> ```bash
> mv data/raw/concursos/*.json dados/concursos/
> git add dados/concursos/
> git rm -r data/raw/concursos/
> ```

- [ ] **Passo 3:** Mover processado

```bash
git mv data/processed/all_draws.json dados/processado/all_draws.json
```

- [ ] **Passo 4:** Mover banco

```bash
git mv data/lotofacil.db dados/lotofacil.db
```

- [ ] **Passo 5:** Deletar `data/` vazio

```bash
[ -d data/raw ] && rmdir data/raw
[ -d data/processed ] && rmdir data/processed
[ -d data ] && rmdir data
```

- [ ] **Passo 6:** Validar paths

```bash
ls dados/
ls dados/concursos/ | wc -l    # total JSONs
ls dados/processado/
ls -lh dados/lotofacil.db
```

- [ ] **Passo 7:** Smoke — verificar que CLI continua lendo

```bash
lotofacil dados status
```

Esperado: total de sorteios continua igual (mesma base, novo path).

`infra/config.py` (criado na onda 2 task 06) já aponta para `DADOS_DIR = PROJETO_RAIZ / "dados"`, então deve funcionar sem mais alterações.

- [ ] **Passo 8:** Testes

```bash
pytest
```

- [ ] **Passo 9:** Commit

```bash
git add -A
git commit -m "chore(dados): consolida inputs em dados/

- data/raw/concursos/*.json → dados/concursos/
- data/processed/all_draws.json → dados/processado/
- data/lotofacil.db → dados/lotofacil.db
- data/ deletada (vazia)

Symlink dados/ → ~/lotofacil-dados/ preservado (decisão de commit
abc0cfc). infra/config.py já aponta para o novo path."
```
