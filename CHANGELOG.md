# Changelog

Este projeto segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e ainda não tem versões publicadas.

## [Não publicado]

### Adicionado

- Rota `GET /healthz` nos painéis de lotofacil, quina e megasena. Responde `200` com `{"status": "ok"}`, sem login e sem acessar banco ou dados.
- Novo `docker-compose.yml` na raiz, que substitui o legado e sobe os três painéis: lotofacil na porta 5001, quina na 5002 e megasena na 5003.
- Workflow de CI `docker.yml`, que monta as imagens dos três painéis em todo PR e em todo push na `main` que alterem esses projetos. Não publica nada.
- Dois passos novos no `lint.yml`: um falha se algum arquivo versionado tiver acento, espaço ou `:` no nome; o outro (`.github/scripts/verificar_links.py`) falha se algum link relativo de um `.md` versionado apontar para um arquivo que não existe.
- `CODE_OF_CONDUCT.md`, em português, adaptado do Contributor Covenant 2.1.
- Templates de issue (bug e melhoria, com um atalho para a política de segurança) e de pull request, em `.github/`.
- `.github/dependabot.yml`: o Dependabot passa a cobrir as GitHub Actions e a acompanhar as dependências pip dos cinco projetos. Como essas dependências usam faixas `>=`, ele quase não abre PR de versão para pip; a varredura de vulnerabilidades continua sendo a do `pip-audit` na CI.
- `Makefile` na raiz, com os alvos `ajuda`, `instalar`, `testar`, `lint` e `docker`.
- `.editorconfig`.
- `docs/README.md`, o índice da documentação, e `docs/deploy.md`, com a configuração do EasyPanel, os volumes, as variáveis de ambiente e o passo a passo para subir os painéis com o Docker Compose.

### Alterado

- Quem usava localmente o `lotofacil/docker-compose.yml` não reaproveita os volumes: o projeto Compose agora é o da raiz do repositório e o volume dos modelos neurais passou de `lotofacil_lab_models` para `lotofacil_modelos_lab`. Os volumes do EasyPanel não mudam.
- Quem usava localmente o `docker-compose.yml` **legado da raiz** não pode subir o compose novo direto. Ele reaproveita os volumes `loteria_lotofacil_dados` e `loteria_lotofacil_saida` (o prefixo é o nome da pasta do repositório), que o compose antigo criou como root, porque a imagem antiga não tinha `USER`. A imagem nova roda como `appuser` (UID 1000) e não consegue gravar neles (`Permission denied`). Antes de subir, corrija o dono de cada volume, com `docker run --rm -v loteria_lotofacil_dados:/v alpine chown -R 1000:1000 /v` (e o mesmo para `loteria_lotofacil_saida`), ou apague os dois. O volume `loteria_lotofacil_db`, que o compose antigo montava em `/app/src`, deixa de ser usado; se você treinou modelos naquele container, eles estão nele, então copie o que quiser guardar antes de apagá-lo.
- O `.gitignore` da raiz ficou só com o que vale para o repositório inteiro; cada projeto ignora a própria `dados/` e `saida/` no seu `.gitignore` (a lotofacil também `backups/` e `portfolio_*`). Motivos em [docs/decisoes.md](docs/decisoes.md).
- O `ruff.toml` não define mais `exclude` nem `extend-exclude`: os padrões do ruff já cobrem venvs e `dist`, e `build/` fica de fora pelo `.gitignore`.
- Documentos dos projetos reorganizados e com nome só em ASCII: `docs/guias/avaliacao-de-boloes.md`, `lotofacil/docs/pesquisa/`, `lotofacil/docs/estrategias/onze-dezenas.md`, `lotofacil/docs/painel.md`, `lotofacil/docs/clima.md`, `lotofacil/docs/dicionario-dados-ml.md`, `super-sete/docs/pesquisa/` e `dia-de-sorte/docs/pesquisa/`. O `scripts/build_ml_dataset.py` da lotofacil passa a gravar `docs/dicionario-dados-ml.md`.
- `lotofacil/docs/curl.md` foi movido para `docs/api-externa.md`, na raiz: o documento descreve a API externa (loteriascaixa-api) que os cinco projetos usam, e não só a lotofacil. Ganhou título novo e uma nota no topo; o resto do conteúdo é o mesmo.
- `README.md` e `CONTRIBUTING.md` reescritos: início rápido e fluxo de contribuição com o `Makefile`, estrutura do repositório, painéis e deploy.

### Removido

- `Dockerfile`, `docker-compose.yml` e `.dockerignore` legados da raiz. Motivos em [docs/decisoes.md](docs/decisoes.md).
- `lotofacil/docker-compose.yml` e `lotofacil/deploy.sh`. Motivos em [docs/decisoes.md](docs/decisoes.md).
- Arquivos de ferramentas de IA saíram do git e ficam só no disco de quem os gerou (e no histórico): `lotofacil/docs/superpowers/` (27 arquivos), `quina/docs/superpowers/` (6) e `lotofacil/.superpowers/` (6). `**/docs/superpowers/` e `**/.superpowers/` passam a ser ignorados em qualquer nível. Motivos em [docs/decisoes.md](docs/decisoes.md).
- `super-sete/dados/sample/` e `dia-de-sorte/dados/sample/` (115 arquivos): amostras que nada lia. Os testes usam `testes/fixtures/`. Motivos em [docs/decisoes.md](docs/decisoes.md).
- Documentos obsoletos: `lotofacil/PRD.md`, `lotofacil/docs/PRD-dashboard.md`, `lotofacil/docs/architecture.md`, `lotofacil/docs/development.md`, `dia-de-sorte/docs/api-doc.md`, `dia-de-sorte/docs/2026-04-07-analisador-diadesorte.md` e um arquivo vazio em `dia-de-sorte/docs/`. Motivos em [docs/decisoes.md](docs/decisoes.md).

### Corrigido

- Container dos painéis (lotofacil, quina e megasena) ficava *unhealthy* com `DASHBOARD_PASSWORD` definida, porque o `HEALTHCHECK` consultava `/api/status`, que exige login. Agora consulta `/healthz`.
- `README.md` da raiz: a Mega-Sena aparecia como "Planejado", e o texto falava de amostras em `dados/sample/` e de um `Dockerfile` da raiz que não existem mais.
- `lotofacil/README.md`: deixou de citar o `docker-compose.yml` da lotofacil, o `Dockerfile` da raiz e nomes de volume que não existem mais. O bloco com uma cópia do `Dockerfile`, que mostrava `--workers 2` quando o real usa 1 worker e 4 threads, virou um link para o arquivo.

### Segurança

- `.env` e `.env.*` (por exemplo `.env.local` e `.env.production`) são ignorados pelo git na raiz, para que a senha do painel não seja versionada por engano.
- O `docker-compose.yml` publica as portas só em `127.0.0.1`. Para expor os painéis na rede, é preciso remover esse prefixo, de preferência só com `DASHBOARD_PASSWORD` definida.
