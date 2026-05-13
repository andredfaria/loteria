# Task 7.5 — Consolidar `saida/jogos/`

**Onda:** 7 — Pastas físicas
**Prioridade:** média
**Tempo estimado:** ~5 min
**Depende de:** 7.4

## Objetivo

Mesclar `saida/jogos_otimizados/` e `saida/sugestao/` em `saida/jogos/`, preservando os arquivos com nomes únicos (sufixar quando necessário). Deletar as duas pastas merged.

## Arquivos envolvidos

**Mover:**

| De | Para |
|---|---|
| `saida/jogos_otimizados/jogos_otimizados.json` | `saida/jogos/jogos_otimizados.json` |
| `saida/sugestao/sugestao_*.json` | `saida/jogos/sugestao_*.json` |
| `saida/sugestao/sugestao_*.txt` | `saida/jogos/sugestao_*.txt` |

**Deletar:**
- `saida/jogos_otimizados/`
- `saida/sugestao/`

## Dependências

- 7.4

## Critérios de aceite

- [ ] `saida/jogos_otimizados/` não existe
- [ ] `saida/sugestao/` não existe
- [ ] `saida/jogos/` contém todos os arquivos (originais + os mesclados)
- [ ] Painel `/api/games` lista os arquivos certos
- [ ] `pytest` passa

## Passos detalhados

- [ ] **Passo 1:** Inspecionar fontes

```bash
ls saida/jogos_otimizados/
ls saida/sugestao/
```

- [ ] **Passo 2:** Mover

```bash
# jogos_otimizados (1 arquivo)
for f in saida/jogos_otimizados/*; do
    [ -f "$f" ] && git mv "$f" "saida/jogos/$(basename "$f")"
done
[ -d saida/jogos_otimizados ] && rmdir saida/jogos_otimizados

# sugestao (vários arquivos: sugestao_3648.json, sugestao_3648.txt, etc.)
for f in saida/sugestao/*; do
    [ -f "$f" ] && git mv "$f" "saida/jogos/$(basename "$f")"
done
[ -d saida/sugestao ] && rmdir saida/sugestao
```

- [ ] **Passo 3:** Validar

```bash
ls saida/
# Esperado: jogos, predicoes, modelos, relatorios, experimentos, logs (logs ainda na raiz; task 7.6)

ls saida/jogos/ | head -10
```

- [ ] **Passo 4:** Smoke

```bash
lotofacil painel &
PID=$!
sleep 2
curl -s localhost:5000/api/games | jq '.[] | .filename' | head -10
kill $PID
```

- [ ] **Passo 5:** Testes

```bash
pytest
```

- [ ] **Passo 6:** Commit

```bash
git add -A
git commit -m "chore(jogos): consolida saida/jogos_otimizados + saida/sugestao em saida/jogos/

- jogos_otimizados.json → saida/jogos/jogos_otimizados.json
- sugestao_*.{json,txt} → saida/jogos/sugestao_*.{json,txt}

Painel /api/games agora vê tudo no mesmo lugar."
```
