# Task 2.1 — Criar estrutura de pastas do pacote `lotofacil/`

**Onda:** 2 — Esqueleto + domínio
**Prioridade:** alta
**Tempo estimado:** ~3 min
**Depende de:** 1.3

## Objetivo

Criar a estrutura de diretórios vazios do novo pacote `src/lotofacil/`, com `__init__.py` em cada camada. Nada de código real ainda — apenas o esqueleto que será preenchido pelas próximas tasks.

## Descrição técnica

Criar 5 sub-pastas top-level (camadas) + sub-pastas de capacidades dentro de `infra/`. Cada uma com `__init__.py` vazio.

## Arquivos envolvidos

**Criar:**

```
src/lotofacil/__init__.py
src/lotofacil/dominio/__init__.py
src/lotofacil/servicos/__init__.py
src/lotofacil/infra/__init__.py
src/lotofacil/infra/dados/__init__.py
src/lotofacil/infra/atributos/__init__.py
src/lotofacil/infra/modelos/__init__.py
src/lotofacil/infra/estrategias/__init__.py
src/lotofacil/infra/avaliacao/__init__.py
src/lotofacil/infra/geracao/__init__.py
src/lotofacil/infra/agendador/__init__.py
src/lotofacil/interface/__init__.py
src/lotofacil/interface/cli/__init__.py
src/lotofacil/interface/painel/__init__.py
src/lotofacil/experimentos/__init__.py
```

## Dependências

- Onda 1 completa

## Critérios de aceite

- [ ] `find src/lotofacil -type d` lista todas as 13 pastas
- [ ] `find src/lotofacil -name "__init__.py" | wc -l` retorna 15
- [ ] `python -c "import lotofacil; import lotofacil.dominio; import lotofacil.infra; import lotofacil.servicos; import lotofacil.interface; import lotofacil.experimentos"` funciona
- [ ] `pytest` passa (não acrescentou nada que quebre)

## Passos detalhados

- [ ] **Passo 1:** Criar as pastas

```bash
mkdir -p src/lotofacil/{dominio,servicos,infra/{dados,atributos,modelos,estrategias,avaliacao,geracao,agendador},interface/{cli,painel},experimentos}
```

- [ ] **Passo 2:** Criar `__init__.py` em cada uma

```bash
touch src/lotofacil/__init__.py
touch src/lotofacil/dominio/__init__.py
touch src/lotofacil/servicos/__init__.py
touch src/lotofacil/infra/__init__.py
touch src/lotofacil/infra/dados/__init__.py
touch src/lotofacil/infra/atributos/__init__.py
touch src/lotofacil/infra/modelos/__init__.py
touch src/lotofacil/infra/estrategias/__init__.py
touch src/lotofacil/infra/avaliacao/__init__.py
touch src/lotofacil/infra/geracao/__init__.py
touch src/lotofacil/infra/agendador/__init__.py
touch src/lotofacil/interface/__init__.py
touch src/lotofacil/interface/cli/__init__.py
touch src/lotofacil/interface/painel/__init__.py
touch src/lotofacil/experimentos/__init__.py
```

- [ ] **Passo 3:** Verificar estrutura

```bash
tree src/lotofacil/ -L 3
```

Esperado: árvore como descrita acima.

- [ ] **Passo 4:** Validar importabilidade

```bash
python -c "import lotofacil"
python -c "from lotofacil import dominio, servicos, infra, interface, experimentos"
python -c "from lotofacil.infra import dados, atributos, modelos, estrategias, avaliacao, geracao, agendador"
python -c "from lotofacil.interface import cli, painel"
```

Esperado: sem erros. (`conftest.py` já adiciona `src/` ao `sys.path`.)

- [ ] **Passo 5:** Testes

```bash
pytest
```

Esperado: pass.

- [ ] **Passo 6:** Commit

```bash
git add src/lotofacil/
git commit -m "feat(arq): cria esqueleto do pacote lotofacil/ com camadas

Estrutura nova:
- dominio/   — entidades, regras, exceções (a preencher nas próximas tasks)
- servicos/  — use cases (preenchido na onda 4)
- infra/     — implementações IO/ML (preenchido na onda 3)
- interface/ — CLI + painel (preenchido na onda 5)
- experimentos/ — lab (preenchido na onda 6)

Nada do código antigo movido — apenas adições. Próxima task implementa
dominio/entidades.py."
```
