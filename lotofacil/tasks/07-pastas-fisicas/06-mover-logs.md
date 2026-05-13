# Task 7.6 — Mover `logs/` → `saida/logs/`

**Onda:** 7 — Pastas físicas
**Prioridade:** baixa
**Tempo estimado:** ~5 min
**Depende de:** 7.5

## Objetivo

Mover pasta `logs/` da raiz do projeto para `saida/logs/`, consolidando todos os outputs sob `saida/`.

## Arquivos envolvidos

**Mover:**
- `logs/*` → `saida/logs/`

**Modificar:**
- Qualquer config de logging que aponta para `logs/` direto

## Dependências

- 7.5

## Critérios de aceite

- [ ] `logs/` não existe na raiz
- [ ] `saida/logs/` contém os logs anteriores
- [ ] Novos comandos geram logs em `saida/logs/` (se já houver setup de logging)
- [ ] `pytest` passa

## Passos detalhados

- [ ] **Passo 1:** Inspecionar

```bash
ls -la logs/ 2>/dev/null
```

- [ ] **Passo 2:** Mover

```bash
mkdir -p saida/logs
for f in logs/*; do
    [ -f "$f" ] && git mv "$f" "saida/logs/$(basename "$f")"
done
[ -d logs ] && rmdir logs
```

- [ ] **Passo 3:** Verificar refs a `logs/` em código

```bash
grep -rn "Path.*logs\|/logs/\|'logs/'\|\"logs/\"" src/lotofacil/
```

Se aparecer hardcoded, atualizar para `LOGS_DIR` (já em `infra/config.py`).

- [ ] **Passo 4:** Testes

```bash
pytest
```

- [ ] **Passo 5:** Commit

```bash
git add -A
git commit -m "chore(logs): move logs/ → saida/logs/

Consolidação: todos os outputs vivem sob saida/.
infra/config.py.LOGS_DIR já aponta para saida/logs."
```
