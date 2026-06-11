"""Testes do parsing de hiperparâmetros da CLI `lotofacil lab train`."""

import pytest
import typer

from lotofacil.experimentos.main import _parse_lstm_units
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
