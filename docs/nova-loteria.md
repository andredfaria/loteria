# Como adicionar uma loteria

1. Crie `<projeto>/` na raiz, com `pyproject.toml`, `README.md`, `src/` e
   `testes/`.
2. Defina as regras próprias em `src/<pacote>/dominio/regras.py`. Quando os
   campos corresponderem ao contrato comum, descreva-os com
   `loteria_nucleo.spec.LoteriaSpec`.
3. Reuse componentes de `loteria_nucleo` quando eles já cobrirem o caso. Não
   force regras posicionais ou campos especiais a caber em uma API inadequada.
4. Adicione o projeto à matriz de testes, ao Dependabot, ao `Makefile` e à
   documentação. Para um painel, inclua seu Dockerfile no workflow de imagens,
   no Compose e na configuração de deploy.
5. Instale com `make instalar P=<projeto>`, rode a suíte do projeto e `make
   lint`. Registre mudanças no `CHANGELOG.md` e decisões estruturais em
   `docs/decisoes.md`.

`loteria-nucleo` é um pacote interno deste monorepo e ainda não está no PyPI.
