# Statistical Analysis - Análise Estatística

Scripts para análise de padrões estatísticos nos dados históricos da Lotofácil.

## Scripts Disponíveis

| Script | Descrição |
|--------|-----------|
| `ciclo_dezenas.py` | Análise de ciclo das dezenas (ausência/proeminência) |
| `analisar_pares_impares.py` | Distribuição de números pares/ímpares |
| `analisar_moldura.py` | Análise de moldura (1-5, 21-25) vs miolo (6-20) |
| `analisar_faixas.py` | Distribuição por faixas de 5 números |
| `analisar_repetidos_consecutivos.py` | Padrões de repetição |
| `ranking_combinacoes_lotofacil.py` | Ranking de combinações |
| `analisar_combinacoes_dezenas.py` | Análise de combinações de dezenas |
| `analisar_combinacoes_ganhadoras.py` | Análise de combinações premiadas |

## Padrões Históricos

Baseado em 3.500+ concursos:

| Padrão | Faixa Ideal | Frequência |
|--------|-------------|------------|
| Soma | 171-220 | ~84% |
| Pares/Ímpares | 7-8 ou 8-7 | ~56% |
| Repetidos do último | 8-10 | ~70% |
| Moldura | 8-11 | ~55% |
| Primos | 4-7 | ~70% |
| Fibonacci | 3-5 | ~65% |

## Uso

```bash
python src/analise/ciclo_dezenas.py
python src/analise/analisar_pares_impares.py
python src/analise/analisar_moldura.py
python src/analise/ranking_combinacoes_lotofacil.py
```
