# Game Generation - Geração de Jogos

Módulos para geração de jogos baseados em critérios estatísticos.

## Scripts

| Script | Descrição |
|--------|-----------|
| `gerador_jogos_lotofacil.py` | Gerador principal de jogos estatísticos |
| `gerador_carteiras_lotofacil.py` | Gerador de carteiras múltiplas |

## Uso

```bash
# Gerar 10 jogos para o próximo concurso
python src/geracao/gerador_jogos_lotofacil.py

# Gerar para um concurso específico
python src/geracao/gerador_jogos_lotofacil.py --concurso 3584

# Gerar quantidade específica
python src/geracao/gerador_jogos_lotofacil.py --quantidade 20

# Usar configuração ML
python src/geracao/gerador_jogos_lotofacil.py \
    --concurso 3584 \
    --config-from-ml ml/recomendacao_concurso_3585.json
```

## Parâmetros

| Parâmetro | Descrição | Padrão |
|-----------|-----------|--------|
| `--concurso` | Concurso de referência | Próximo ao último |
| `--quantidade` | Número de jogos | 10 |
| `--config-from-ml` | Arquivo de config ML | None |

## Filtros Aplicados

O gerador aplica filtros em cascata:

1. **Nível 1 (84%)**: Soma 171-220
2. **Nível 2 (70%)**: Repetidos 8-10, Pares/Ímpares 7-8
3. **Nível 3 (55%)**: Moldura 8-11

## Saída

Jogos salvos em `saida/jogos/jogo_provavel_N.json`:

```json
[
  ["01", "03", "05", "07", "09", "11", "13", "15", "17", "19", "21", "23", "24", "25"],
  ...
]
```
