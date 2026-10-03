# Análise Climática — Lotofácil

Integração de dados meteorológicos da [Open-Meteo API](https://open-meteo.com/) com os resultados dos sorteios da Lotofácil, para investigar possíveis correlações entre condições climáticas e números sorteados.

> **Aviso:** Loteria é jogo de azar. Cada sorteio é um evento aleatório independente. Esta análise é puramente estatística e exploratória — não há evidência científica de que o clima influencie resultados.

---

## Visão Geral

Os sorteios da Lotofácil acontecem em São Paulo, SP. Este módulo coleta dados climáticos históricos para cada dia de sorteio e cruza com as dezenas sorteadas para identificar padrões.

### Métricas coletadas

| Métrica | Descrição |
|---|---|
| `temperature_2m` | Temperatura horária (°C) |
| `precipitation_probability` | Probabilidade de chuva (%) |
| `weathercode` | Código WMO de condição climática |

### Resumo diário calculado

| Campo | Descrição |
|---|---|
| `temp_min` / `temp_max` / `temp_media` | Estatísticas de temperatura no dia |
| `temp_sorteio` | Temperatura no horário do sorteio (~20h) |
| `precipitacao_media` | Média diária de probabilidade de chuva |
| `precipitacao_sorteio` | Probabilidade de chuva no horário do sorteio |
| `condicao_sorteio` | Condição climática no horário do sorteio |
| `condicao_dominante` | Condição climática mais frequente no dia |

---

## Uso

### 1. Buscar dados climáticos

```bash
# Buscar clima dos últimos 50 concursos (padrão)
python src/coleta/busca_clima.py

# Buscar clima dos últimos N concursos
python src/coleta/busca_clima.py --ultimos 20

# Buscar clima de todos os concursos existentes
python src/coleta/busca_clima.py --todos

# Buscar clima de um concurso específico
python src/coleta/busca_clima.py --concurso 3650

# Buscar clima para uma data avulsa (sem vínculo)
python src/coleta/busca_clima.py --data 2026-05-04
```

### 2. Analisar correlações

```bash
# Executar análise com dados disponíveis
python src/analise/analisar_clima.py

# Definir mínimo de concursos para análise
python src/analise/analisar_clima.py --minimo 100
```

---

## Formato dos Dados

Os arquivos de clima são salvos em `dados/clima/` com o padrão:

```
clima_concurso{N}-{YYYY-MM-DD}.json
```

### Exemplo

```
dados/clima/clima_concurso3655-2026-04-07.json
```

### Estrutura do JSON

```json
{
  "concurso": 3655,
  "data": "2026-04-07",
  "latitude": -23.55,
  "longitude": -46.63,
  "timezone": "America/Sao_Paulo",
  "hourly_units": {
    "time": "iso8601",
    "temperature_2m": "°C",
    "precipitation_probability": "%",
    "weathercode": "WMO code"
  },
  "hourly": {
    "time": ["2026-04-07T00:00", "..."],
    "temperature_2m": [17.6, 16.2, "..."],
    "precipitation_probability": [10, 5, "..."],
    "weathercode": [3, 2, "..."]
  },
  "resumo": {
    "temp_min": 14.7,
    "temp_max": 25.6,
    "temp_media": 19.5,
    "precipitacao_media": 20.0,
    "temp_sorteio": 20.6,
    "precipitacao_sorteio": 6,
    "weathercode_sorteio": 2,
    "weathercode_dominante": 3,
    "condicao_sorteio": "Parcialmente nublado",
    "condicao_dominante": "Nublado"
  }
}
```

---

## Código WMO de Condições Climáticas

| Código | Condição |
|---|---|
| 0 | Céu limpo |
| 1 | Principalmente limpo |
| 2 | Parcialmente nublado |
| 3 | Nublado |
| 45 | Neblina |
| 51-57 | Garoa (leve a densa) |
| 61-67 | Chuva (leve a forte) |
| 71-77 | Neve |
| 80-82 | Pancadas de chuva |
| 95-99 | Trovoada |

---

## Análise Realizada

O script `analisar_clima.py` realiza três tipos de análise:

1. **Temperatura vs Dezenas** — Frequência de dezenas por faixa de temperatura (frio, agradável, quente)
2. **Chuva vs Dezenas** — Frequência de dezenas por probabilidade de chuva (sem chuva, baixa, alta)
3. **Pares/Ímpares vs Condição** — Distribuição de pares e ímpares por condição climática

### Exemplo de saída

```
============================================================
Análise Clima vs Números — Lotofácil
Concursos com dados climáticos: 50
============================================================

🌡️ TEMPERATURA vs DEZENAS

  frio (< 18°C) (12 sorteios)
    + frequentes: 10(58.3%), 05(50.0%), 13(50.0%), 23(50.0%), 24(50.0%)
    - frequentes: 01(16.7%), 08(25.0%), 14(25.0%), 21(25.0%), 25(25.0%)

🌧️ CHUVA vs DEZENAS

  sem chuva (0-20%) (30 sorteios)
    + frequentes: 05(53.3%), 10(53.3%), 13(50.0%), 20(50.0%), 24(50.0%)
    - frequentes: 01(20.0%), 07(26.7%), 11(30.0%), 16(30.0%), 22(30.0%)

⚖️ PARES/ÍMPARES vs CONDIÇÃO CLIMÁTICA

  Parcialmente nublado (18 sorteios)
    Pares: 48.9% | Ímpares: 51.1%
```

---

## API Open-Meteo

- **Endpoint:** `https://api.open-meteo.com/v1/forecast`
- **Coordenadas:** São Paulo, SP (`-23.55, -46.63`)
- **Timezone:** `America/Sao_Paulo`
- **Dados:** `temperature_2m`, `precipitation_probability`, `weathercode`
- **Licença:** Gratuita para uso não-comercial, sem autenticação

---

## Limitações

- Dados climáticos são históricos e podem não refletir condições exatas no momento do sorteio
- A Open-Meteo retorna dados de reanálise para datas passadas — são estimativas baseadas em modelos
- Não há relação causal comprovada entre clima e resultados de loteria
- Resultados devem ser interpretados como curiosidade estatística, não como base para apostas
