# Arquitetura

O repositório reúne cinco aplicações independentes e o pacote interno
`nucleo/`, distribuído localmente como `loteria-nucleo` e importado como
`loteria_nucleo`. O núcleo recebe código que tem o mesmo contrato para mais de
uma loteria; regras e fluxos exclusivos continuam dentro de cada projeto.

## Estrutura

```text
nucleo/src/loteria_nucleo/   componentes compartilhados
megasena/src/megasena/       Mega-Sena
quina/src/quina/             Quina
lotofacil/src/lotofacil/     Lotofácil
dia-de-sorte/src/diadesorte/ Dia de Sorte
super-sete/src/supersete/    Super Sete
```

A migração é progressiva. Nesta etapa, Mega-Sena declara suas regras em
`LoteriaSpec` e usa os cálculos combinatórios e a resolução de caminhos do
núcleo. Os demais projetos passam a instalar o núcleo desde já; suas migrações
de código acontecem nas fases seguintes. Os módulos de ML da Mega-Sena também
permanecem no projeto até a fase 4.

## Instalação local

Cada projeto mantém seu próprio ambiente virtual. Instale o núcleo local
junto com o projeto usando `make instalar P=megasena`.

Não instale `loteria-nucleo` do PyPI: o pacote ainda não é publicado. O comando
do Makefile instala a cópia deste repositório em modo editável.

## Imagens e deploy

Os Dockerfiles continuam em cada pasta, mas usam a raiz como contexto para
copiar `nucleo/`. O conteúdo da aplicação permanece em `/app`; portanto,
volumes e portas não mudam. Consulte [deploy.md](deploy.md) para atualizar os
três apps no EasyPanel.
