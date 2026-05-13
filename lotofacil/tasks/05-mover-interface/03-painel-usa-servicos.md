# Task 5.3 — Painel passa a usar serviços (endpoints de leitura)

**Onda:** 5 — Mover interface + renomear CLI
**Prioridade:** alta
**Tempo estimado:** ~25 min
**Depende de:** 5.2

## Objetivo

Refatorar endpoints **de leitura** do painel (`/api/status`, `/api/games`, `/api/games/:f`, `/api/predictions`, `/api/models/status`) para chamarem diretamente os serviços `lotofacil.servicos.*` em vez das funções internas `_listar_jogos`, `_escanear_modelos`, `_info_ultimo_concurso` etc.

Endpoints **de ação** (`POST /api/generate`) continuam disparando subprocess (`_executar_comando`) para preservar streaming via SSE.

## Arquivos envolvidos

**Modificar:**
- `src/lotofacil/interface/painel/servidor.py`

**Remover (funções privadas que viraram serviços):**
- `_listar_jogos` → usar `listar_jogos_gerados`
- `_escanear_modelos` → usar `listar_modelos_treinados`
- `_info_ultimo_concurso` → usar `consultar_status_base`
- helper de listar predições → usar `listar_historico_predicoes`

## Dependências

- 5.2

## Critérios de aceite

- [ ] Endpoints continuam respondendo (`/api/status`, `/api/games`, `/api/predictions`, `/api/models/status`)
- [ ] JSON de resposta tem o **mesmo formato** documentado em `docs/PRD-dashboard.md` (contrato preservado)
- [ ] `servidor.py` não tem mais `_listar_jogos`, `_escanear_modelos`, `_info_ultimo_concurso` (substituídas)
- [ ] `pytest src/lotofacil/interface/painel/tests/test_servidor.py` passa

## Passos detalhados

- [ ] **Passo 1:** Mapear endpoints atuais

```bash
grep -n "@app.route" src/lotofacil/interface/painel/servidor.py
```

Confirmar 5 endpoints de leitura: `/api/status`, `/api/games`, `/api/games/:f`, `/api/predictions`, `/api/models/status`.

- [ ] **Passo 2:** Refatorar `/api/status`

```python
# ANTES (~10 linhas com _info_ultimo_concurso, glob, count):
@app.route("/api/status")
def status():
    last = _info_ultimo_concurso()
    total = sum(1 for _ in DADOS_DIR.glob("concurso_*.json"))
    games_count = sum(1 for _ in JOGOS_DIR.glob("*.json"))
    return jsonify({...})

# DEPOIS:
from lotofacil.servicos.consultar_status_base import consultar_status_base
from lotofacil.servicos.listar_jogos_gerados import listar_jogos_gerados

@app.route("/api/status")
def status():
    s = consultar_status_base()
    jogos = listar_jogos_gerados(limite=20)
    return jsonify({
        "last_concurso": {
            "concurso": s.ultimo_concurso,
            "data": s.ultimo_data.strftime("%d/%m/%Y") if s.ultimo_data else None,
        },
        "total_draws": s.total_sorteios,
        "games_count": len(jogos),
        "timestamp": datetime.utcnow().isoformat(timespec="milliseconds"),
    })
```

- [ ] **Passo 3:** Refatorar `/api/games`

```python
from lotofacil.servicos.listar_jogos_gerados import listar_jogos_gerados

@app.route("/api/games")
def games():
    jogos = listar_jogos_gerados(limite=20)
    return jsonify([
        {"filename": j.filename, "concurso": j.concurso, "size": j.size, "mtime": j.mtime}
        for j in jogos
    ])
```

- [ ] **Passo 4:** Refatorar `/api/games/<filename>`

```python
@app.route("/api/games/<filename>")
def get_game(filename):
    conteudo = listar_jogos_gerados(filename=filename)
    if not conteudo:
        abort(404)
    return jsonify(conteudo)
```

- [ ] **Passo 5:** Refatorar `/api/predictions`

```python
from lotofacil.servicos.listar_historico_predicoes import listar_historico_predicoes

@app.route("/api/predictions")
def predictions():
    grupos = listar_historico_predicoes(limite=50)
    return jsonify([
        {"concurso": g.concurso, "mtime": g.mtime, "abordagens": g.abordagens}
        for g in grupos
    ])
```

- [ ] **Passo 6:** Refatorar `/api/models/status`

```python
from lotofacil.servicos.listar_modelos_treinados import listar_modelos_treinados

@app.route("/api/models/status")
def models_status():
    modelos = listar_modelos_treinados()
    return jsonify([
        {
            "name": m.nome,
            "group": m.grupo,
            "size_mb": m.tamanho_mb,
            "trained_at": m.treinado_em,
            "epochs_trained": m.epocas,
            "val_loss_final": m.val_loss_final,
            "config": m.config,
        }
        for m in modelos
    ])
```

- [ ] **Passo 7:** Remover funções privadas obsoletas

```bash
# As funções _listar_jogos, _escanear_modelos, _info_ultimo_concurso
# perderam todos os usuários. Removê-las.
```

Editar `servidor.py` e deletar essas funções.

- [ ] **Passo 8:** Atualizar testes

`test_servidor.py` pode precisar de monkeypatching dos serviços em vez das funções internas. Ex:

```python
# ANTES:
@patch("lotofacil.interface.painel.servidor._listar_jogos")
# DEPOIS:
@patch("lotofacil.interface.painel.servidor.listar_jogos_gerados")
```

- [ ] **Passo 9:** Testes

```bash
pytest src/lotofacil/interface/painel/tests/test_servidor.py -v
pytest
```

- [ ] **Passo 10:** Smoke

```bash
python -m lotofacil.interface.painel.servidor &
PID=$!
sleep 2

curl -s localhost:5000/api/status | jq .
# Esperado: {"last_concurso": {...}, "total_draws": N, "games_count": N, "timestamp": "..."}

curl -s localhost:5000/api/games | jq .
curl -s localhost:5000/api/predictions | jq . | head -30
curl -s localhost:5000/api/models/status | jq . | head -30

kill $PID
```

- [ ] **Passo 11:** Validar contrato preservado

Comparar JSON antes/depois (se possível); senão validar com `jq` que as chaves esperadas estão presentes (ver `docs/PRD-dashboard.md` seção 7).

- [ ] **Passo 12:** Commit

```bash
git add -A
git commit -m "refactor(painel): endpoints de leitura usam serviços

Substitui funções privadas (_listar_jogos, _escanear_modelos, etc.) por
chamadas a:
- consultar_status_base()
- listar_jogos_gerados()
- listar_historico_predicoes()
- listar_modelos_treinados()

Contratos JSON dos endpoints preservados (documentados em
docs/PRD-dashboard.md seção 7). Endpoints de ação (POST /api/generate)
continuam via subprocess para manter SSE streaming.

CLI e painel agora consomem o mesmo código de orquestração."
```
