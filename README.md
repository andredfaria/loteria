# Loteria - Análise Estatística de Loterias Brasileiras

Monorepo com sistemas de análise estatística, geração de jogos e Machine Learning para loterias da Caixa Econômica Federal.

> **Aviso:** Este projeto é para fins de estudo estatístico. Loteria é jogo de azar — cada sorteio é um evento aleatório independente. Nenhum sistema garante ganhos.

---

## Subprojetos

| Projeto | Descrição | Status |
|---------|-----------|--------|
| [lotofacil/](lotofacil/) | Sistema completo: coleta, análise, geração, ML e portfolio | Ativo |
| [super-sete/](super-sete/) | Análise estatística e coleta de dados | Ativo |
| [megasena/](megasena/) | Em desenvolvimento | Planejado |

---

## Lotofácil

O subprojeto mais completo. Inclui:

- **Coleta** — busca sorteios históricos da API da Caixa
- **Análise** — padrões estatísticos (pares/ímpares, moldura, fibonacci, primos)
- **Geração** — combinações filtradas por critérios estatísticos
- **ML Pipeline** — LightGBM/Random Forest para otimizar parâmetros de geração
- **CLI com SQLite** — sistema ensemble (Frequency + ML + LSTM) com banco local
- **Portfolio** — diversificação em 5 estratégias complementares

```bash
cd lotofacil
source venv/bin/activate
pip install -r requirements.txt

# Coletar dados
python src/coleta/busca_sorteios.py

# Gerar jogos (concurso de referência N → gera para N+1)
python src/geracao/gerador_jogos_lotofacil.py -q 10 -c <N>

# CLI com ensemble ML
python src/lotofacil_ml/main.py update --all
python src/lotofacil_ml/main.py train
python src/lotofacil_ml/main.py predict
```

Veja [lotofacil/README.md](lotofacil/README.md) para documentação completa.

---

## Super Sete

Sistema de coleta e análise estatística para a Super Sete (7 colunas, cada uma com um dígito de 0–9).

- **Coleta** — busca sorteios históricos da API da Caixa e salva em `dados/concurso_<N>.json`
- **Análise** — score composto por coluna com base em frequência, atraso, tendência, entropia e diversidade

```bash
cd super-sete
pip install -r requirements.txt

# Coletar dados
python busca_sorteios.py

# Analisar padrões por coluna
python analise_estatistica.py
```

Veja [super-sete/README.md](super-sete/README.md) para documentação completa.

---

## API Caixa

Todos os projetos consomem a mesma API:

```
https://loteriascaixa-api.herokuapp.com/api/<loteria>/<concurso>
```

Onde `<loteria>` é `lotofacil`, `megasena` ou `supersete`.

---

## Dados de Amostra

Cada subprojeto inclui os **100 sorteios mais recentes** em `dados/sample/` para uso imediato sem precisar executar a coleta. Para o dataset completo, use os scripts de coleta.

---

## Licença

MIT — veja [LICENSE](LICENSE).
