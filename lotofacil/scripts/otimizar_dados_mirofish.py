import json
import glob
import os
import sys

pasta_dados = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dados')
saida_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mirofish')
arquivos = sorted(
    glob.glob(os.path.join(pasta_dados, 'concurso_*.json')),
    key=lambda x: int(x.split('_')[-1].replace('.json', ''))
)

dados_limpos = []
erros = []

for arquivo in arquivos:
    with open(arquivo, 'r', encoding='utf-8') as f:
        try:
            conteudo = f.read()
            dados_brutos = json.loads(conteudo)

            dezenas_int = [int(d) for d in dados_brutos['dezenas']]
            pares = sum(1 for d in dezenas_int if d % 2 == 0)
            impares = 15 - pares
            soma = sum(dezenas_int)

            sorteio_limpo = {
                "concurso": dados_brutos["concurso"],
                "data": dados_brutos["data"],
                "dezenas": dezenas_int,
                "estatisticas": {
                    "pares": pares,
                    "impares": impares,
                    "soma_total": soma
                }
            }
            dados_limpos.append(sorteio_limpo)

        except Exception as e:
            erros.append(f"{os.path.basename(arquivo)}: {e}")

dados_limpos.sort(key=lambda x: x['concurso'])

os.makedirs(saida_dir, exist_ok=True)
caminho_saida = os.path.join(saida_dir, 'historico_lotofacil_limpo.json')
with open(caminho_saida, 'w', encoding='utf-8') as f:
    json.dump(dados_limpos, f, ensure_ascii=False, indent=2)

print(f"OK: {len(dados_limpos)} concursos processados")
print(f"SAIDA: {caminho_saida}")
print(f"TAMANHO: {os.path.getsize(caminho_saida) / 1024:.1f} KB")
if erros:
    print(f"ERROS: {len(erros)}")
    for e in erros[:5]:
        print(f"  - {e}")
