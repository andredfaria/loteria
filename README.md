# Loteria — Análise Estatística de Loterias Brasileiras

Monorepo com cinco projetos Python independentes, que coletam os resultados das loterias da Caixa Econômica Federal e os analisam com estatística e Machine Learning.

> **Aviso:** Este projeto é para fins de estudo estatístico. Loteria é jogo de azar — cada sorteio é um evento aleatório independente. Nenhum sistema garante ganhos.

---

## Projetos

| Projeto | O que tem | Status |
|---------|-----------|--------|
| [lotofacil/](lotofacil/) | Sistema completo: coleta (com lua e clima), ML clássico e neural (clima + lua), portfólio de jogos, CLI e painel web | Ativo |
| [quina/](quina/) | Coleta, CLI, estratégias de jogo, ML e painel web | Ativo |
| [megasena/](megasena/) | Coleta, CLI, ML e painel web com avaliador e comparador de bolão | Ativo |
| [dia-de-sorte/](dia-de-sorte/) | Coleta, CLI e ML | Ativo |
| [super-sete/](super-sete/) | Coleta e CLI | Ativo |

Cada projeto é autônomo: tem o próprio `pyproject.toml`, o próprio ambiente virtual e a própria CLI (`lotofacil`, `quina`, `megasena`, `diadesorte` e `supersete`). Os comandos de cada um estão no `README.md` da pasta. A `dia-de-sorte` e a `super-sete` ainda guardam, na pasta do projeto, os scripts do começo (legado, serão portados para a CLI).

---

## Início rápido

Na raiz do repositório, com Python 3.11 ou mais novo (a CI e as imagens Docker usam o 3.12):

```bash
make instalar P=megasena                     # cria megasena/venv e instala o projeto com as ferramentas de teste
make testar P=megasena                       # roda o pytest do projeto
megasena/venv/bin/megasena dados atualizar   # baixa o histórico de concursos da API
make lint                                    # ruff check ., o mesmo gate da CI
```

Troque `megasena` por qualquer outro projeto (`lotofacil`, `quina`, `dia-de-sorte`, `super-sete`). Sem `P`, o `make testar` roda os cinco. O `make lint` precisa do `ruff` instalado (`pip install ruff`). `make ajuda` lista todos os alvos.

---

## Estrutura

```text
loteria/
├── lotofacil/            # coleta, ML clássico e neural, portfólio, CLI e painel
├── quina/                # coleta, CLI, estratégias, ML e painel
├── megasena/             # coleta, CLI, ML e painel com bolão
├── dia-de-sorte/         # coleta, CLI e ML
├── super-sete/           # coleta e CLI
├── docs/                 # documentação que vale para mais de um projeto
├── .github/              # CI (testes, lint, segurança, docker), templates e Dependabot
├── docker-compose.yml    # sobe os painéis de lotofacil, quina e megasena localmente
├── Makefile              # instalar, testar, lint e docker
├── ruff.toml             # configuração de lint compartilhada
└── CHANGELOG.md  CONTRIBUTING.md  CODE_OF_CONDUCT.md  SECURITY.md  LICENSE
```

Dentro de cada projeto, o código fica em `src/<pacote>/`, os testes em `testes/` e a configuração em `pyproject.toml`. Os três painéis também têm `Dockerfile` e `entrypoint.sh`. A documentação está indexada em [docs/README.md](docs/README.md).

O pacote `nucleo/`, com o código comum entre as loterias, chega na próxima etapa da reorganização. Por enquanto esse código vive repetido em cada projeto.

---

## Dados

Os projetos baixam os resultados da API pública [loteriascaixa-api](https://github.com/guto-alves/loterias-api), pelo espelho `https://loteriascaixa-api.herokuapp.com/api/<loteria>` (`lotofacil`, `quina`, `megasena`, `diadesorte` e `supersete`). É um serviço de terceiros, sem garantia oficial da Caixa; a estrutura da resposta está em [docs/api-externa.md](docs/api-externa.md).

Cada projeto baixa o histórico de concursos com `<pacote> dados atualizar` (na primeira vez, tudo; depois, só os concursos novos) e mostra o que já tem com `<pacote> dados status`. Os dados ficam em `<projeto>/dados/`.

**Nenhum histórico é versionado.** `dados/` e `saida/` de cada projeto estão no `.gitignore`. Os testes não precisam do histórico: usam `<projeto>/testes/fixtures/` ou dados criados no próprio teste, e os poucos que dependem do histórico local são pulados quando ele não existe.

---

## Painéis e deploy

Os projetos lotofacil, quina e megasena têm, cada um, um painel web (Flask, servido pelo Gunicorn na porta 5000 do container) com `Dockerfile` próprio, publicado no EasyPanel. O [`docker-compose.yml`](docker-compose.yml) da raiz sobe os três localmente.

Os painéis **falham fechado**: sem `DASHBOARD_PASSWORD` (login por senha) ou `DASHBOARD_PUBLICO=1` (painel sem senha, confirmado de propósito), o painel não inicia. A rota `/healthz`, que responde sem login, serve ao health check do container.

A configuração do EasyPanel, os volumes, as variáveis de ambiente e o passo a passo local estão em [docs/deploy.md](docs/deploy.md).

---

## Contribuir, segurança e licença

- [CONTRIBUTING.md](CONTRIBUTING.md): os princípios do projeto, como montar o ambiente e o que fazer antes de abrir um PR.
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md): como esperamos que a comunidade se comporte.
- [SECURITY.md](SECURITY.md): como reportar uma vulnerabilidade e como implantar com segurança.
- [CHANGELOG.md](CHANGELOG.md): o que mudou.
- Licença MIT — veja [LICENSE](LICENSE).
