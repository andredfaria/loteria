"""Testes do parsing de hiperparâmetros e presets da CLI `lotofacil lab train`."""

import pytest
import typer

from lotofacil.experimentos.config import PRESETS_TREINO
from lotofacil.experimentos.main import _parse_lstm_units, _resolver_preset
from lotofacil.experimentos.data.feature_flags import FeatureConfig
from lotofacil.experimentos.models.neural_modular import NeuralModular


def test_parse_lstm_units_valido():
    assert _parse_lstm_units("256,128,64") == [256, 128, 64]
    assert _parse_lstm_units(" 64 , 32 , 16 ") == [64, 32, 16]


@pytest.mark.parametrize("valor", ["256,128", "a,b,c", "256,128,64,32", "0,32,16", "-1,32,16"])
def test_parse_lstm_units_invalido(valor):
    with pytest.raises(typer.BadParameter):
        _parse_lstm_units(valor)


def test_hiperparametros_efetivos_usa_defaults_do_config():
    from lotofacil.experimentos import config as lab_cfg

    cfg = FeatureConfig.from_signature("base")
    model = NeuralModular(cfg)
    hp = model.hiperparametros_efetivos()
    assert hp["LSTM_BATCH_SIZE"] == lab_cfg.LSTM_BATCH_SIZE
    assert hp["LSTM_LR"] == lab_cfg.LSTM_LR
    assert hp["LSTM_UNITS"] == lab_cfg.LSTM_UNITS
    assert hp["NEURAL_VAL_SPLIT"] == lab_cfg.NEURAL_VAL_SPLIT


def test_hiperparametros_efetivos_respeita_overrides():
    cfg = FeatureConfig.from_signature("base")
    model = NeuralModular(cfg, hp_overrides={"LSTM_BATCH_SIZE": 64, "LSTM_DROPOUT": 0.2})
    hp = model.hiperparametros_efetivos()
    assert hp["LSTM_BATCH_SIZE"] == 64
    assert hp["LSTM_DROPOUT"] == 0.2


def test_hiperparametros_efetivos_modo_fast():
    cfg = FeatureConfig.from_signature("base")
    model = NeuralModular(cfg, fast=True)
    hp = model.hiperparametros_efetivos()
    assert hp["LSTM_UNITS"] == [64, 32, 16]
    assert hp["LSTM_BATCH_SIZE"] == 64


def test_override_explicito_vence_modo_fast():
    cfg = FeatureConfig.from_signature("base")
    model = NeuralModular(cfg, hp_overrides={"LSTM_BATCH_SIZE": 128}, fast=True)
    assert model.hiperparametros_efetivos()["LSTM_BATCH_SIZE"] == 128


# ── Presets de treino (--preset rapido|equilibrado|completo) ──────────────────


def test_preset_rapido_aplica_valores():
    overrides = _resolver_preset("rapido")
    model = NeuralModular(FeatureConfig.from_signature("base"),
                          hp_overrides=overrides, preset="rapido")
    hp = model.hiperparametros_efetivos()
    assert hp["LSTM_UNITS"] == [64, 32, 16]
    assert hp["LSTM_BATCH_SIZE"] == 64
    assert hp["LSTM_DROPOUT"] == 0.2
    assert hp["LSTM_DROPOUT_DENSE"] == 0.15
    assert hp["ATTENTION_HEADS"] == 2
    assert hp["ATTENTION_DIM"] == 16
    assert hp["LSTM_EPOCHS"] == 40
    assert hp["LSTM_PATIENCE"] == 5


def test_preset_equilibrado_aplica_valores():
    overrides = _resolver_preset("equilibrado")
    model = NeuralModular(FeatureConfig.from_signature("base"),
                          hp_overrides=overrides, preset="equilibrado")
    hp = model.hiperparametros_efetivos()
    assert hp["LSTM_UNITS"] == [128, 64, 32]
    assert hp["LSTM_EPOCHS"] == 60
    assert hp["LSTM_PATIENCE"] == 8
    assert hp["LSTM_BATCH_SIZE"] == 32


def test_preset_completo_mantem_defaults():
    from lotofacil.experimentos import config as lab_cfg

    overrides = _resolver_preset("completo")
    assert overrides == {}
    model = NeuralModular(FeatureConfig.from_signature("base"),
                          hp_overrides=overrides, preset="completo")
    hp = model.hiperparametros_efetivos()
    assert hp["LSTM_UNITS"] == lab_cfg.LSTM_UNITS
    assert hp["LSTM_EPOCHS"] == lab_cfg.LSTM_EPOCHS
    assert hp["LSTM_PATIENCE"] == lab_cfg.LSTM_PATIENCE
    assert hp["LSTM_BATCH_SIZE"] == lab_cfg.LSTM_BATCH_SIZE


def test_flag_explicita_vence_preset():
    # Simula a montagem da CLI: preset primeiro, flag explícita por cima.
    overrides = _resolver_preset("rapido")
    overrides["LSTM_EPOCHS"] = 99       # --epochs 99
    overrides["LSTM_BATCH_SIZE"] = 16   # --batch-size 16
    model = NeuralModular(FeatureConfig.from_signature("base"),
                          hp_overrides=overrides, preset="rapido")
    hp = model.hiperparametros_efetivos()
    assert hp["LSTM_EPOCHS"] == 99
    assert hp["LSTM_BATCH_SIZE"] == 16
    # O restante do preset permanece valendo.
    assert hp["LSTM_UNITS"] == [64, 32, 16]
    assert hp["LSTM_PATIENCE"] == 5


def test_preset_sem_valor_retorna_vazio():
    assert _resolver_preset(None) == {}


def test_preset_invalido_falha():
    with pytest.raises(typer.BadParameter, match="Preset inválido"):
        _resolver_preset("turbo")


def test_resolver_preset_nao_muta_config():
    overrides = _resolver_preset("rapido")
    overrides["LSTM_EPOCHS"] = 1
    assert PRESETS_TREINO["rapido"]["LSTM_EPOCHS"] == 40


def test_cli_train_preset_invalido_falha():
    from typer.testing import CliRunner
    from lotofacil.experimentos.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["train", "--preset", "turbo"])
    assert result.exit_code != 0
    try:
        saida = result.output + result.stderr
    except ValueError:  # versões antigas do click misturam stderr em output
        saida = result.output
    assert "Preset inválido" in saida


def test_meta_json_registra_preset(tmp_path):
    """save() deve gravar o preset usado no meta.json (sem treinar de verdade)."""
    import json
    from pathlib import Path
    from types import SimpleNamespace

    overrides = _resolver_preset("rapido")
    model = NeuralModular(FeatureConfig.from_signature("base"),
                          hp_overrides=overrides, preset="rapido")
    # Stub do modelo Keras para evitar treino real.
    model._fitted = True
    model._model = SimpleNamespace(
        save=lambda p: Path(p).write_text("stub", encoding="utf-8")
    )
    destino = tmp_path / "neural_teste.keras"
    model.save(destino)

    meta = json.loads(destino.with_suffix(".meta.json").read_text(encoding="utf-8"))
    assert meta["preset"] == "rapido"
    assert meta["hp_efetivos"]["LSTM_UNITS"] == [64, 32, 16]
    assert meta["hp_efetivos"]["LSTM_EPOCHS"] == 40
