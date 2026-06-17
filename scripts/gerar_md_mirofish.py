import json
import os

raiz = os.path.dirname(os.path.dirname(__file__))
json_path = os.path.join(raiz, 'mirofish', 'historico_lotofacil_limpo.json')

with open(json_path, encoding='utf-8') as f:
    dados = json.load(f)

linhas = [
    "# Histórico Lotofácil — Dados Otimizados para MiroFish",
    "",
    "## Descrição dos Campos",
    "",
    "| Campo | Tipo | Descrição |",
    "|-------|------|-----------|",
    "| `concurso` | int | Número do concurso (sorteio), ordenado cronologicamente |",
    "| `data` | str | Data do sorteio no formato DD/MM/AAAA |",
    "| `dezenas` | list[int] | 15 números sorteados (1–25), convertidos para inteiros |",
    "| `estatisticas.pares` | int | Quantidade de números pares no sorteio (0–15) |",
    "| `estatisticas.impares` | int | Quantidade de números ímpares no sorteio (0–15) |",
    "| `estatisticas.soma_total` | int | Soma de todas as 15 dezenas |",
    "",
    f"## Dados Completos ({len(dados)} concursos)",
    "",
    "```json",
]

with open(os.path.join(raiz, 'mirofish', 'historico_lotofacil_limpo.md'), 'w', encoding='utf-8') as md:
    md.write('\n'.join(linhas) + '\n')
    json.dump(dados, md, ensure_ascii=False, indent=2)
    md.write('\n```\n')

tamanho = os.path.getsize(os.path.join(raiz, 'mirofish', 'historico_lotofacil_limpo.md')) / 1024
print(f"OK: {tamanho:.1f} KB")
