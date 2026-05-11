# Validation - Validação

Scripts para validação de jogos gerados contra resultados históricos.

## Scripts

| Script | Descrição |
|--------|-----------|
| `validar_jogos_provaveis.py` | Valida jogos gerados contra sorteios reais |
| `validar_aposta_lotofacil.py` | Valida uma aposta específica |

## Uso

```bash
# Validar jogos prováveis
python src/validacao/validar_jogos_provaveis.py

# Validar aposta específica
python src/validacao/validar_aposta_lotofacil.py --jogo "01,02,03,04,05,06,07,08,09,10,11,12,13,14,15"
```

## Métricas

- **Acertos**: 11-15 acertos
- **Hits esperados**: Média de acertos
- **Probabilidade**: Probabilidade de 11+ acertos
