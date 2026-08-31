from pathlib import Path

from megasena.infra.dados.leitor import load_draws, _parse_raw

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sample_draws"


def _fixture() -> Path:
    return FIXTURES


def test_load_draws_carregar_todas():
    sorteios = load_draws(_fixture())
    assert len(sorteios) == 3
    assert sorteios[0].concurso == 100
    assert sorteios[-1].concurso == 102


def test_load_draws_ordenado():
    sorteios = load_draws(_fixture())
    concursos = [s.concurso for s in sorteios]
    assert concursos == sorted(concursos)


def test_load_draws_dezenas_validas():
    sorteios = load_draws(_fixture())
    for s in sorteios:
        assert len(s.dezenas) == 6
        assert all(1 <= n <= 60 for n in s.dezenas)
        assert len(set(s.dezenas)) == 6


def test_parse_raw_valido():
    raw = {"concurso": 1, "data": "01/01/2020", "dezenas": ["01", "02", "03", "04", "05", "06"]}
    rec = _parse_raw(raw)
    assert rec is not None
    assert rec.concurso == 1
    assert rec.dezenas == [1, 2, 3, 4, 5, 6]


def test_parse_raw_dezenas_insuficientes():
    raw = {"concurso": 1, "data": "01/01/2020", "dezenas": ["01", "02", "03", "04", "05"]}
    assert _parse_raw(raw) is None


def test_parse_raw_sem_concurso():
    raw = {"data": "01/01/2020", "dezenas": ["01", "02", "03", "04", "05", "06"]}
    assert _parse_raw(raw) is None


def test_parse_raw_fora_range():
    raw = {"concurso": 1, "data": "01/01/2020", "dezenas": ["01", "02", "03", "04", "05", "61"]}
    assert _parse_raw(raw) is None