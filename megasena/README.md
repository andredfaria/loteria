# Mega-Sena

Sistema de coleta, análise estatística e predição ML para a Mega-Sena (6 números de 1–60).

> **Aviso:** Ferramenta de estudo estatístico. Loteria é jogo de azar — cada sorteio é um evento aleatório independente. Nenhum modelo supera significativamente o aleatório.

---

## Instalação

```bash
cd loteria/megasena
python -m venv venv && source venv/bin/activate
pip install -e ".[dev,ml]"
```

Requer Python ≥ 3.11.

---

## CLI — Uso Rápido

```bash
megasena dados atualizar       # sincroniza concursos da API (bulk) → SQLite + JSON
megasena dados status          # total, último concurso, dezenas
megasena modelo treinar        # treina ensemble (Frequency + ML + Probabilistic)
megasena modelo prever         # jogo de 6 números para o próximo concurso
megasena modelo probas         # probabilidade por dezena
megasena modelo backtest       # validação walk-forward vs. aleatório
```

---

## Dashboard Web

Flask + Gunicorn na porta **5000**. O painel falha fechado: defina
`DASHBOARD_PASSWORD` (login por senha, recomendado) ou `DASHBOARD_PUBLICO=1`
(sem senha, confirmado explicitamente) — sem uma delas o processo não sobe.
`DASHBOARD_AUTH_SECRET` fixa a chave de sessão; sem ela, todo restart derruba
os logins.

```bash
DASHBOARD_PASSWORD=... gunicorn megasena.interface.painel.server:app \
    --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 600
```

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/status` | Último concurso e totais |
| `GET` | `/api/frequencia` | Frequência por número (1–60) |
| `GET` | `/api/atraso` | Atraso por número |
| `POST` | `/api/atualizar` | Sincroniza novos concursos |
| `POST` | `/api/bolao/avaliar` | Avalia preço e probabilidade de um bolão |
| `GET` | `/comparar` | Tela de comparação de bolões |
| `POST` | `/api/bolao/comparar` | Ranqueia de 2 a 10 bolões por custo-benefício |

### Avaliador de bolão

Card **Avaliar bolão** no painel: informe o valor total do bolão (cota × nº de
cotas), a quantidade de apostas, as dezenas por aposta (6–20) e, opcionalmente,
o número de cotas. O cálculo segue
[`docs/guias/avaliacao-de-boloes.md`](../docs/guias/avaliacao-de-boloes.md):
converte tudo em combinações simples (R$ 6,00 cada), compara o valor cobrado com
o teto de 35% de taxa das lotéricas e mostra a chance de sena do bolão e de
quina/quadra por volante.

### Comparar bolões

Tela **`/comparar`** (link no card do avaliador): cadastre de 2 a 10 bolões,
cada um com nome, valor total, apostas, dezenas por aposta e cotas, e
compare-os lado a lado. O ranking segue o **custo cobrado por combinação
simples** (menor é melhor) e desempata por mais dezenas por volante. A tabela
também mostra taxa, valor da sua cota, sua parte do prêmio, chance de sena,
combinações e quina por volante; clique numa coluna para reordenar. O motivo
de o critério ser esse, e não a maior chance ou a cota mais barata, está na
seção 7 do guia. Lógica em `megasena.servicos.bolao.comparar_boloes`.

---

## Deploy com Docker (EasyPanel)

Build context `megasena`, Dockerfile `Dockerfile`, porta `5000`. Monte volumes
em `/app/dados` (SQLite + JSON dos concursos) e `/app/saida` (modelos) para
persistir entre deploys. Com o volume vazio, use o botão **Atualizar dados**
do painel — a primeira sincronização baixa o histórico completo.

```bash
docker build -t megasena-painel .
docker run -p 5000:5000 -e DASHBOARD_PASSWORD=... -e DASHBOARD_AUTH_SECRET=... \
    -v megasena_dados:/app/dados -v megasena_saida:/app/saida megasena-painel
```

---

## Arquitetura

```
src/megasena/
├── dominio/           # Entidades (Sorteio: 6 números 1-60), regras, exceções
├── infra/
│   ├── config.py      # Paths, API_MEGASENA, timeout/retry, constantes do jogo
│   ├── dados/         # api_caixa.py (fetcher bulk + incremental), banco.py (SQLite), leitor.py
│   ├── atributos/     # engenharia de features (frequência, atraso, coocorrência, tendência...)
│   ├── modelos/       # base_model, frequency_ensemble, ml_model, probabilistic, ensemble
│   └── geracao/       # optimizers.py (simulated annealing p/ jogo de 6 números)
├── servicos/          # bolao.py (avaliação e comparação de bolões)
└── interface/
    ├── cli/           # Typer CLI (megasena dados|modelo)
    └── painel/        # Flask dashboard (server.py + static/dashboard.html, comparar.html)
```

### Regras do jogo

| Propriedade | Valor |
|-------------|-------|
| Números por sorteio | 6 |
| Faixa de números | 1–60 |
| Total de combinações | C(60,6) = 50.063.860 |
| Probabilidade (6/6) | 1 em ~50 milhões |
| Faixas de premiação | 4, 5 e 6 acertos |

### API

`https://loteriascaixa-api.herokuapp.com/api/megasena`

| Endpoint | Uso |
|----------|-----|
| `GET /api/megasena` | Bulk — todos os concursos |
| `GET /api/megasena/latest` | Último concurso |
| `GET /api/megasena/{n}` | Concurso específico |

---

## Testes

```bash
source venv/bin/activate
pytest                        # todos os testes
pytest testes/unidade/ -v    # testes unitários
pytest testes/integracao/ -v  # testes de integração
```

---

## Licença

MIT — veja [../LICENSE](../LICENSE).