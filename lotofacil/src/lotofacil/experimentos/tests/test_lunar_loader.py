"""Regression tests for lunar phase computation.

Guards against the historic bug where `phase` was filled with pylunar's
`fractional_phase()` (illuminated fraction) instead of the cyclic phase
[0,1) derived from the moon's age. The illumination is symmetric around
the full moon, so it cannot tell waxing from waning and labels a full
moon as "Nova". The cyclic phase fixes both.

Reference astronomy (São Paulo, 21h BRT):
  2026-06-14 → new moon   (phase ≈ 0/1, is_new=1)
  2026-06-29 → full moon  (phase ≈ 0.5, is_full=1)
  2026-06-22 → waxing     (phase < 0.5)
  2026-06-06 → waning     (phase > 0.5)
"""
from __future__ import annotations

import math

import pytest

import json

from lotofacil.experimentos.data.lunar_loader import (
    LUNAR_FEATURE_NAMES,
    _cache_path,
    _compute_features_raw,
    recompute_lunar_cache,
)


def _feats(date_iso: str) -> dict:
    return _compute_features_raw(date_iso)


def test_full_moon_has_phase_near_half_and_is_full():
    f = _feats("2026-06-29")
    assert f["phase"] == pytest.approx(0.5, abs=0.06)
    assert f["is_full"] == 1.0
    assert f["is_new"] == 0.0


def test_new_moon_is_new_and_not_full():
    f = _feats("2026-06-14")
    # cyclic phase wraps: near 0 or near 1
    assert min(f["phase"], 1.0 - f["phase"]) < 0.06
    assert f["is_new"] == 1.0
    assert f["is_full"] == 0.0


def test_waxing_phase_below_half_waning_above_half():
    waxing = _feats("2026-06-22")["phase"]   # between new (Jun14) and full (Jun29)
    waning = _feats("2026-06-06")["phase"]   # between full (Jun1) and new (Jun14)
    assert waxing < 0.5 < waning


def test_phase_is_not_illumination_for_gibbous_date():
    # The original bug made phase == illumination. For a waning gibbous
    # (bright but past full) the two must differ substantially.
    f = _feats("2026-06-02")
    assert abs(f["phase"] - f["illumination"]) > 0.1


def test_phase_sin_cos_match_cyclic_phase():
    f = _feats("2026-06-22")
    assert f["phase_sin"] == pytest.approx(math.sin(2 * math.pi * f["phase"]), abs=1e-6)
    assert f["phase_cos"] == pytest.approx(math.cos(2 * math.pi * f["phase"]), abs=1e-6)


def test_schema_has_all_seven_features():
    f = _feats("2026-06-22")
    assert list(f.keys()) == LUNAR_FEATURE_NAMES


def test_recompute_overwrites_a_stale_cache_file(tmp_path, monkeypatch):
    import lotofacil.experimentos.data.lunar_loader as ll
    monkeypatch.setattr(ll, "LUA_DIR", tmp_path)   # isolate from the real cache

    date_iso = "2026-06-29"  # full moon
    path = ll._cache_path(date_iso)
    # Simulate the old bug: phase stored as illumination (~0.999, "Nova" band).
    path.write_text(json.dumps({
        "date": date_iso,
        "features": {k: 0.0 for k in LUNAR_FEATURE_NAMES} | {"phase": 0.999},
    }))

    ll.recompute_lunar_cache(date_iso)

    written = json.loads(path.read_text())["features"]
    assert written["phase"] == pytest.approx(0.5, abs=0.06)   # corrected to full
    assert written["is_full"] == 1.0
