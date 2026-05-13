# API de Consulta de Resultados - Lotofácil

## Descrição
Endpoint para consultar os resultados de um concurso específico da Lotofácil pela API pública da Loterias Caixa.

## Endpoint

**Base URL:** `https://loteriascaixa-api.herokuapp.com/api/lotofacil`

**Método:** `GET`

**URL Completa:**
```
GET /api/lotofacil/{concurso}
```

**Parâmetros de URL:**
- `{concurso}` (obrigatório): Número do concurso desejado (ex: 3583)

## Headers

```
accept: */*
```

## Exemplo de Chamada

### Formato genérico (com parâmetro):
```bash
curl -X GET "https://loteriascaixa-api.herokuapp.com/api/lotofacil/{concurso}" \
  -H "accept: */*"
```

### Exemplo prático (concurso 3583):
```bash
curl -X GET "https://loteriascaixa-api.herokuapp.com/api/lotofacil/3583" \
  -H "accept: */*"
```

## Estrutura da Resposta

### Resposta de Sucesso (HTTP 200)

```json
{
  "loteria": "lotofacil",
  "concurso": 3583,
  "data": "09/01/2026",
  "local": "ESPAÇO DA SORTE em SÃO PAULO, SP",
  "dezenasOrdemSorteio": [
    "02", "21", "22", "10", "09", "04", "14", "15",
    "06", "24", "25", "12", "13", "23", "03"
  ],
  "dezenas": [
    "02", "03", "04", "06", "09", "10", "12", "13",
    "14", "15", "21", "22", "23", "24", "25"
  ],
  "trevos": [],
  "timeCoracao": null,
  "mesSorte": null,
  "premiacoes": [
    {
      "descricao": "15 acertos",
      "faixa": 1,
      "ganhadores": 0,
      "valorPremio": 0
    },
    {
      "descricao": "14 acertos",
      "faixa": 2,
      "ganhadores": 209,
      "valorPremio": 2297.49
    },
    {
      "descricao": "13 acertos",
      "faixa": 3,
      "ganhadores": 7925,
      "valorPremio": 35
    },
    {
      "descricao": "12 acertos",
      "faixa": 4,
      "ganhadores": 107604,
      "valorPremio": 14
    },
    {
      "descricao": "11 acertos",
      "faixa": 5,
      "ganhadores": 606327,
      "valorPremio": 7
    }
  ],
  "estadosPremiados": [],
  "observacao": "",
  "acumulou": true,
  "proximoConcurso": 3584,
  "dataProximoConcurso": "10/01/2026",
  "localGanhadores": [],
  "valorArrecadado": 25815853,
  "valorAcumuladoConcurso_0_5": 1039352.76,
  "valorAcumuladoConcursoEspecial": 51685523.8,
  "valorAcumuladoProximoConcurso": 2290062.64,
  "valorEstimadoProximoConcurso": 6000000
}
```

## Descrição dos Campos

### Campos Principais
- **loteria**: Nome da loteria (sempre "lotofacil")
- **concurso**: Número do concurso consultado
- **data**: Data do sorteio no formato DD/MM/YYYY
- **local**: Local onde foi realizado o sorteio

### Arrays de Números
- **dezenasOrdemSorteio**: Array com os 15 números sorteados na ordem em que foram sorteados (strings)
- **dezenas**: Array com os 15 números sorteados em ordem crescente (strings)

### Premiações
- **premiacoes**: Array de objetos contendo:
  - `descricao`: Descrição da faixa de premiação (ex: "15 acertos")
  - `faixa`: Número da faixa de premiação (1 = 15 acertos, 2 = 14 acertos, etc.)
  - `ganhadores`: Quantidade de ganhadores na faixa
  - `valorPremio`: Valor do prêmio por ganhador (em reais)

### Informações Adicionais
- **acumulou**: Boolean indicando se o prêmio principal acumulou
- **proximoConcurso**: Número do próximo concurso
- **dataProximoConcurso**: Data do próximo concurso
- **valorArrecadado**: Valor total arrecadado no concurso (em reais)
- **valorAcumuladoProximoConcurso**: Valor acumulado para o próximo concurso (em reais)
- **valorEstimadoProximoConcurso**: Valor estimado do próximo concurso (em reais)

### Campos Opcionais
- **trevos**: Array vazio (campo não utilizado na Lotofácil)
- **timeCoracao**: Valor nulo (campo não utilizado na Lotofácil)
- **mesSorte**: Valor nulo (campo não utilizado na Lotofácil)
- **estadosPremiados**: Array vazio (lista de estados com ganhadores)
- **localGanhadores**: Array vazio (informações sobre localização dos ganhadores)
- **observacao**: String vazia ou com observações adicionais