"""Testes do tuning por busca aleatória com walk-forward (`lotofacil lab tune`).

Usa um modelo fake (sem TensorFlow) no lugar do NeuralModular para que o
smoke rode em segundos, e verifica que nenhum trial usa dados futuros.
"""

import json
import random

import pytest

from lotofacil.dominio.entidades import Draw
from lotofacil.experimentos.config import PRESETS_TREINO, TUNING_ESPACO
from lotofacil.experimentos.experiments import tuning


# ── Helpers ────────────────────────────────────────────────────────────────────


def _fazer_draws(n: int) -> list:
    """Gera n sorteios sintéticos com concursos consecutivos 1..n."""
    rng = random.Random(0)
    return [
        Draw(
            concurso=c,
            data="2026-01-01",
            dezenas=sorted(rng.sample(range(1, 26), 15)),
        )
        for c in range(1, n + 1)
    ]


class ModeloFake:
    """Stub barato de NeuralModular: registra os concursos vistos no fit().

    A cada predict(), grava em `chamadas` (registro de classe) o conjunto de
    concursos usados no fit e o maior concurso do contexto de predição —
    permitindo a asserção de não-vazamento no teste.
    """

    name = "fake"
    chamadas: list = []          # [{"fit": [...], "max_contexto": int}, ...]
    hp_recebidos: list = []      # hp_overrides passados em cada construção

    def __init__(self, config, hp_overrides=None, fast=False, preset=None):
        self.config = config
        self._hp = dict(hp_overrides or {})
        ModeloFake.hp_recebidos.append(dict(self._hp))
        self._fit_concursos: list = []

    def fit(self, draws):
        self._fit_concursos = [d.concurso for d in draws]

    def predict(self, draws):
        ModeloFake.chamadas.append({
            "fit": list(self._fit_concursos),
            "max_contexto": max(d.concurso for d in draws),
        })
        # Determinístico: 15 primeiros números.
        return list(range(1, 16))

    @classmethod
    def limpar(cls):
        cls.chamadas = []
        cls.hp_recebidos = []


@pytest.fixture()
def modelo_fake(monkeypatch):
    """Substitui NeuralModular dentro de tuning.py pelo stub barato."""
    ModeloFake.limpar()
    monkeypatch.setattr(tuning, "NeuralModular", ModeloFake)
    return ModeloFake


# ── amostrar_hiperparametros ──────────────────────────────────────────────────


def test_amostrar_hiperparametros_dentro_dos_ranges():
    rng = random.Random(123)
    for _ in range(50):
        hp = tuning.amostrar_hiperparametros(TUNING_ESPACO, rng)
        assert set(hp) == set(TUNING_ESPACO)
        assert 1e-4 <= hp["LSTM_LR"] <= 1e-2
        assert 0.1 <= hp["LSTM_DROPOUT"] <= 0.5
        assert hp["LSTM_BATCH_SIZE"] in TUNING_ESPACO["LSTM_BATCH_SIZE"]["valores"]
        assert hp["LSTM_UNITS"] in TUNING_ESPACO["LSTM_UNITS"]["valores"]


def test_amostrar_hiperparametros_reprodutivel_com_mesma_seed():
    hp_a = tuning.amostrar_hiperparametros(TUNING_ESPACO, random.Random(42))
    hp_b = tuning.amostrar_hiperparametros(TUNING_ESPACO, random.Random(42))
    assert hp_a == hp_b


def test_amostrar_hiperparametros_nao_compartilha_lista_com_espaco():
    hp = tuning.amostrar_hiperparametros(TUNING_ESPACO, random.Random(7))
    hp["LSTM_UNITS"].append(999)
    assert all(999 not in v for v in TUNING_ESPACO["LSTM_UNITS"]["valores"])


def test_amostrar_hiperparametros_tipo_invalido_falha():
    with pytest.raises(ValueError, match="Tipo de amostragem desconhecido"):
        tuning.amostrar_hiperparametros(
            {"X": {"tipo": "gaussiana", "min": 0, "max": 1}}, random.Random(0)
        )


# ── executar_tuning (smoke com modelo fake) ───────────────────────────────────


