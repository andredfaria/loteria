import json
import os

raiz = os.path.dirname(os.path.dirname(__file__))
json_path = os.path.join(raiz, 'mirofish', 'historico_lotofacil_limpo.json')

with open(json_path) as f:
    dados = json.load(f)

md = f"""# Histórico Lotofácil — Dados Otimizados para MiroFish

## Descrição dos Campos

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `concurso` | int | Número do concurso (sorteio), ordenado cronologicamente |
| `data` | str | Data do sorteio no formato DD/MM/AAAA |
| `dezenas` | list[int] | 15 números sorteados (1–25), convertidos para inteiros |
| `estatisticas.pares` | int | Quantidade de números pares no sorteio (0–15) |
| `estatisticas.impares` | int | Quantidade de números ímpares no sorteio (0–15) |
| `estatisticas.soma_total` | int | Soma de todas as 15 dezenas |

## Dados Completos ({len(dados)} concursos)

```json
{json.dumps(dados, ensure_ascii=False, indent=2)}
```
"""

md_path = os.path.join(raiz, 'mirofish', 'historico_lotofacil_limpo.md')
with open(md_path, 'w', encoding='utf-8') as f:
    f.write(md)

tamanho = os.path.getsize(md_path) / 1024
print(f"OK: {md_path} ({tamanho:.1f} KB)")
