# Task 7.3 — Consolidar `saida/predicoes/` e `saida/relatorios/`

**Onda:** 7 — Pastas físicas
**Prioridade:** média
**Tempo estimado:** ~10 min
**Depende de:** 7.2

## Objetivo

Mover `output/predictions/` para `saida/predicoes/` e `output/reports/` para `saida/relatorios/`. Deletar `output/` (deve estar vazia após esta task e a anterior).

## Arquivos envolvidos

**Mover:**

| De | Para |
|---|---|
| `output/predictions/*` | `saida/predicoes/` |
| `output/reports/*` | `saida/relatorios/` |

**Deletar:**
- `output/predictions/`
- `output/reports/`
- `output/` (vazia)

## Dependências

- 7.2

## Critérios de aceite

- [ ] `ls saida/predicoes/` lista as predições antigas
- [ ] `ls saida/relatorios/` lista relatórios HTML / KPI
- [ ] `output/` não existe mais
- [ ] `pytest` passa

## Passos detalhados

- [ ] **Passo 1:** Inspecionar fontes

```bash
ls -la output/predictions/ 2>/dev/null
ls -la output/reports/ 2>/dev/null
```

- [ ] **Passo 2:** Garantir destinos

```bash
mkdir -p saida/predicoes saida/relatorios
```

- [ ] **Passo 3:** Mover predictions

```bash
for f in output/predictions/*; do
    [ -f "$f" ] && git mv "$f" "saida/predicoes/$(basename "$f")"
done
[ -d output/predictions ] && rmdir output/predictions
```

- [ ] **Passo 4:** Mover reports

```bash
for f in output/reports/*; do
    [ -f "$f" ] && git mv "$f" "saida/relatorios/$(basename "$f")"
done
[ -d output/reports ] && rmdir output/reports
```

- [ ] **Passo 5:** Deletar `output/`

```bash
[ -d output ] && rmdir output
```

- [ ] **Passo 6:** Validar

```bash
ls saida/predicoes/
ls saida/relatorios/
ls output/ 2>&1 | grep -i "no such"
```

- [ ] **Passo 7:** Smoke — verificar geração

```bash
lotofacil prever  # deve gerar em saida/jogos/ (predições novas — geram lá, não em saida/predicoes/)
# saida/predicoes/ é o destino "legado"; convencionar:
# - JSON com confianças por dezena (mapa) → saida/predicoes/
# - Predições no formato 11 dezenas → saida/jogos/predicao_*.json
```

> **Decisão:** mantém `saida/predicoes/` para histórico (relatórios analíticos das predições). Predições novas continuam indo em `saida/jogos/predicao_*.json` (formato apostável). Documentar isso em `infra/config.py` se ambíguo.

- [ ] **Passo 8:** Testes

```bash
pytest
```

- [ ] **Passo 9:** Commit

```bash
git add -A
git commit -m "chore(saida): consolida output/{predictions,reports} → saida/{predicoes,relatorios}

- output/predictions/* → saida/predicoes/
- output/reports/* → saida/relatorios/
- output/ deletada (vazia)

infra/config.py.PREDICOES_DIR, RELATORIOS_DIR já apontam corretamente.

Convenção:
- saida/jogos/predicao_*.json — formato apostável (11 dezenas)
- saida/predicoes/* — relatórios analíticos (confiança por dezena)"
```
