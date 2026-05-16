# Loteria — Análise Estatística de Loterias Brasileiras

Monorepo com sistemas de análise estatística, geração de jogos e Machine Learning para loterias da Caixa Econômica Federal.

> **Aviso:** Este projeto é para fins de estudo estatístico. Loteria é jogo de azar — cada sorteio é um evento aleatório independente. Nenhum sistema garante ganhos.

---

## Subprojetos

| Projeto | Descrição | Status |
|---------|-----------|--------|
| [lotofacil/](lotofacil/) | Sistema completo: coleta, análise, ML, dashboard web | Ativo |
| [super-sete/](super-sete/) | Coleta e análise estatística por coluna | Ativo |
| [megasena/](megasena/) | Em desenvolvimento | Planejado |

Cada subprojeto é autônomo com seu próprio `requirements.txt` / `pyproject.toml` e ambiente virtual.

---

## Lotofácil

O subprojeto mais completo. Pipeline de ponta a ponta: coleta de dados → análise estatística → geração de jogos → ML → predição → dashboard web.

Funcionalidades principais:

- **Coleta** — busca sorteios históricos da API da Caixa, dados climáticos (Open-Meteo) e fase lunar
- **Análise** — padrões estatísticos: pares/ímpares, moldura, fibonacci, primos, co-ocorrência
- **Geração** — combinações filtradas por critérios históricos
- **ML Pipeline** — LightGBM / Random Forest / LSTM clássico (ensemble)
- **Pipeline Neural Lab** — LSTM + Attention + Focal Loss com variáveis exógenas (clima, lua)
- **Portfolio** — diversificação em 5 estratégias complementares
- **Dashboard Web** — interface para treino, predição e monitoramento (Flask + Gunicorn, porta 5000)

```bash
cd lotofacil
source venv/bin/activate
pip install -e .

lotofacil dados atualizar       # sincroniza sorteios da API
lotofacil modelo treinar        # treina ensemble clássico
lotofacil prever                # gera predição para o próximo concurso
```

Veja [lotofacil/README.md](lotofacil/README.md) para documentação completa do sistema, CLI e dashboard.

---

## Super Sete

Coleta e análise estatística para a Super Sete (7 colunas × dígito 0–9).

- **Coleta** — salva sorteios históricos em `dados_supersete/concurso_<N>.json`
- **Análise** — score composto por coluna: frequência, atraso, tendência, entropia, diversidade

```bash
cd super-sete
pip install -r requirements.txt
python busca_sorteios.py       # coleta dados
python analise_estatistica.py  # análise por coluna
```

---

## API Caixa

Todos os projetos consomem:

```
https://loteriascaixa-api.herokuapp.com/api/<loteria>/<concurso>
```

`<loteria>`: `lotofacil`, `megasena`, `supersete`

---

## Dados de Amostra

Cada subprojeto inclui os **100 sorteios mais recentes** em `dados/sample/` (ou equivalente) para uso imediato sem coletar o dataset completo.

---

## Deploy (EasyPanel)

O sistema Lotofácil inclui um **Dockerfile dedicado** em `lotofacil/Dockerfile`. O arquivo `Dockerfile` na raiz deste repositório é uma versão legada e **não deve ser usada** para deploy em produção — ela exclui o TensorFlow e usa o servidor de desenvolvimento do Flask.

Ao configurar o serviço no EasyPanel, defina:

| Campo | Valor correto |
|-------|---------------|
| **Build Context** | `lotofacil` |
| **Dockerfile Path** | `lotofacil/Dockerfile` |
| **Port** | `5000` |

> Se o EasyPanel estiver apontando para o `Dockerfile` da raiz, o TensorFlow não será instalado e o servidor Flask dev será usado em vez do Gunicorn.

---

## Licença

MIT — veja [LICENSE](LICENSE).
