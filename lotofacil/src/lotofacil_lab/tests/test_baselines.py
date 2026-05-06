"""Tests for random and frequency baselines."""

import pytest

from lotofacil_lab.models.baseline_random import RandomBaseline
from lotofacil_lab.models.baseline_frequency import FrequencyBaseline


def test_random_baseline_output_range():
    model = RandomBaseline()
    model.fit([])
    dezenas = model.predict([])
    assert len(dezenas) == 15
    assert all(1 <= d <= 25 for d in dezenas)
    assert len(set(dezenas)) == 15


def test_random_baseline_reproducible():
    a = RandomBaseline(seed=99)
    b = RandomBaseline(seed=99)
    assert a.predict([]) == b.predict([])


def test_random_baseline_different_seeds():
    a = RandomBaseline(seed=1).predict([])
    b = RandomBaseline(seed=2).predict([])
    assert a != b  # almost certainly different


def test_random_baseline_predict_many():
    model = RandomBaseline()
    games = model.predict_many(5)
    assert len(games) == 5
    for game in games:
        assert len(game) == 15 and len(set(game)) == 15


def test_frequency_baseline_output_range(sample_draws):
    model = FrequencyBaseline()
    model.fit(sample_draws)
    dezenas = model.predict(sample_draws)
    assert len(dezenas) == 15
    assert all(1 <= d <= 25 for d in dezenas)
    assert len(set(dezenas)) == 15


def test_frequency_baseline_empty_fit():
    model = FrequencyBaseline()
    model.fit([])
    dezenas = model.predict([])
    assert len(dezenas) == 15


def test_frequency_baseline_name():
    assert FrequencyBaseline().name == "frequency"


def test_random_baseline_name():
    assert RandomBaseline().name == "random"
