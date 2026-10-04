# Relatório de Análise do Super Sete da Loteria Federal

## 1. Introdução

Este relatório apresenta uma análise abrangente do jogo **Super Sete** da Loteria Federal do Brasil, operado pela Caixa Econômica Federal. A análise combina uma abordagem descritiva dos dados históricos com uma auditoria estatística rigorosa baseada em princípios de matemática combinatória, estatística inferencial e teoria da informação.

O estudo foi realizado com base em dados históricos de **798 concursos** realizados até 14 de janeiro de 2026, com o objetivo de:

- Identificar padrões e tendências nos resultados históricos
- Fornecer estatísticas descritivas sobre frequências de números por coluna
- Realizar testes estatísticos formais para verificar aleatoriedade
- Avaliar criticamente estratégias comuns de apostas
- Oferecer informações técnicas e práticas para apostadores

## 2. Metodologia

### 2.1. Coleta de Dados

Os dados foram coletados do site Rede Loteria [1], que disponibiliza o histórico completo dos resultados do Super Sete. O processamento foi realizado através de scripts em Python que:

- Extraíram e organizaram os resultados de todos os concursos
- Calcularam frequências de cada número (0-9) por coluna
- Computaram estatísticas descritivas (média, mediana, desvio padrão)
- Analisaram distribuições de números pares e ímpares
- Calcularam somas dos números sorteados por concurso

### 2.2. Metodologia Estatística

Para a auditoria estatística, foram aplicados os seguintes métodos:

- **Cálculo Combinatório:** Determinação das probabilidades exatas para cada faixa de premiação
- **Teste de Uniformidade (Qui-Quadrado):** Avaliação da hipótese nula ($H_0$) de que cada dígito (0-9) possui probabilidade idêntica de sorteio ($p=0.1$)
- **Entropia de Shannon:** Medição da incerteza e imprevisibilidade dos resultados por coluna
- **Análise de Correlação de Spearman:** Verificação de dependências estatísticas entre as colunas
- **Análise de Atrasos e Frequências:** Estudo da dispersão temporal e repetições consecutivas

### 2.3. Visualização

Foram gerados gráficos para visualização das principais estatísticas, incluindo mapas de calor de frequências e gráficos de distribuição.

## 3. Fundamentos Teóricos: Probabilidades do Super Sete

O Super Sete é um sistema de **7 colunas independentes**, cada uma com **10 dígitos possíveis** (0 a 9). O espaço amostral total é de $10^7 = 10.000.000$ de combinações possíveis.

### 3.1. Probabilidades de Acerto

| Acertos | Probabilidade Teórica | Chance (1 em...) |
| :--- | :--- | :--- |
| **7 Colunas** | $0,0000001$ | $10.000.000$ |
| **6 Colunas** | $0,0000063$ | $158.730$ |
| **5 Colunas** | $0,0001701$ | $5.878$ |
| **4 Colunas** | $0,0025515$ | $392$ |
| **3 Colunas** | $0,0229635$ | $43,5$ |

### 3.2. Características do Sistema

- Cada coluna é **independente** das demais
- Cada dígito tem probabilidade teórica de **10%** em cada sorteio
- O sistema não possui "memória" - cada sorteio é independente dos anteriores
- A probabilidade de qualquer combinação específica é sempre a mesma

## 4. Análise Descritiva dos Dados Históricos

### 4.1. Frequência de Números por Coluna

O mapa de calor abaixo ilustra a frequência de cada número (0 a 9) em cada uma das sete colunas do Super Sete. Números com cores mais escuras indicam maior frequência de sorteio.

