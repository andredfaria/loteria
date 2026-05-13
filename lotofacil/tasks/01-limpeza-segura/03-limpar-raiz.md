# Task 1.3 — Limpar artefatos da raiz

**Onda:** 1 — Limpeza segura
**Prioridade:** alta
**Tempo estimado:** ~5 min
**Depende de:** 1.2

## Objetivo

Remover artefatos vazados para a raiz do projeto: arquivos de portfólio gerados (`portfolio_*.txt/json`), metadados de build (`lotofacil_prediction.egg-info/`), e caches de pytest/Python (`.pytest_cache/`, `__pycache__/` na raiz). Não remover `venv/`, `.venv/` (ambientes virtuais do dev).

## Descrição técnica

- Artefatos de portfólio na raiz (`portfolio_3679.txt`, `portfolio_3681.json`, `portfolio_3681.txt`, `portfolio_3681_dual.json`, `portfolio_3681_dual.txt`) parecem outputs de execuções antigas que vazaram para a raiz. Preservar histórico em `saida/jogos/` (alguns podem já existir lá; comparar) ou descartar.
- `lotofacil_prediction.egg-info/` é regenerado por `pip install -e .` — não precisa estar no git.
- `__pycache__/`, `.pytest_cache/` são caches.

## Arquivos envolvidos

**Mover/deletar (decidir caso a caso):**

| Arquivo | Operação |
|---|---|
| `portfolio_3679.txt` | comparar com `saida/jogos/portfolio_3679.*`; se duplicado, deletar; senão mover |
| `portfolio_3681.json` | idem |
| `portfolio_3681.txt` | idem |
| `portfolio_3681_dual.json` | mover para `saida/jogos/` (nome único) |
| `portfolio_3681_dual.txt` | idem |

**Deletar definitivamente:**
- `lotofacil_prediction.egg-info/`
- `__pycache__/` (raiz)
- `.pytest_cache/` (raiz)

**Atualizar `.gitignore` para garantir que não voltam:**

```gitignore
# Artefatos da raiz que não devem voltar
/portfolio_*.txt
/portfolio_*.json
/lotofacil_prediction.egg-info/
/.pytest_cache/
__pycache__/
```

## Dependências

- Task 1.2 (órfãos removidos)

## Critérios de aceite

- [ ] `ls portfolio_*.txt portfolio_*.json 2>&1 | grep -i "no such"`
- [ ] `ls lotofacil_prediction.egg-info __pycache__ .pytest_cache 2>&1 | grep -i "no such"`
- [ ] `.gitignore` contém regras para os padrões acima
- [ ] Conteúdo relevante de portfolio preservado em `saida/jogos/`
- [ ] `pytest` passa (vai recriar `.pytest_cache/` — gitignored)
- [ ] `pip install -e .` ainda funciona (regenera `egg-info` — gitignored)

## Passos detalhados

- [ ] **Passo 1:** Inspecionar portfólios da raiz

```bash
ls -la portfolio_*.txt portfolio_*.json 2>/dev/null
ls -la saida/jogos/portfolio_*.* 2>/dev/null
```

- [ ] **Passo 2:** Para cada portfolio_*.{txt,json} na raiz, decidir

```bash
# Exemplo para portfolio_3681.json:
if [ -f "saida/jogos/portfolio_3681.json" ]; then
  diff portfolio_3681.json saida/jogos/portfolio_3681.json
  # se idênticos, deletar:
  git rm portfolio_3681.json
else
  git mv portfolio_3681.json saida/jogos/portfolio_3681.json
fi
```

Repetir para cada arquivo.

- [ ] **Passo 3:** Mover os `_dual` (provavelmente único)

```bash
git mv portfolio_3681_dual.json saida/jogos/ 2>/dev/null
git mv portfolio_3681_dual.txt saida/jogos/ 2>/dev/null
```

- [ ] **Passo 4:** Deletar artefatos de build/cache

```bash
git rm -rf lotofacil_prediction.egg-info/ 2>/dev/null || rm -rf lotofacil_prediction.egg-info/
rm -rf __pycache__ .pytest_cache
```

- [ ] **Passo 5:** Atualizar `.gitignore`

Verificar conteúdo atual:

```bash
cat .gitignore
```

Adicionar entradas faltantes (não duplicar se já existem):

```bash
{
echo ""
echo "# Refactor onda 1 — não permitir voltar"
echo "/portfolio_*.txt"
echo "/portfolio_*.json"
echo "/lotofacil_prediction.egg-info/"
echo "/.pytest_cache/"
echo "__pycache__/"
} >> .gitignore
```

(Idempotente: rodar `sort -u .gitignore > .gitignore.new && mv .gitignore.new .gitignore` depois se preocupar com duplicatas.)

- [ ] **Passo 6:** Verificar estado

```bash
ls portfolio_* lotofacil_prediction.egg-info __pycache__ .pytest_cache 2>&1
git status --short
```

- [ ] **Passo 7:** Testes + smoke

```bash
pytest
lotofacil dados status
pip install -e .                # regenera egg-info (gitignored)
```

- [ ] **Passo 8:** Commit

```bash
git commit -m "chore: limpa artefatos vazados para a raiz

- portfolio_*.{txt,json} movidos para saida/jogos/ ou removidos se duplicados
- lotofacil_prediction.egg-info removido (regenerado por pip install -e .)
- __pycache__/, .pytest_cache/ removidos
- .gitignore atualizado para evitar recidiva

Última task da onda 1 — limpeza segura completa."
```
