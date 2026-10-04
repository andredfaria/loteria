# loteria-nucleo

Pacote interno com componentes compartilhados pelos projetos deste monorepo.
O nome da distribuição Python é `loteria-nucleo`; o import é
`loteria_nucleo`. O pacote ainda não é publicado no PyPI.

Instale sempre a cópia deste repositório junto com o projeto que vai usar:

```bash
pip install -e ./nucleo -e "./megasena[dev]"
```

Não instale `loteria-nucleo` do PyPI. Os módulos compartilhados são extraídos
progressivamente nas fases da reorganização do monorepo.
