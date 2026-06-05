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


def test_load_raw_draws_le_ordem_e_ordena(tmp_path):
    _escrever_concurso(tmp_path, 2, "06/10/2003", [1, 2, 3], [3, 1, 2])
    _escrever_concurso(tmp_path, 1, "29/09/2003", [5, 6, 7], [7, 6, 5])
    rows = dataset_ml._load_raw_draws(tmp_path)
    assert [r["concurso"] for r in rows] == [1, 2]          # ordenado asc
    assert rows[0]["dezenas"] == [5, 6, 7]                   # convertido p/ int e sorted
    assert rows[0]["dezenas_ordem_sorteio"] == [7, 6, 5]     # ordem preservada
    assert rows[0]["local"] == "TESTE"


def test_clima_fields_ausente_vira_nan():
    out = dataset_ml._clima_fields(None)
    assert set(out) == set(dataset_ml.CLIMA_COLS)
    assert all(_math.isnan(v) for v in out.values())


def test_clima_fields_mapeia_chaves_do_resumo():
    resumo = {"temp_sorteio": 20.8, "precipitacao_media": None,
              "weathercode_dominante": 3}
    out = dataset_ml._clima_fields(resumo)
    assert out["temp_sorteio"] == 20.8
    assert out["wcode_dominante"] == 3
    assert _math.isnan(out["precip_media"])     # None -> NaN


def test_temporal_fields_quarta_feira():
    # 2003-10-01 é quarta-feira (weekday=2)
    out = dataset_ml._temporal_fields("2003-10-01")
    assert abs(out["dow_sin"] - _math.sin(2 * _math.pi * 2 / 7)) < 1e-6
    assert set(out) == set(dataset_ml.TEMPORAL_COLS)


def test_temporal_fields_data_invalida_vira_nan():
    out = dataset_ml._temporal_fields("")
    assert all(_math.isnan(v) for v in out.values())


def test_build_dataset_uma_linha_por_concurso_e_binarios(tmp_path, monkeypatch):
    _escrever_concurso(tmp_path, 1, "29/09/2003", [2, 3, 5], [5, 3, 2])
    _escrever_concurso(tmp_path, 2, "06/10/2003", [1, 2, 4], [4, 2, 1])
    # Sem clima/lua reais nesse tmp: força ausência
    monkeypatch.setattr(dataset_ml, "load_all_climate", lambda: {})
    monkeypatch.setattr(dataset_ml, "compute_lunar_features",
                        lambda iso: __import__("numpy").zeros(len(dataset_ml.LUNAR_FEATURE_NAMES)))

    df = dataset_ml.build_dataset(tmp_path)
    assert len(df) == 2
    linha1 = df[df["concurso"] == 1].iloc[0]
    assert linha1["bola_02"] == 1 and linha1["bola_03"] == 1 and linha1["bola_05"] == 1
    assert linha1["bola_01"] == 0
    assert linha1["primeira_dezena"] == 5            # 1º da ordem
    assert linha1["tem_clima"] == 0                  # forçado ausente
    assert linha1["data"] == "2003-09-29"            # normalizado p/ ISO
    # todas as colunas canônicas presentes
    nomes = {c.name for c in dataset_ml.CANONICAL_COLUMNS}
    assert nomes <= set(df.columns)
