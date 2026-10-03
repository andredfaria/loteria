# Documentação

Índice dos documentos do repositório. Os que valem para mais de um projeto ficam nesta pasta; os de cada loteria ficam em `<projeto>/docs/`. O que cada projeto faz e como usá-lo está no `README.md` da pasta dele, a partir do [README da raiz](../README.md).

## Repositório

- [deploy.md](deploy.md): configuração dos painéis no EasyPanel, volumes, variáveis de ambiente e como subi-los localmente com o Docker Compose.
- [decisoes.md](decisoes.md): registro do que saiu ou mudou na reorganização do monorepo, com data, motivo e evidência.
- [api-externa.md](api-externa.md): estrutura da resposta da API externa de resultados (loteriascaixa-api), que os cinco projetos usam.
- [guias/avaliacao-de-boloes.md](guias/avaliacao-de-boloes.md): metodologia para avaliar o preço e a chance de um bolão da Mega-Sena ou da Lotofácil.

## Lotofácil

- [painel.md](../lotofacil/docs/painel.md): visão geral do painel web (versão de 2026-05-29).
- [clima.md](../lotofacil/docs/clima.md): análise climática, com dados da Open-Meteo, dos sorteios da Lotofácil.
- [dicionario-dados-ml.md](../lotofacil/docs/dicionario-dados-ml.md): dicionário das colunas do dataset de ML.
- [estrategias/onze-dezenas.md](../lotofacil/docs/estrategias/onze-dezenas.md): estratégia de 11 dezenas.
- [pesquisa/](../lotofacil/docs/pesquisa/): relatórios de pesquisa (`estrategias-racionais.md`, `hierarquia-de-estrategias.md` e `validacao-ml-3500-3580.md`).

## Dia de Sorte

- [pesquisa/](../dia-de-sorte/docs/pesquisa/): nove documentos, um por estratégia de jogo (`01-equilibrio-par-impar.md` a `09-mes-da-sorte.md`).

## Super Sete

- [pesquisa/](../super-sete/docs/pesquisa/): relatório de análise do jogo (`relatorio-de-analise.md`).