def test_executar_tuning_smoke_e_sem_vazamento(modelo_fake):
    draws = _fazer_draws(80)
    resultado = tuning.executar_tuning(
        draws,
        config_sig="base+temp+priors",
        n_trials=2,
        n_test=6,
        retrain_every=2,
        min_train=50,
        fast=True,
        seed=123,
    )

    assert resultado["config"] == "base+temp+priors"
    assert resultado["n_trials"] == 2
    assert len(resultado["trials"]) == 2

    for trial in resultado["trials"]:
        assert "erro" not in trial
        assert trial["n_avaliados"] == 6
        assert 0.0 <= trial["p_value_vs_random"] <= 1.0
        assert set(trial["hiperparametros"]) == set(TUNING_ESPACO)

    # Ranqueados por mean_hits desc.
    hits = [t["mean_hits"] for t in resultado["trials"]]
    assert hits == sorted(hits, reverse=True)

    # Não-vazamento: para cada predição do concurso t (= max_contexto + 1 em
    # concursos consecutivos), o fit usou apenas concursos < t.
    assert modelo_fake.chamadas, "nenhuma predição registrada"
    for chamada in modelo_fake.chamadas:
        concurso_alvo = chamada["max_contexto"] + 1
        assert chamada["fit"], "fit não foi chamado antes de predict"
        assert all(c < concurso_alvo for c in chamada["fit"])


def test_executar_tuning_fast_aplica_preset_rapido(modelo_fake):
    draws = _fazer_draws(60)
    tuning.executar_tuning(
        draws, n_trials=1, n_test=2, retrain_every=1, min_train=50,
        fast=True, seed=1,
    )
    assert modelo_fake.hp_recebidos
    for hp in modelo_fake.hp_recebidos:
        # Chaves do preset rapido que não são amostradas permanecem.
        assert hp["LSTM_EPOCHS"] == PRESETS_TREINO["rapido"]["LSTM_EPOCHS"]
        # Hiperparâmetros amostrados sobrescrevem o preset.
        assert hp["LSTM_BATCH_SIZE"] in TUNING_ESPACO["LSTM_BATCH_SIZE"]["valores"]
        assert 1e-4 <= hp["LSTM_LR"] <= 1e-2  # amostrado, sobrescreve o default


def test_executar_tuning_reprodutivel_com_mesma_seed(modelo_fake):
    draws = _fazer_draws(60)
    kwargs = dict(n_trials=2, n_test=2, retrain_every=1, min_train=50, seed=99)
    r1 = tuning.executar_tuning(draws, **kwargs)
    r2 = tuning.executar_tuning(draws, **kwargs)
    hp1 = [t["hiperparametros"] for t in r1["trials"]]
    hp2 = [t["hiperparametros"] for t in r2["trials"]]
    assert hp1 == hp2


def test_executar_tuning_trial_com_erro_nao_derruba(modelo_fake, monkeypatch):
    draws = _fazer_draws(60)

    chamadas = {"n": 0}

    def walk_forward_instavel(*args, **kwargs):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise RuntimeError("falha simulada")
        return [{"concurso": 51, "predicted": list(range(1, 16)),
                 "actual": list(range(1, 16)), "hits": 15}]

    monkeypatch.setattr(tuning, "walk_forward", walk_forward_instavel)
    resultado = tuning.executar_tuning(
        draws, n_trials=2, n_test=1, retrain_every=1, min_train=50, seed=5,
    )
    assert len(resultado["trials"]) == 2
    erros = [t for t in resultado["trials"] if "erro" in t]
    ok = [t for t in resultado["trials"] if "erro" not in t]
    assert len(erros) == 1 and "falha simulada" in erros[0]["erro"]
    assert len(ok) == 1
    # Trial com erro vai para o fim do ranking.
    assert "erro" in resultado["trials"][-1]


# ── salvar_relatorio (JSON + markdown) ────────────────────────────────────────


def test_salvar_relatorio_grava_json_e_markdown(modelo_fake, monkeypatch, tmp_path):
    monkeypatch.setattr(tuning, "TUNING_DIR", tmp_path)
    draws = _fazer_draws(60)
    resultado = tuning.executar_tuning(
        draws, n_trials=2, n_test=3, retrain_every=2, min_train=50,
        fast=True, seed=321,
    )
    json_path, md_path = tuning.salvar_relatorio(resultado)

    assert json_path.parent == tmp_path
    assert json_path.name.startswith("tuning_") and json_path.suffix == ".json"
    assert md_path.name.startswith("tuning_") and md_path.suffix == ".md"

    gravado = json.loads(json_path.read_text(encoding="utf-8"))
    assert gravado["config"] == "base+temp+priors"
    assert len(gravado["trials"]) == 2
    assert gravado["baseline_aleatorio_hits"] == 9.0

    md = md_path.read_text(encoding="utf-8")
    assert "Tuning por Busca Aleatória" in md
    assert "mean_hits" in md
    assert "p-value" in md
    for nome in TUNING_ESPACO:
        assert nome in md
    # Uma linha de tabela por trial (linhas começando com "| 1 |", "| 2 |").
    assert "| 1 |" in md and "| 2 |" in md
