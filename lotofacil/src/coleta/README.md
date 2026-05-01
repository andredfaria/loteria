# Data Collection - Coleta de Dados

Módulos para coleta de dados históricos da Lotofácil via API.

## Scripts

| Script | Descrição |
|--------|-----------|
| `busca_sorteios.py` | Coleta principal - baixa todos os concursos da API |
| `atualizar_concursos.py` | Atualização incremental - busca apenas concursos novos |

## Uso

```bash
# Buscar todos os concursos (do 1 até o mais recente)
python src/coleta/busca_sorteios.py

# Buscar até um concurso específico
python src/coleta/busca_sorteios.py --ate 3500

# Atualizar apenas concursos novos
python src/coleta/atualizar_concursos.py
```

## API

API utilizada: `https://loteriascaixa-api.herokuapp.com/api/lotofacil`

## Dados de Saída

Os dados são salvos em `dados/concurso_N.json`:

```json
{
  "concurso": 3500,
  "data": "DD/MM/YYYY",
  "dezenas": ["01", "02", "03", ...],
  "dezenasOrdemSorteio": ["07", "03", ...],
  "trevos": []
}
```

Também é gerado um arquivo consolidado `dados/numeros_sorteados.json` com todos os concursos.
