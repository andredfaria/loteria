# Task 7.2 — Consolidar `saida/modelos/`

**Onda:** 7 — Pastas físicas
**Prioridade:** média
**Tempo estimado:** ~10 min
**Depende de:** 7.1

## Objetivo

Mover modelos treinados de `output/models/` e `src/models_saved/` para `saida/modelos/` (consolidação). Deletar `src/models_saved/` (gitignored — apenas pasta física a remover).

## Arquivos envolvidos

**Mover:**

| De | Para |
|---|---|
| `output/models/*.keras` | `saida/modelos/` |
| `output/models/*.joblib` | `saida/modelos/` |
| `output/models/*.meta.json` | `saida/modelos/` |
| `src/models_saved/*` | `saida/modelos/` (se houver conflito de nome, sufixar) |

**Deletar (vazias após mover):**
- `output/models/`
- `src/models_saved/`

## Dependências

- 7.1

## Critérios de aceite

- [ ] `ls saida/modelos/` lista todos os modelos (.keras, .joblib)
- [ ] `output/models/` não existe
- [ ] `src/models_saved/` não existe
- [ ] `lotofacil modelo treinar` continua salvando em `saida/modelos/` (já aponta lá via `infra/config.py`)
- [ ] `curl localhost:5000/api/models/status` lista modelos corretos
- [ ] `pytest` passa

## Passos detalhados

- [ ] **Passo 1:** Inspecionar fontes

```bash
ls -la output/models/ 2>/dev/null
ls -la src/models_saved/ 2>/dev/null
```

- [ ] **Passo 2:** Garantir destino

```bash
mkdir -p saida/modelos
```

- [ ] **Passo 3:** Mover de `output/models/`

```bash
# .keras files
for f in output/models/*.keras; do
    [ -f "$f" ] && git mv "$f" "saida/modelos/$(basename "$f")"
done

# .joblib files
for f in output/models/*.joblib; do
    [ -f "$f" ] && git mv "$f" "saida/modelos/$(basename "$f")"
done

# .meta.json files
for f in output/models/*.meta.json; do
    [ -f "$f" ] && git mv "$f" "saida/modelos/$(basename "$f")"
done
```

- [ ] **Passo 4:** Mover de `src/models_saved/`

```bash
# Gitignored normalmente — usar mv direto
for f in src/models_saved/*; do
    [ -f "$f" ] && mv "$f" "saida/modelos/$(basename "$f")"
done
```

Se houver conflito de nome (mesmo arquivo em ambos), confirmar qual é mais recente:

```bash
ls -lt saida/modelos/ | head -5
```

- [ ] **Passo 5:** Limpar pastas vazias

```bash
rmdir output/models/ 2>/dev/null
rmdir src/models_saved/ 2>/dev/null
```

(`output/` ainda tem `predictions/` e `reports/` — não deletar inteira ainda.)

- [ ] **Passo 6:** Validar

```bash
ls saida/modelos/
ls output/ src/ 2>/dev/null | grep -E "models_saved|models$"  # nada
```

- [ ] **Passo 7:** Smoke

```bash
lotofacil modelo treinar  # salva em saida/modelos/
ls saida/modelos/
```

Ou se não tem dados:

```bash
curl -s localhost:5000/api/models/status | jq . | head -30
```

Antes precisa subir o painel — `lotofacil painel &`.

- [ ] **Passo 8:** Testes

```bash
pytest
```

- [ ] **Passo 9:** Commit

```bash
git add -A
git commit -m "chore(modelos): consolida modelos treinados em saida/modelos/

- output/models/* → saida/modelos/
- src/models_saved/* → saida/modelos/

Eliminadas duas pastas redundantes (output/models, src/models_saved).
infra/config.py.MODELOS_DIR já aponta para saida/modelos."
```
