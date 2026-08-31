# Política de Segurança

## Como reportar uma vulnerabilidade

Abra um **[security advisory privado](https://github.com/andredfaria/loteria/security/advisories/new)**.
Não abra issue pública para vulnerabilidade — issues são visíveis antes de existir correção.

Se preferir, abra uma issue pública contendo **apenas** "encontrei um problema de
segurança, entre em contato" e nada mais, sem detalhes.

Expectativa de resposta: este é um projeto pessoal mantido no tempo livre, sem
SLA. Faço o possível para responder em uma semana.

## Escopo

O que interessa reportar:

- Acesso não autenticado aos painéis web (`lotofacil`, `quina`).
- Execução remota de comandos, injeção de SQL ou path traversal.
- Negação de serviço via parâmetro de API sem limite.
- Vazamento de segredos, credenciais ou caminhos do servidor em respostas de erro.
- Vulnerabilidade em dependência que seja de fato explorável aqui.

O que **não** é vulnerabilidade neste projeto:

- Os modelos não preverem resultados de loteria. Isso é o comportamento
  esperado e está documentado — sorteios são eventos aleatórios independentes.
- Rodar o painel com `DASHBOARD_PUBLICO=1`. Essa variável existe justamente
  para exigir uma confirmação explícita de que se aceita o painel sem senha.

## Como implantar com segurança

Os painéis **falham fechado**: sem configuração de segurança, o processo não
inicia. Isso é deliberado — a versão anterior liberava tudo quando nenhuma
senha estava definida, então o estado padrão de um deploy era o inseguro.

| Variável | Efeito se ausente |
|---|---|
| `DASHBOARD_PASSWORD` | Sem ela **e** sem `DASHBOARD_PUBLICO=1`, o servidor recusa iniciar. |
| `DASHBOARD_AUTH_SECRET` | A chave de sessão é sorteada a cada início: todo restart desloga todo mundo, e com `--workers > 1` o login falha de forma intermitente. |
| `DASHBOARD_PUBLICO=1` | Confirma explicitamente o painel sem autenticação. Só atrás de rede ou tunnel confiável. |
| `DASHBOARD_MAX_JOBS` | Padrão `2`. Limita treinos/backtests simultâneos; acima disso a API responde `429`. |

`DASHBOARD_SKIP_AUTH_CHECK=1` existe **apenas** para a suíte de testes poder
importar o módulo do servidor. Nenhum `Dockerfile` ou `entrypoint.sh` deste
repositório a define. Não use em produção: ela reabre exatamente o buraco que a
checagem de inicialização fecha.

Os contêineres rodam como usuário não-root (`appuser`, UID/GID 1000).

## Verificação automatizada

Rodam em todo push e PR (`.github/workflows/seguranca.yml`):

- `pip-audit` — vulnerabilidades conhecidas nas dependências, nos cinco projetos.
  Também roda semanalmente, porque CVE aparece sem ninguém tocar no código.
- `gitleaks` — varredura de segredos no histórico completo, não só na árvore atual.
- `bandit` — análise estática, severidade média e alta.

## Dados

O repositório contém apenas amostras de resultados de loteria — informação
pública da Caixa. Não há dados pessoais, credenciais ou datasets privados
versionados. O histórico completo é baixado pela CLI e está no `.gitignore`.
