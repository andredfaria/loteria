# Dicionário de Dados — Dataset ML Lotofácil

Tabela canônica: uma linha por concurso. Alvo de treino derivado: `saiu_no_proximo` (sorteio do concurso `t+1`, ver `to_training_matrix`).

| Coluna | Tipo | Unidade | Fonte | Papel | Descrição |
|--------|------|---------|-------|-------|-----------|
| `concurso` | int | — | sorteio | meta | Número do concurso (chave primária). |
| `data` | date | YYYY-MM-DD | sorteio | meta | Data do sorteio (ISO). |
| `local` | text | — | sorteio | meta | Local do sorteio. |
| `dezenas` | json[int] | — | sorteio | feature | 15 dezenas sorteadas, ordenadas asc. |
| `dezenas_ordem_sorteio` | json[int] | — | sorteio | alvo | 15 dezenas na ordem física de saída. Fonte do alvo. |
| `primeira_dezena` | int | 1-25 ou nulo | sorteio | feature | Primeira bola sorteada (derivada da ordem); nulo se a ordem estiver ausente. |
| `bola_01` | int | 0/1 | sorteio | feature | 1 se a dezena 1 saiu neste concurso. |
| `bola_02` | int | 0/1 | sorteio | feature | 1 se a dezena 2 saiu neste concurso. |
| `bola_03` | int | 0/1 | sorteio | feature | 1 se a dezena 3 saiu neste concurso. |
| `bola_04` | int | 0/1 | sorteio | feature | 1 se a dezena 4 saiu neste concurso. |
| `bola_05` | int | 0/1 | sorteio | feature | 1 se a dezena 5 saiu neste concurso. |
| `bola_06` | int | 0/1 | sorteio | feature | 1 se a dezena 6 saiu neste concurso. |
| `bola_07` | int | 0/1 | sorteio | feature | 1 se a dezena 7 saiu neste concurso. |
| `bola_08` | int | 0/1 | sorteio | feature | 1 se a dezena 8 saiu neste concurso. |
| `bola_09` | int | 0/1 | sorteio | feature | 1 se a dezena 9 saiu neste concurso. |
| `bola_10` | int | 0/1 | sorteio | feature | 1 se a dezena 10 saiu neste concurso. |
| `bola_11` | int | 0/1 | sorteio | feature | 1 se a dezena 11 saiu neste concurso. |
| `bola_12` | int | 0/1 | sorteio | feature | 1 se a dezena 12 saiu neste concurso. |
| `bola_13` | int | 0/1 | sorteio | feature | 1 se a dezena 13 saiu neste concurso. |
| `bola_14` | int | 0/1 | sorteio | feature | 1 se a dezena 14 saiu neste concurso. |
| `bola_15` | int | 0/1 | sorteio | feature | 1 se a dezena 15 saiu neste concurso. |
| `bola_16` | int | 0/1 | sorteio | feature | 1 se a dezena 16 saiu neste concurso. |
| `bola_17` | int | 0/1 | sorteio | feature | 1 se a dezena 17 saiu neste concurso. |
| `bola_18` | int | 0/1 | sorteio | feature | 1 se a dezena 18 saiu neste concurso. |
| `bola_19` | int | 0/1 | sorteio | feature | 1 se a dezena 19 saiu neste concurso. |
| `bola_20` | int | 0/1 | sorteio | feature | 1 se a dezena 20 saiu neste concurso. |
| `bola_21` | int | 0/1 | sorteio | feature | 1 se a dezena 21 saiu neste concurso. |
| `bola_22` | int | 0/1 | sorteio | feature | 1 se a dezena 22 saiu neste concurso. |
| `bola_23` | int | 0/1 | sorteio | feature | 1 se a dezena 23 saiu neste concurso. |
| `bola_24` | int | 0/1 | sorteio | feature | 1 se a dezena 24 saiu neste concurso. |
| `bola_25` | int | 0/1 | sorteio | feature | 1 se a dezena 25 saiu neste concurso. |
| `temp_min` | float | °C | clima | feature | Clima (temp_min) no dia/horário do sorteio. NaN se ausente. |
| `temp_max` | float | °C | clima | feature | Clima (temp_max) no dia/horário do sorteio. NaN se ausente. |
| `temp_media` | float | °C | clima | feature | Clima (temp_media) no dia/horário do sorteio. NaN se ausente. |
| `temp_sorteio` | float | °C | clima | feature | Clima (temp_sorteio) no dia/horário do sorteio. NaN se ausente. |
| `precip_media` | float | mm | clima | feature | Clima (precip_media) no dia/horário do sorteio. NaN se ausente. |
| `precip_sorteio` | float | mm | clima | feature | Clima (precip_sorteio) no dia/horário do sorteio. NaN se ausente. |
| `wcode_sorteio` | float | código WMO | clima | feature | Clima (wcode_sorteio) no dia/horário do sorteio. NaN se ausente. |
| `wcode_dominante` | float | código WMO | clima | feature | Clima (wcode_dominante) no dia/horário do sorteio. NaN se ausente. |
| `phase` | float | [0,1] | lua | feature | Fase fracionária [0,1): 0=nova, 0.5=cheia. |
| `phase_sin` | float | [-1,1] | lua | feature | sin(2π·phase) — codificação cíclica. |
| `phase_cos` | float | [-1,1] | lua | feature | cos(2π·phase) — codificação cíclica. |
| `illumination` | float | [0,1] | lua | feature | Fração do disco iluminada [0,1]. |
| `age_norm` | float | [0,1] | lua | feature | Dias desde a lua nova / 29.53 → [0,1]. |
| `is_new` | float | [0,1] | lua | feature | 1 se ±1.5d da lua nova. |
| `is_full` | float | [0,1] | lua | feature | 1 se ±1.5d da lua cheia. |
| `dow_sin` | float | [-1,1] | temporal | feature | Codificação cíclica temporal (dow_sin). |
| `dow_cos` | float | [-1,1] | temporal | feature | Codificação cíclica temporal (dow_cos). |
| `mes_sin` | float | [-1,1] | temporal | feature | Codificação cíclica temporal (mes_sin). |
| `mes_cos` | float | [-1,1] | temporal | feature | Codificação cíclica temporal (mes_cos). |
| `tem_clima` | int | 0/1 | cobertura | cobertura | 1 se há dado de clima para o concurso. |
| `tem_lua` | int | 0/1 | cobertura | cobertura | 1 se há dado de lua para a data. |