![Frequência de Números por Coluna](https://private-us-east-1.manuscdn.com/sessionFile/4hVsxtndTzKg7F3HYdmTos/sandbox/lFEnEjRmnQqaMZqkHSoAp4-images_1768448537737_na1fn_L2hvbWUvdWJ1bnR1L2ZyZXF1ZW5jaWFfaGVhdG1hcA.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvNGhWc3h0bmRUektnN0YzSFlkbVRvcy9zYW5kYm94L2xGRW5FalJtblFxYU1acWtIU29BcDQtaW1hZ2VzXzE3Njg0NDg1Mzc3MzdfbmExZm5fTDJodmJXVXZkV0oxYm5SMUwyWnlaWEYxWlc1amFXRmZhR1ZoZEcxaGNBLnBuZyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc5ODc2MTYwMH19fV19&Key-Pair-Id=K2HSFNDJXOU9YS&Signature=Nv2FNZToZeZeAE8biy4qEy4BtlTDGyo9zIvSFNgyPI8aKLr2esVJZQNIhgzpYHarhM2V8~-ePIWt-6Gju437BeE89qUfFumCxxni3OZLDRlkBOzHEzCgQMLV43FtJSN0~zVATKvRelcGeQI~MY41bctYDsq34lJtU~g-Pa~sqH5AU85FvHbW5YW-hyFXaZNuUgcPDW9AqF9HM93RpEHw3yy-z~~pWaTODu7tulCdW0dkLHf2pqVg2Slpn-jtjpnU7TJLzkun5h3yBl6T04dtARit6653kiImxtK57LjX9QAz10Ay-YFthvfPdPPeOY3NyVKBrmXoIuaDh0gcyOPCAQ__)

### 4.2. Frequência Geral dos Números

Este gráfico mostra a frequência total de cada número (0 a 9) considerando todas as sete colunas em conjunto.

![Frequência Geral dos Números](https://private-us-east-1.manuscdn.com/sessionFile/4hVsxtndTzKg7F3HYdmTos/sandbox/lFEnEjRmnQqaMZqkHSoAp4-images_1768448537738_na1fn_L2hvbWUvdWJ1bnR1L2ZyZXF1ZW5jaWFfZ2VyYWw.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvNGhWc3h0bmRUektnN0YzSFlkbVRvcy9zYW5kYm94L2xGRW5FalJtblFxYU1acWtIU29BcDQtaW1hZ2VzXzE3Njg0NDg1Mzc3MzhfbmExZm5fTDJodmJXVXZkV0oxYm5SMUwyWnlaWEYxWlc1amFXRmZaMlZ5WVd3LnBuZyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc5ODc2MTYwMH19fV19&Key-Pair-Id=K2HSFNDJXOU9YS&Signature=ZPuyIK~KDcvthKT7DrEs6kZdyCP0EMHSXHVk4agkm8bS5BiyqrbdEA1veiE-cA243N7AH3Ao6NgRN~5Jz6vNIJbCf~pX3hQ-iw0aGlQ1KxCCAWD9UqQb4hr-xG8WnjarWRDcym9y~upzYxkF-4sUMFHJyQV9qh3ciNfadkZabzXxfHEIVJWXLUnaGekrVJ1lY8RkuMOq6NIWIuSNKSKYfS4Qw7m5czHmmP-cq-wBjDtr0xhOoTgmBpVJnB1VV~Rb1mJlJ3IOXtPpInJYjuIu-aaDgJeOTXcjqVKe04tYAEXiJBRuLgGNMfIVQGN3V--lqKEMsHuvsCivs7~vm~A71g__)

### 4.3. Números Mais e Menos Sorteados por Coluna

Com base na análise de frequência dos 798 concursos, identificamos os números que mais e menos saíram em cada coluna:

| Coluna | Mais Sorteados (Número - Frequência) | Menos Sorteados (Número - Frequência) |
|---|---|---|
| 1 | 0 (94), 3 (87), 5 (85) | 9 (76), 2 (72), 8 (72) |
| 2 | 5 (87), 7 (86), 6 (82) | 4 (78), 8 (76), 0 (71) |
| 3 | 5 (93), 1 (85), 4 (84) | 0 (76), 9 (73), 6 (72) |
| 4 | 6 (92), 9 (92), 7 (87) | 4 (74), 3 (69), 8 (66) |
| 5 | 3 (94), 5 (86), 6 (85) | 9 (78), 2 (73), 1 (54) |
| 6 | 0 (91), 7 (91), 4 (88) | 1 (71), 2 (68), 5 (62) |
| 7 | 3 (89), 9 (87), 6 (81) | 7 (77), 4 (74), 8 (74) |

> **Nota:** As diferenças observadas são variações estatísticas esperadas em um sistema aleatório. A análise formal (Seção 5) confirma que essas diferenças não são estatisticamente significativas.

### 4.4. Distribuição de Pares e Ímpares

A análise da distribuição de números pares e ímpares nos sorteios revela que o padrão mais comum é a combinação de 3 números pares e 4 ímpares, ou vice-versa. O gráfico abaixo exibe a quantidade de concursos para cada combinação (ex: 3P-4I significa 3 números pares e 4 números ímpares).

![Distribuição de Pares e Ímpares](https://private-us-east-1.manuscdn.com/sessionFile/4hVsxtndTzKg7F3HYdmTos/sandbox/lFEnEjRmnQqaMZqkHSoAp4-images_1768448537739_na1fn_L2hvbWUvdWJ1bnR1L2Rpc3RyaWJ1aWNhb19wYXJfaW1wYXI.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvNGhWc3h0bmRUektnN0YzSFlkbVRvcy9zYW5kYm94L2xGRW5FalJtblFxYU1acWtIU29BcDQtaW1hZ2VzXzE3Njg0NDg1Mzc3MzlfbmExZm5fTDJodmJXVXZkV0oxYm5SMUwyUnBjM1J5YVdKMWFXTmhiMTl3WVhKZmFXMXdZWEkucG5nIiwiQ29uZGl0aW9uIjp7IkRhdGVMZXNzVGhhbiI6eyJBV1M6RXBvY2hUaW1lIjoxNzk4NzYxNjAwfX19XX0_&Key-Pair-Id=K2HSFNDJXOU9YS&Signature=DedH6Yn-lK74GoqkXle74GfdtLhZ-es-zKy0T-aQqoaqjZnn6TMgshtlnEOaVbZRmx4CWepywu-qGuoqokKUBWKHKCwL0dZwwWvwo6BjX9thpTWqPahdB1LBBUu418qq2762WrgIEHVIhXXgFUt6HL018IAjENn9ErA8x-AUhUBNFr9bGOyaaoGBE-1zPr4vZ-oFi2tkKEYNTUIq49rRJcxlfZTaVRV3HoGrN0d~AWqb5sBUcjmuGhFJSZ9PDSlRPpmBg6b34NT-j13pIh94TD6JjDegwN6nHcPd0unp4nrOHe~qrtiRW6FCnN3rIBrUSebJNXXMy9wTfsgzq4xjbg__)

### 4.5. Estatísticas da Soma dos Números

A soma dos sete números sorteados em cada concurso apresenta as seguintes estatísticas:

*   **Média:** 31.71
*   **Mínimo:** 11
*   **Máximo:** 56
*   **Mediana:** 31.0

> **Nota:** A média teórica esperada para a soma de 7 dígitos aleatórios (0-9) é 31.5, o que está muito próximo do valor observado (31.71), confirmando a aleatoriedade do sistema.

### 4.6. Comportamento de Repetições e Atrasos

*   **Repetições Consecutivas:** Em 47,5% dos concursos, nenhum número se repetiu na mesma coluna em relação ao sorteio anterior. A probabilidade de 4 ou mais repetições simultâneas é inferior a 0,9%, o que está alinhado com a expectativa teórica.
*   **Intervalos Médios (Atrasos):** O intervalo médio observado para qualquer dígito é de aproximadamente 10 concursos, com desvios padrão normais para sistemas estocásticos. Picos de atraso (ex: dígito 7 na coluna 1 com 84 concursos de atraso) são eventos raros, mas previstos em distribuições de cauda longa.

## 5. Auditoria Estatística: Testes de Aleatoriedade

Esta seção apresenta os resultados dos testes estatísticos formais aplicados para verificar se o comportamento observado dos dados históricos é consistente com um modelo teórico de aleatoriedade perfeita.

### 5.1. Testes de Uniformidade (Qui-Quadrado)

O teste de Qui-Quadrado foi aplicado a cada coluna para verificar se a distribuição observada se desvia significativamente da distribuição uniforme esperada (onde cada dígito deveria aparecer com frequência igual).

| Coluna | Estatística $\chi^2$ | P-Value | Status ($ \alpha = 0.05 $) |
| :--- | :--- | :--- | :--- |
| 1 | 5,66 | 0,773 | **Consistente com Aleatoriedade** |
| 2 | 2,40 | 0,983 | **Consistente com Aleatoriedade** |
| 3 | 4,51 | 0,875 | **Consistente com Aleatoriedade** |
| 4 | 8,92 | 0,445 | **Consistente com Aleatoriedade** |
| 5 | 12,73 | 0,175 | **Consistente com Aleatoriedade** |
| 6 | 12,43 | 0,190 | **Consistente com Aleatoriedade** |
| 7 | 2,78 | 0,972 | **Consistente com Aleatoriedade** |

> **Interpretação:** Todos os *p-values* são superiores a 0,05, o que significa que **não há evidências estatísticas** para rejeitar a hipótese de que o sorteio é puramente aleatório e uniforme em todas as colunas. As diferenças observadas nas frequências são flutuações estatísticas normais.

### 5.2. Entropia Informacional

A entropia de Shannon mede a "desordem" ou imprevisibilidade de um sistema. A entropia máxima teórica para uma coluna de 10 dígitos é $\log_2(10) \approx 3,322$ bits.

As entropias calculadas para as colunas variaram entre **3,309** e **3,319**. Esta proximidade extrema com o valor máximo confirma que a imprevisibilidade dos resultados é quase perfeita, dificultando qualquer tentativa de previsão determinística.

### 5.3. Correlação entre Colunas

A análise de correlação de Spearman entre as colunas resultou em valores próximos de zero (variando entre -0,06 e +0,06). Isso confirma a **independência estatística** das colunas: o resultado de uma coluna não exerce influência sobre as demais, conforme esperado teoricamente.

## 6. Avaliação Crítica de Estratégias de Apostas

Esta seção avalia criticamente estratégias comuns de apostas à luz dos resultados estatísticos obtidos.

### 6.1. Limitações Fundamentais

**Importante:** Nenhuma estratégia baseada em dados históricos altera a probabilidade fundamental de acerto. O valor esperado ($EV$) de qualquer aposta simples permanece constante e negativo devido à margem da casa. Estratégias servem apenas para organizar a variância e o risco do apostador, não para aumentar as chances matemáticas de vitória.

### 6.2. Análise de Estratégias Comuns

#### Frequência Histórica (Números "Quentes")

**Premissa:** Utilizar números que apareceram com maior frequência no passado.

**Avaliação Estatística:** Baseia-se na falácia de que o passado influencia o futuro em eventos independentes. Estatisticamente, um número que saiu muito tem **exatamente a mesma chance** de sair novamente que um número que não sai há tempos. Os testes de uniformidade confirmam que as diferenças de frequência observadas são flutuações aleatórias, não padrões preditivos.

#### Atraso Estatístico (Números "Frios")

**Premissa:** Apostar em números que não aparecem há muito tempo, pois "estão devendo".

**Avaliação Estatística:** Conhecida como a *Falácia do Apostador*. O sistema não possui "memória"; a probabilidade de um dígito sair é sempre **10%** em cada sorteio, independentemente de quanto tempo ele esteja sem aparecer. Picos de atraso são eventos raros, mas previstos em distribuições estocásticas.

#### Escolha Balanceada (Pares/Ímpares)

**Premissa:** Equilibrar a quantidade de números pares e ímpares, pois a maioria dos resultados apresenta equilíbrio.

**Avaliação Estatística:** Embora a maioria dos resultados apresente um equilíbrio (3P-4I ou 4P-3I), isso ocorre porque **existem mais combinações equilibradas no espaço amostral**, não porque o sistema "prefira" o equilíbrio. É uma consequência matemática, não um padrão preditivo.

### 6.3. Estratégias Práticas (Gestão de Risco)

Embora não alterem probabilidades, algumas abordagens podem ser úteis para gestão de risco e organização das apostas:

1. **Bolões:** Participar de bolões aumenta a quantidade de apostas e, consequentemente, as chances de ganhar, diluindo o custo entre os participantes [4]. Esta é uma estratégia de **diversificação de risco**, não de aumento de probabilidade.

2. **Fechamentos:** Utilizar fechamentos é uma estratégia que garante premiações menores (terno, quadra, etc.) caso um determinado conjunto de números seja sorteado [5]. É uma forma de **reduzir a variância** dos resultados, não de aumentar a probabilidade de acerto principal.

3. **Apostas Combinadas:** Marcar mais de um número por coluna aumenta o valor da aposta, mas também eleva significativamente as chances de acerto, pois gera mais combinações de jogos [6]. Esta é uma estratégia de **aumento de cobertura**, com custo proporcional.

4. **Evitar Sequências Óbvias:** Evite apostar em sequências muito óbvias (ex: 1-2-3-4-5-6-7) ou padrões visuais no volante. Embora não haja desvantagem matemática, em caso de acerto, a divisão do prêmio pode ser maior devido ao grande número de apostadores com essas escolhas.

## 7. Conclusões

### 7.1. Principais Achados

1. **Aleatoriedade Robusta:** O sistema Super Sete demonstra alta conformidade com os modelos de aleatoriedade uniforme e independência de variáveis. Todos os testes estatísticos formais confirmam que o sistema se comporta como esperado teoricamente.

2. **Inexistência de Vieses:** Não foram detectados desvios sistemáticos ou padrões não-aleatórios mensuráveis nos 798 concursos analisados. As diferenças observadas nas frequências são flutuações estatísticas normais.

3. **Independência das Colunas:** A análise de correlação confirma que as colunas são estatisticamente independentes, conforme o modelo teórico.

4. **Imprevisibilidade:** A entropia informacional próxima do máximo teórico confirma que o sistema é altamente imprevisível, dificultando qualquer tentativa de previsão determinística.

### 7.2. Limitações da Análise

Esta análise é estritamente estatística e baseada no histórico disponível. Loterias são sistemas projetados para serem imprevisíveis, e qualquer padrão observado no passado é uma flutuação estatística natural, não uma regra preditiva. A probabilidade matemática é a única métrica soberana.

### 7.3. Recomendações Finais

O Super Sete é um jogo de loteria que oferece diversas possibilidades de apostas. Embora a sorte seja o fator predominante, a análise estatística pode auxiliar os apostadores a fazerem escolhas mais informadas sobre **gestão de risco** e **organização de apostas**. 

É fundamental:
- Jogar com responsabilidade
- Estar ciente de que não há garantias de vitória
- Entender que estratégias baseadas em frequências históricas não alteram probabilidades
- Encarar o jogo como entretenimento, não como investimento

---

**Responsável Técnico:** Manus AI - Especialista em Análise de Dados e Estatística Aplicada  
**Data da Auditoria:** 15 de Janeiro de 2026  
**Premissa Fundamental:** O jogo deve ser encarado como entretenimento. A probabilidade matemática é a única métrica soberana.

## Referências

[1] [Rede Loteria - Todos os Resultados do Super Sete](https://redeloteria.com.br/resultados/todos-os-resultados-do-super-sete/)

[2] [KotasPlus - Esquema do Super Sete: segredos que ninguém conta](https://www.kotasplus.com.br/dicas/super-sete/esquema-super-sete)

[3] [Super Sete: como jogar na loteria e qual a chance de ganhar](https://ndmais.com.br/loterias/super-sete-como-jogar-na-loteria-e-qual-a-chance-de-ganhar/)

[4] [Megaloterias - Super Sete: tem que ser na ordem? Descubra como apostar!](https://www.megaloterias.com.br/noticias/super-sete-tem-que-ser-na-ordem-descubra-como-apostar)

[5] [Loterix - Os 7 Melhores Fechamentos Para Apostas Na Super Sete](https://loterix.com.br/blog/estrategia/os-7-melhores-fechamentos-para-apostas-na-super-sete/)

[6] [RecargaPay - Como jogar na Super Sete? Veja como apostar](https://recargapay.com.br/pix/jogar-super-sete)
