"""Test fixtures for lotofacil_lab tests."""

import sys
from pathlib import Path

import pytest

# Ensure src/ is importable
_SRC = Path(__file__).resolve().parent.parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from lotofacil.experimentos.config import TOTAL_NUMBERS, NUMBERS_PER_DRAW  # noqa: E402
from lotofacil.dominio.entidades import Draw  # noqa: E402


def _make_draw(concurso: int, dezenas: list, data: str = "01/01/2020") -> Draw:
    return Draw(concurso=concurso, data=data, dezenas=dezenas)


@pytest.fixture
def sample_draws():
    """50 synthetic draws with deterministic dezenas for unit tests."""
    import numpy as np
    rng = np.random.default_rng(42)
    draws = []
    year_start = 2018
    for i in range(50):
        month = (i % 12) + 1
        day = (i % 28) + 1
        data = f"{day:02d}/{month:02d}/{year_start + i // 12}"
        dezenas = sorted(rng.choice(TOTAL_NUMBERS, NUMBERS_PER_DRAW, replace=False).tolist())
        dezenas = [int(d) + 1 for d in dezenas]
        # Ensure unique sorted ints in [1,25]
        dezenas = sorted(set(dezenas))[:NUMBERS_PER_DRAW]
        if len(dezenas) < NUMBERS_PER_DRAW:
            # Fill gaps
            missing = [x for x in range(1, 26) if x not in dezenas]
            dezenas += missing[:NUMBERS_PER_DRAW - len(dezenas)]
            dezenas = sorted(dezenas[:NUMBERS_PER_DRAW])
        draws.append(Draw(concurso=i + 1, data=data, dezenas=dezenas))
    return draws


@pytest.fixture
def minimal_draws():
    """Minimal set of 10 draws for smoke tests."""
    import numpy as np
    rng = np.random.default_rng(7)
    draws = []
    for i in range(10):
        dezenas = sorted(rng.choice(TOTAL_NUMBERS, NUMBERS_PER_DRAW, replace=False).tolist())
        dezenas = [int(d) + 1 for d in dezenas]
        dezenas = sorted(set(dezenas))[:NUMBERS_PER_DRAW]
        if len(dezenas) < NUMBERS_PER_DRAW:
            missing = [x for x in range(1, 26) if x not in dezenas]
            dezenas += missing[:NUMBERS_PER_DRAW - len(dezenas)]
            dezenas = sorted(dezenas[:NUMBERS_PER_DRAW])
        draws.append(Draw(concurso=i + 1, data=f"0{i+1}/01/2024" if i < 9 else "10/01/2024",
                          dezenas=dezenas))
    return draws
