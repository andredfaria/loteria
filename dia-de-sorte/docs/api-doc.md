# 🎰 Loterias Caixa API

API gratuita para consulta de resultados das loterias da Caixa Econômica Federal.

Base URL:

```
https://loteriascaixa-api.herokuapp.com/api
```

---

## 📌 Visão Geral

Essa API fornece dados atualizados de diversas loterias brasileiras em formato JSON, permitindo integração simples com sistemas, dashboards e automações.

Loterias disponíveis:

* Mega-Sena
* Lotofácil
* Quina
* Lotomania
* Timemania
* Dupla Sena
* Dia de Sorte
* Super Sete
* +Milionária
* Federal

---

## 🚀 Endpoints

### 🔹 Listar todas as loterias disponíveis

```http
GET /api
```

#### Exemplo:

```bash
curl https://loteriascaixa-api.herokuapp.com/api
```

#### Resposta:

```json
[
  "megasena",
  "lotofacil",
  "quina",
  "lotomania",
  "diadesorte",
  "duplasena",
  "federal",
  "maismilionaria",
  "supersete",
  "timemania"
]
```

---

### 🔹 Buscar último resultado de uma loteria

```http
GET /api/{loteria}/latest
```

#### Parâmetros:

| Nome    | Tipo   | Obrigatório | Descrição       |
| ------- | ------ | ----------- | --------------- |
| loteria | string | ✅           | Nome da loteria |

#### Exemplo:

```bash
curl https://loteriascaixa-api.herokuapp.com/api/megasena/latest
```

#### Resposta:

```json
{
  "loteria": "megasena",
  "concurso": 2654,
  "data": "2024-07-15",
  "dezenas": ["15","23","35","42","47","58"]
}
```

---

### 🔹 Buscar resultado por número do concurso

```http
GET /api/{loteria}/{concurso}
```

#### Parâmetros:

| Nome     | Tipo   | Obrigatório | Descrição          |
| -------- | ------ | ----------- | ------------------ |
| loteria  | string | ✅           | Nome da loteria    |
| concurso | number | ✅           | Número do concurso |

#### Exemplo:

```bash
curl https://loteriascaixa-api.herokuapp.com/api/megasena/2654
```

---

### 🔹 Buscar múltiplos concursos

```http
GET /api/{loteria}?concurso=ultimos
GET /api/{loteria}?concurso=ultimos{N}
```

#### Exemplos:

```bash
# Últimos concursos
curl https://loteriascaixa-api.herokuapp.com/api/megasena?concurso=ultimos

# Últimos 10 concursos
curl https://loteriascaixa-api.herokuapp.com/api/megasena?concurso=ultimos10
```

---

## 📊 Estrutura da Resposta

Exemplo genérico:

```json
{
  "loteria": "string",
  "concurso": number,
  "data": "YYYY-MM-DD",
  "dezenas": ["string"],
  "premiacoes": [
    {
      "descricao": "string",
      "ganhadores": number,
      "valor": number
    }
  ]
}
```

---

## ⚠️ Observações

* API é **gratuita e sem autenticação**
* Pode sofrer instabilidade (Heroku free / custo de hospedagem) ([GitHub][1])
* Ideal usar cache/local storage para evitar muitas requisições
* Não há garantia oficial da Caixa (dados são agregados)

---

## ❌ Códigos de Erro

| Código | Descrição                          |
| ------ | ---------------------------------- |
| 404    | Loteria ou concurso não encontrado |
| 500    | Erro interno da API                |

---

## 💡 Boas Práticas

* Cachear resultados localmente
* Evitar chamadas em loop
* Validar nome da loteria antes de chamar
* Criar fallback (API pode cair)

---

## 🧪 Exemplo em JavaScript

```javascript
async function getMegaSena() {
  const res = await fetch("https://loteriascaixa-api.herokuapp.com/api/megasena/latest");
  const data = await res.json();
  console.log(data);
}

getMegaSena();
```

---

## 📦 Possíveis Casos de Uso

* Dashboards de loteria
* Bots de Telegram/WhatsApp
* Apps mobile
* Análise estatística de jogos
* Geração de apostas inteligentes

---