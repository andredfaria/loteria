# Quina — Dashboard Mínimo + Deploy EasyPanel (design)

Data: 2026-07-08

## Contexto

Com a Fase 1 (Fundação) da Quina concluída — coleta de dados, banco SQLite, CLI `quina dados atualizar`/`status` —, o usuário pediu para expor uma interface web e fazer o deploy no EasyPanel, no mesmo padrão já usado pela Lotofácil (`lotofacil/Dockerfile` + serviço no EasyPanel).

Diferente da Lotofácil, a Quina ainda não tem estatística avançada, modelos de ML, backtest ou geração de portfólio (essas são fases futuras do roadmap: Estatística/Features, Modelos ML, Backtest, Portfólio, CLI completa). O dashboard da Lotofácil expõe justamente esse tipo de conteúdo — não faz sentido replicá-lo agora, pois não há dados por trás.

Decisão: construir um **dashboard mínimo, somente com o que já existe** — status da coleta, frequência e atraso dos números, e um botão para disparar a sincronização — e fazer o deploy desse dashboard mínimo no EasyPanel. Frequência e atraso são calculados diretamente a partir dos concursos já persistidos no banco (SQLite), sem depender de nenhuma fase futura.

## Escopo

Dentro do escopo:
- Servidor Flask (`quina/src/quina/interface/painel/server.py`) com 4 rotas
- Página única (`static/dashboard.html`)
- Sem autenticação (dados de sorteio são públicos, nada sensível)
- `Dockerfile` + `entrypoint.sh` próprios da Quina
- Deploy como serviço separado no EasyPanel (independente do serviço da Lotofácil)

Fora do escopo (fica para fases futuras, quando existirem):
- Predições, status de modelos, treino, backtest, portfólio, alertas, leaderboard
- Autenticação/login
- Agendador (scheduler) para sincronização automática

## Arquitetura

```
quina/src/quina/interface/painel/
├── __init__.py
├── server.py            # Flask app, 4 rotas
└── static/
    └── dashboard.html    # página única, sem abas
quina/testes/integracao/test_server.py
quina/Dockerfile
quina/entrypoint.sh
```

### Rotas

- **`GET /`** — serve `static/dashboard.html`
- **`GET /api/status`** — `{"total_concursos": int, "ultimo_concurso": {"concurso": int, "data": str, "dezenas": [int]} | None}`. Usa `DatabaseManager().get_all_concursos()` / `get_latest_concurso()` (já existentes, Fase 1).
- **`GET /api/frequencia`** — `{"frequencia": {"1": int, ..., "80": int}, "total_concursos": int}`. Conta quantas vezes cada número 1–80 apareceu em `get_all_concursos()`.
- **`GET /api/atraso`** — `{"atraso": {"1": {"atraso": int, "ultimo_concurso": int|None}, ...}, "total_concursos": int}`. Mesma lógica do `api_dados_atraso` da Lotofácil (`lotofacil/src/lotofacil/interface/painel/server.py:935-977`), adaptada para 1–80: para cada número, quantos concursos se passaram desde a última aparição.
- **`POST /api/atualizar`** — chama `QuinaFetcher().sync_new_draws()` (Fase 1, já existente), retorna `{"novos": int}` em caso de sucesso, ou `{"error": str}` com status 500 em caso de exceção.

Todas as rotas de leitura tratam banco vazio (0 concursos) retornando estruturas zeradas/vazias, não erro.

### Frontend

Página única, sem abas, sem login:
- Cartão de status: total de concursos, último concurso (número, data, 5 dezenas)
- Botão "Atualizar dados" → `POST /api/atualizar` → recarrega os dados na tela ao concluir; desabilitado durante a chamada; mostra erro inline se falhar
- Grade/tabela de frequência dos números 1–80 (destaque visual para mais/menos sorteados)
- Tabela de atraso, ordenada do maior atraso pro menor

Fetch com tratamento de erro: se qualquer chamada falhar, mostra mensagem de erro no lugar do card correspondente, sem quebrar o restante da página.

## Dependências novas

`quina/pyproject.toml` ganha `flask>=3.0.0` e, como dependência opcional de produção (não `dev`), `gunicorn>=22.0.0` — nenhuma outra dependência nova (sem ML, sem pandas/numpy).

## Deploy — Docker + EasyPanel

### `quina/Dockerfile`

Modelo do `lotofacil/Dockerfile`, mais enxuto (sem `gcc`/`libgomp1`, que existem lá só por causa de TensorFlow/scikit-learn):

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e .
RUN mkdir -p dados saida
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENV PYTHONPATH="/app/src:${PYTHONPATH}"
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/status')" || exit 1
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "quina.interface.painel.server:app", \
     "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", \
     "--timeout", "600", "--access-logfile", "-", "--error-logfile", "-"]
```

### `quina/entrypoint.sh`

```bash
#!/bin/bash
set -e
mkdir -p /app/dados /app/saida
if ! ls /app/dados/concurso_*.json > /dev/null 2>&1; then
    echo "[entrypoint] Dados vazios. Use o botão 'Atualizar dados' no painel ou rode 'quina dados atualizar'."
fi
exec "$@"
```

### Configuração no EasyPanel

Novo serviço, **separado** do serviço existente da Lotofácil (projetos independentes, sem dependência entre si):

| Campo | Valor |
|-------|-------|
| Build Context | `quina` |
| Dockerfile Path | `Dockerfile` |
| Porta | `5000` |
| Volume | montar em `/app/dados` (persiste `quina.db` + `concurso_*.json` entre deploys — sem isso, todo o histórico coletado se perde a cada redeploy) |

Dentro do container, `DADOS_DIR` (de `quina.infra.config`) resolve para `/app/dados` — um diretório normal, não symlink (o symlink pra `~/quina-dados/` é só convenção do ambiente de desenvolvimento local).

Primeira execução: banco vazio. Usuário clica "Atualizar dados" no painel (ou roda `quina dados atualizar` dentro do container) para popular o histórico completo via API da Caixa.

## Testes

`quina/testes/integracao/test_server.py`, usando o test client do Flask (`app.test_client()`):
- `/api/status` com banco vazio e com concursos (via `DatabaseManager` de teste apontando pro `tmp_path`, mesmo padrão de monkeypatch já usado em `test_cli_dados.py`)
- `/api/frequencia` e `/api/atraso` calculados contra concursos conhecidos, valores conferidos manualmente
- `/api/atualizar` sucesso (mock de `QuinaFetcher.sync_new_draws` retornando N) e falha (mock levantando exceção → 500)
- `/` retorna o HTML da página

## Fora de escopo (reforço)

Predições, modelos, backtest, portfólio, autenticação, scheduler — tudo isso entra quando as fases correspondentes do roadmap existirem.
