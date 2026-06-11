import json

import numpy as np
import pandas as pd

from lotofacil.experimentos.models import modelo_ordem_lgbm as mod


def _long_sintetico(n_concursos=40, seed=0):
    rng = np.random.default_rng(seed)
    recs = []
    for c in range(1, n_concursos + 1):
        ganhadores = set(rng.choice(range(1, 26), size=15, replace=False))
        for numero in range(1, 26):
            recs.append({
                "concurso": c,
                "numero": numero,
                "freq_10": rng.random(),
                "freq_30": rng.random(),
                "freq_100": rng.random(),
                "freq_all": rng.random(),
                "days_since_last": rng.random(),
                "saiu_no_anterior": int(rng.random() > 0.4),
                "saiu_no_proximo": 1 if numero in ganhadores else 0,
            })
    df = pd.DataFrame(recs)
    # Colunas clima/lua/temporal exigidas pelo FEATURE_COLS (preenche com 0)
    for col in mod.FEATURE_COLS:
        if col not in df.columns:
            df[col] = 0.0
    return df


def test_temporal_split_nao_vaza_concursos():
    df = _long_sintetico()
    train, test = mod.temporal_split(df, frac=0.75)
    assert train["concurso"].max() < test["concurso"].min()


def test_train_and_evaluate_retorna_metricas():
    df = _long_sintetico()
    train, test = mod.temporal_split(df, frac=0.75)
    model = mod.train_model(train)
    metrics = mod.evaluate(model, test)
    assert metrics["baseline_aleatorio"] == 9.0
    assert 0 <= metrics["acertos_medio"] <= 15
    assert metrics["n_concursos_teste"] > 0
    assert "logloss" in metrics and "auc" in metrics


def test_predict_top15_retorna_15_dezenas_distintas():
    df = _long_sintetico()
    model = mod.train_model(df)
    # Uma matriz de inferência = 25 linhas (uma por número), só FEATURE_COLS
    inf = df[df["concurso"] == df["concurso"].max()][mod.FEATURE_COLS].copy()
    top15, ranking = mod.predict_top15(model, inf)
    assert len(top15) == 15
    assert len(set(top15)) == 15
    assert all(1 <= n <= 25 for n in top15)
    assert len(ranking) == 25
    # ranking ordenado por proba desc
    assert list(ranking["proba"]) == sorted(ranking["proba"], reverse=True)


def test_save_e_load_model_preserva_predicoes(tmp_path):
    df = _long_sintetico()
    model = mod.train_model(df)
    inf = df[df["concurso"] == df["concurso"].max()][mod.FEATURE_COLS].copy()

    path = tmp_path / "ordem_lgbm.joblib"
    mod.save_model(model, path, metrics={"acertos_medio": 9.1, "baseline_aleatorio": 9.0})
    assert path.exists()
    assert path.with_suffix(".meta.json").exists()

    loaded = mod.load_model(path)
    top15_original, _ = mod.predict_top15(model, inf)
    top15_loaded, _ = mod.predict_top15(loaded, inf)
    assert top15_original == top15_loaded

    meta = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8"))
    assert meta["metrics"]["acertos_medio"] == 9.1
    assert meta["feature_cols"] == mod.FEATURE_COLS
