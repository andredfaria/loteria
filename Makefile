# Atalhos do monorepo. Cada projeto tem o próprio venv em <projeto>/venv.
# Comece por: make ajuda

PROJETOS := lotofacil quina megasena dia-de-sorte super-sete
PAINEIS  := lotofacil quina megasena
PYTHON   ?= python3
P        ?=

.PHONY: ajuda instalar testar lint docker checar-projeto

ajuda:
	@echo "make instalar P=<projeto>   cria <projeto>/venv e instala nucleo/ + projeto[dev]"
	@echo "make testar [P=<projeto>]   roda o pytest de um projeto, ou de todos se P for omitido"
	@echo "make lint                   mesmo \`ruff check .\` da CI"
	@echo "make docker P=<painel>      builda a imagem do painel ($(PAINEIS))"
	@echo ""
	@echo "Projetos: $(PROJETOS)"

checar-projeto:
	@test -n "$(P)" || { echo "Informe o projeto: P=<projeto>. Opções: $(PROJETOS)" >&2; exit 2; }
	@printf '%s\n' $(PROJETOS) | grep -qxF -- "$(P)" || { echo "Projeto desconhecido: '$(P)'. Opções: $(PROJETOS)" >&2; exit 2; }

instalar: checar-projeto
	test -x $(P)/venv/bin/python || $(PYTHON) -m venv $(P)/venv
	$(P)/venv/bin/pip install -e ./nucleo -e "./$(P)[dev]"

testar:
ifeq ($(strip $(P)),)
	@falhou=""; for p in $(PROJETOS); do \
	  echo "== $$p"; \
	  if [ ! -x $$p/venv/bin/python ]; then echo "   sem venv: rode 'make instalar P=$$p'"; falhou="$$falhou $$p"; continue; fi; \
	  (cd $$p && DASHBOARD_SKIP_AUTH_CHECK=1 venv/bin/python -m pytest -q) || falhou="$$falhou $$p"; \
	done; \
	if [ -n "$$falhou" ]; then echo "Falharam:$$falhou"; exit 1; fi
else
	@$(MAKE) --no-print-directory checar-projeto P="$(P)"
	@test -x $(P)/venv/bin/python || { echo "Sem venv em $(P)/venv: rode 'make instalar P=$(P)'" >&2; exit 2; }
	cd $(P) && DASHBOARD_SKIP_AUTH_CHECK=1 venv/bin/python -m pytest -q
endif

lint:
	@command -v ruff >/dev/null 2>&1 || { echo "ruff não encontrado. Instale com: pip install ruff (ou: uvx ruff check .)" >&2; exit 2; }
	ruff check .

docker: checar-projeto
	@printf '%s\n' $(PAINEIS) | grep -qxF -- "$(P)" || { echo "'$(P)' não tem painel nem Dockerfile. Painéis: $(PAINEIS)" >&2; exit 2; }
	docker build -t loteria-$(P):local $(P)
