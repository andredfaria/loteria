# Loteria — Análise Estatística de Loterias Brasileiras

Monorepo com sistemas de análise estatística, geração de jogos e Machine Learning para loterias da Caixa Econômica Federal.

> **Aviso:** Este projeto é para fins de estudo estatístico. Loteria é jogo de azar — cada sorteio é um evento aleatório independente. Nenhum sistema garante ganhos.

---

## Subprojetos

| Projeto | Descrição | Status |
|---------|-----------|--------|
| [lotofacil/](lotofacil/) | Sistema completo: coleta, análise, ML, dashboard web | Ativo |
| [quina/](quina/) | Coleta, CLI, dashboard Flask, ML ensemble | Ativo |
| [dia-de-sorte/](dia-de-sorte/) | Pacote estruturado: coleta + CLI + análise estatística | Ativo |
| [super-sete/](super-sete/) | Pacote estruturado: coleta + CLI + análise por coluna | Ativo |
| [megasena/](megasena/) | Em desenvolvimento | Planejado |

Cada subprojeto é autônomo com seu próprio `pyproject.toml` e ambiente virtual.

---

## Lotofácil

Sistema mais completo. Pipeline de ponta a ponta: coleta → análise → ML → predição → dashboard web.

```bash
cd lotofacil && source venv/bin/activate && pip install -e .

lotofacil dados atualizar       # sincroniza sorteios da API
lotofacil modelo treinar        # treina ensemble clássico
lotofacil prever                # gera predição para o próximo concurso
```

Veja [lotofacil/README.md](lotofacil/README.md).

---

## Quina

Coleta, CLI, modelos de ML e dashboard Flask.

```bash
cd quina && source venv/bin/activate && pip install -e .

quina dados atualizar           # sincroniza concursos da API
quina dados status              # status do banco local
quina modelo treinar            # walk-forward backtest
quina prever prever             # predição ensemble
```

Veja [quina/README.md](quina/README.md).

---

## Dia de Sorte

Pacote estruturado com CLI e API:

```bash
cd dia-de-sorte && source venv/bin/activate && pip install -e .

diadesorte dados atualizar      # sincroniza concursos (bulk)
diadesorte dados status         # total, último, dezenas, mês da sorte
```

Veja [dia-de-sorte/README.md](dia-de-sorte/README.md). Scripts legados em `analisar_diadesorte.py`.

---

## Super Sete

Pacote estruturado com CLI:

```bash
cd super-sete && source venv/bin/activate && pip install -e .

supersete dados atualizar       # sincroniza concursos (bulk)
supersete dados status          # total, último, dígitos
```

Veja [super-sete/README.md](super-sete/README.md). Scripts legados em `analise_estatistica.py`.

---

## API Caixa

Todos os projetos consomem a mesma API:

```
https://loteriascaixa-api.herokuapp.com/api/<loteria>
https://loteriascaixa-api.herokuapp.com/api/<loteria>/latest
https://loteriascaixa-api.herokuapp.com/api/<loteria>/<concurso>
```

`<loteria>`: `lotofacil`, `megasena`, `quina`, `supersete`, `diadesorte`, `duplasena`, `lotomania`, `timemania`, `maismilionaria`, `federal`

---

## Dados

Cada projeto contém apenas **amostras** (`dados/sample/` ou `testes/fixtures/`) com os sorteios mais recentes. O dataset completo é baixado via CLI e ignorado pelo `.gitignore`.

---

## Deploy (EasyPanel)

Os projetos com dashboard web (lotofacil, quina) possuem `Dockerfile` próprio:

| Projeto | Build Context | Dockerfile Path | Port |
|---------|---------------|------------------|------|
| lotofacil | `lotofacil` | `Dockerfile` | `5000` |
| quina | `quina` | `Dockerfile` | `5000` |

> O `Dockerfile` na raiz do repositório é legado e **não deve ser usado**.

### Variáveis de ambiente obrigatórias (lotofacil)

O dashboard do **lotofacil** falha fechado: sem `DASHBOARD_PASSWORD` (login
por senha) ou `DASHBOARD_PUBLICO=1` (painel público, sem senha, confirmado
explicitamente), o container não sobe. `DASHBOARD_AUTH_SECRET` fixa a chave
de sessão (sem ela, restart/redeploy derruba todas as sessões de login).
`DASHBOARD_MAX_JOBS` (padrão `2`) limita quantos jobs pesados — geração,
treino, backtest — podem rodar ao mesmo tempo antes de responder `429`.
Detalhes em [lotofacil/README.md](lotofacil/README.md#autenticação-e-variáveis-de-ambiente).

O dashboard do **quina** ainda não tem autenticação — não exponha sua porta
diretamente à internet sem um proxy/tunnel com autenticação na frente.

---

## Licença

MIT — veja [LICENSE](LICENSE).
