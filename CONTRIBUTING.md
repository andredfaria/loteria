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

Cada projeto é autônomo, com seu próprio venv:

```bash
cd <projeto> && python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
pytest
```

Os painéis falham fechado. Para rodar a suíte, o `conftest.py` já define
`DASHBOARD_SKIP_AUTH_CHECK=1`; para rodar o servidor de verdade, defina
`DASHBOARD_PASSWORD`. Ver [SECURITY.md](SECURITY.md).

## Antes de abrir o PR

```bash
ruff check .     # gate da CI
pytest           # no projeto que você tocou
```

O ruleset do `ruff.toml` é estreito de propósito: pega bug, não estilo. Para
ampliá-lo, escolha **uma** regra, rode `ruff check --select <REGRA> --fix`,
revise o diff e abra um PR só disso — assim o diff continua legível.

## Mudou feature de modelo?

Alterar a semântica de uma feature invalida os modelos treinados: os `.joblib`
continuam carregando e passam a receber colunas com outro significado,
produzindo lixo em silêncio. Diga no PR o que precisa ser retreinado.

## Segurança

Vulnerabilidade não vai em issue pública — veja [SECURITY.md](SECURITY.md).
