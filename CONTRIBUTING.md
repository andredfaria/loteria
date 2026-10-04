# Contribuindo

Obrigado pelo interesse. Este é um projeto de **estudo estatístico** de
loterias brasileiras. Antes de qualquer coisa, o princípio que orienta todas as
decisões aqui:

> Loterias são eventos aleatórios independentes. Nenhum sistema prevê
> resultados. O objetivo do projeto é analisar dados históricos com honestidade
> — inclusive quando a resposta honesta é "não há sinal".

## O que isso significa na prática

Contribuições que **afirmam** poder preditivo sem evidência serão recusadas.
Contribuições que **medem** e reportam a ausência de poder preditivo são
exatamente o que o projeto quer.

Três regras que valem mais que qualquer padrão de código:

1. **Nunca chame score de probabilidade.** Os modelos produzem um score de
   ordenação em `[0, 1]`, normalizado min-max — o topo recebe `1.0` por
   construção. A probabilidade real de uma dezena sair é
   `NUMEROS_POR_SORTEIO / TOTAL_NUMEROS` e não muda. Toda tela que mostra um
   score mostra essa probabilidade ao lado.

2. **Docstring que afirma uma propriedade precisa medi-la.** Se você escreve
   "sob independência o valor esperado é 1,0", rode um experimento com sorteios
   sintéticos uniformes e cite o número medido. Uma nota honesta que erra o
   número é pior que nenhuma nota.

3. **Feature nova precisa de teste de propriedade**, não só de caminho feliz.
   Coluna constante e coluna duplicada já passaram despercebidas aqui — veja
   `testes/unidade/test_atributos_propriedades.py`.

## Ambiente

Cada projeto é autônomo, com o próprio venv em `<projeto>/venv`. Na raiz do
repositório:

```bash
make instalar P=<projeto>   # cria <projeto>/venv, se faltar, e instala o projeto com [dev]
make testar P=<projeto>     # roda o pytest do projeto (sem P, roda os cinco)
make lint                   # o mesmo `ruff check .` da CI
```

Os projetos são `lotofacil`, `quina`, `megasena`, `dia-de-sorte` e
`super-sete`. `make ajuda` lista todos os alvos. O `make lint` precisa do `ruff`
instalado (`pip install ruff`). Sem `make` (no Windows, por exemplo), leia o
[`Makefile`](Makefile): cada alvo é um comando curto de venv, pip, pytest, ruff
ou docker.

Os painéis falham fechado. Para rodar a suíte, o `make testar` e os
`conftest.py` já definem `DASHBOARD_SKIP_AUTH_CHECK=1`; para rodar o servidor de
verdade, defina `DASHBOARD_PASSWORD`. Ver [SECURITY.md](SECURITY.md).

## Organização

- Cada loteria é uma pasta na raiz, com o código em `src/<pacote>/` e os testes
  em `testes/`.
- Documentos de pesquisa ficam em `<projeto>/docs/pesquisa/`. Documento novo
  ganha uma linha em [docs/README.md](docs/README.md).
- Nomes de arquivo em ASCII e, nos documentos, em kebab-case
  (`avaliacao-de-boloes.md`). A CI recusa acento, espaço e `:` no nome de
  qualquer arquivo versionado.
- Links relativos entre documentos são verificados pela CI: um `.md` que aponta
  para um arquivo que não existe falha o PR. Para conferir antes, rode
  `python3 .github/scripts/verificar_links.py`.

## Antes de abrir o PR

```bash
make lint                  # o mesmo `ruff check .` da CI
make testar P=<projeto>    # no projeto que você tocou
```

Além do `ruff check .`, a CI roda `python3 .github/scripts/verificar_links.py` e
a checagem de nomes de arquivo portáveis (veja "Organização", acima); o
`make lint` não faz essas duas.

O PR já abre com um [template](.github/pull_request_template.md) que repete
essa lista e pergunta pelo retreino de modelos e pelo uso de score no lugar de
probabilidade. Registre a mudança no [CHANGELOG.md](CHANGELOG.md), na seção
"Não publicado".

O ruleset do `ruff.toml` é estreito de propósito: pega bug, não estilo. Para
ampliá-lo, escolha **uma** regra, rode `ruff check --select <REGRA> --fix`,
revise o diff e abra um PR só disso — assim o diff continua legível.

## Mudou feature de modelo?

Alterar a semântica de uma feature invalida os modelos treinados: os `.joblib`
continuam carregando e passam a receber colunas com outro significado,
produzindo lixo em silêncio. Diga no PR o que precisa ser retreinado.

## Conduta

Participar do projeto é aceitar o [Código de Conduta](CODE_OF_CONDUCT.md).

## Segurança

Vulnerabilidade não vai em issue pública — veja [SECURITY.md](SECURITY.md).
