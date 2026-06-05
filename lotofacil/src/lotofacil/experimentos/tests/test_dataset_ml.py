import json as _json
import math as _math

from lotofacil.experimentos.data import dataset_ml


def _escrever_concurso(tmp_path, concurso, data, dezenas, ordem):
    payload = {
        "concurso": concurso,
        "data": data,
        "local": "TESTE",
        "dezenas": [f"{d:02d}" for d in dezenas],
        "dezenasOrdemSorteio": [f"{d:02d}" for d in ordem],
    }
    (tmp_path / f"concurso_{concurso}.json").write_text(_json.dumps(payload), encoding="utf-8")


def test_canonical_columns_cobrem_grupos_esperados():
    nomes = [c.name for c in dataset_ml.CANONICAL_COLUMNS]
    # meta
    assert {"concurso", "data", "local"} <= set(nomes)
    # alvo bruto
    assert "dezenas_ordem_sorteio" in nomes
    assert "primeira_dezena" in nomes
    # 25 colunas binárias do sorteio
    assert all(f"bola_{k:02d}" in nomes for k in range(1, 26))
    # clima (8) e lua (7)
    assert "temp_sorteio" in nomes and "wcode_dominante" in nomes
    assert "phase" in nomes and "is_full" in nomes
    # temporal e cobertura
    assert {"dow_sin", "dow_cos", "mes_sin", "mes_cos"} <= set(nomes)
    assert {"tem_clima", "tem_lua"} <= set(nomes)


def test_cada_coluna_tem_papel_valido():
    papeis = {c.role for c in dataset_ml.CANONICAL_COLUMNS}
    assert papeis <= {"meta", "feature", "alvo", "cobertura"}
