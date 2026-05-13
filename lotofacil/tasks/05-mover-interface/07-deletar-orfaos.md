# Task 5.7 — Deletar resíduos órfãos das ondas anteriores

**Onda:** 5 — Mover interface + renomear CLI
**Prioridade:** alta
**Tempo estimado:** ~10 min
**Depende de:** 5.6

## Objetivo

Deletar os diretórios `src/` órfãos que ficaram esvaziados após as ondas 3-5: nada mais importa deles, podem ir para o lixo.

## Diretórios alvo

| Caminho | Razão |
|---|---|
| `src/lotofacil_ml/` | Conteúdo canonical movido para `infra/` na onda 3 |
| `src/strategies/` | Movido para `infra/estrategias/` na onda 3 task 5 |
| `src/data/` | Duplicatas órfãs (canonical foi lotofacil_ml) |
| `src/core/` | Conteúdo (`Draw`, `Prediction`) portado para `dominio/entidades.py` na onda 2 |
| `src/features/` | Versão órfã v2.0 (canonical foi lotofacil_ml) |
| `src/models/` | Versão órfã v2.0 |
| `src/evaluation/` | Versão órfã (exceto `comparison.py`, já movido na onda 3 task 4) |
| `src/models_saved/` | Será movido para `saida/modelos/` na onda 7 — NÃO deletar aqui |

## Arquivos envolvidos

**Deletar (recursive):**
- `src/lotofacil_ml/`
- `src/strategies/` (se ainda existe)
- `src/data/`
- `src/core/`
- `src/features/`
- `src/models/`
- `src/evaluation/`

**Não tocar:**
- `src/lotofacil/` (o pacote novo)
- `src/models_saved/` (saída de treinos — onda 7)
- `src/lotofacil_lab/` (move na onda 6)
- `src/lotofacil.db` (já deletado na onda 1 task 2)

## Dependências

- 5.6

## Critérios de aceite

- [ ] `find src -maxdepth 1 -type d` retorna apenas: `src`, `src/lotofacil`, `src/lotofacil_lab`, `src/models_saved` (e talvez `__pycache__`)
- [ ] `pip install -e .` ainda funciona
- [ ] `lotofacil dados status` funciona
- [ ] `lotofacil prever` funciona
- [ ] `pytest` passa

## Passos detalhados

- [ ] **Passo 1:** Verificar que ninguém importa desses diretórios

```bash
for dir in lotofacil_ml strategies data core features models evaluation; do
    echo "=== $dir ==="
    grep -rn "from $dir\.\|from src.$dir\|import $dir" src/lotofacil/ 2>/dev/null
done
```

Esperado: 0 resultados (todos os imports foram atualizados nas ondas 3 e 4).

- [ ] **Passo 2:** Verificar consumidores externos (lab)

```bash
grep -rn "from lotofacil_ml\|from strategies\|from data\.\|from core\.\|from features\.\|from models\.\|from evaluation\." src/lotofacil_lab/
```

Se aparecer algo no lab, atualizar para `lotofacil.infra.*` ANTES de deletar. Lab será movido inteiro na onda 6 mas precisa dos canônicos durante a onda 5.

- [ ] **Passo 3:** Deletar

```bash
git rm -rf src/lotofacil_ml/ 2>/dev/null
git rm -rf src/strategies/ 2>/dev/null
git rm -rf src/data/ 2>/dev/null
git rm -rf src/core/ 2>/dev/null
git rm -rf src/features/ 2>/dev/null
git rm -rf src/models/ 2>/dev/null
git rm -rf src/evaluation/ 2>/dev/null
```

- [ ] **Passo 4:** Limpar caches

```bash
find src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

- [ ] **Passo 5:** Validar estrutura

```bash
find src -maxdepth 1 -type d
# Esperado: src, src/lotofacil, src/lotofacil_lab, src/models_saved (e talvez __pycache__)
```

- [ ] **Passo 6:** Reinstalar (sanidade)

```bash
pip install -e .
```

- [ ] **Passo 7:** Testes

```bash
pytest
```

- [ ] **Passo 8:** Smoke completo

```bash
lotofacil dados status
lotofacil prever
lotofacil portfolio --jogos 3
lotofacil modelo treinar  # ou erra DB vazio — esperado
lotofacil lab ablacao --n-test 5
lotofacil painel &
sleep 2
curl -s localhost:5000/api/status | jq .
kill %1
```

- [ ] **Passo 9:** Commit

```bash
git add -A
git commit -m "chore: deleta resíduos órfãos de src/

Após movimentações das ondas 3-5, estes diretórios não têm mais
consumidores no projeto:

- src/lotofacil_ml/   → conteúdo em src/lotofacil/infra/
- src/strategies/     → conteúdo em src/lotofacil/infra/estrategias/
- src/data/           → duplicatas (canonical foi para infra/dados/)
- src/core/           → conteúdo em src/lotofacil/dominio/
- src/features/       → versão órfã (canonical foi lotofacil_ml/features)
- src/models/         → versão órfã
- src/evaluation/     → versão órfã (comparison.py único já movido)

Última task da onda 5. src/ agora contém apenas:
  src/lotofacil/      (pacote novo, alvo do refactor)
  src/lotofacil_lab/  (move na onda 6)
  src/models_saved/   (consolida em saida/modelos/ na onda 7)"
```
