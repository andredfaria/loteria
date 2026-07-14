from pathlib import Path

from supersete.infra.dados.leitor import load_draws, _parse_raw

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sample_draws"


def test_load_draws_carregar_todas():
    sorteios = load_draws(FIXTURES)
    assert len(sorteios) == 3
    assert sorteios[0].concurso == 100
    assert sorteios[-1].concurso == 102


def test_load_draws_ordenado():
    sorteios = load_draws(FIXTURES)
    concursos = [s.concurso for s in sorteios]
    assert concursos == sorted(concursos)


def test_load_draws_digitos_validos():
    sorteios = load_draws(FIXTURES)
    for s in sorteios:
        assert len(s.digitos) == 7
        assert all(0 <= d <= 9 for d in s.digitos)


def test_parse_raw_valido():
    raw = {"concurso": 1, "data": "01/01/2020", "dezenas": ["1", "2", "3", "4", "5", "6", "7"]}
    rec = _parse_raw(raw)
    assert rec is not None
    assert rec.concurso == 1
    assert rec.digitos == [1, 2, 3, 4, 5, 6, 7]


def test_parse_raw_com_zero():
    raw = {"concurso": 1, "data": "01/01/2020", "dezenas": ["0", "0", "0", "0", "0", "0", "0"]}
    rec = _parse_raw(raw)
    assert rec is not None
    assert rec.digitos == [0, 0, 0, 0, 0, 0, 0]


def test_parse_raw_digitos_insuficientes():
    raw = {"concurso": 1, "data": "01/01/2020", "dezenas": ["1", "2", "3", "4", "5", "6"]}
    assert _parse_raw(raw) is None


def test_parse_raw_digito_invalido():
    raw = {"concurso": 1, "data": "01/01/2020", "dezenas": ["1", "2", "3", "4", "5", "6", "10"]}
    assert _parse_raw(raw) is None


def test_parse_raw_sem_concurso():
    raw = {"data": "01/01/2020", "dezenas": ["1", "2", "3", "4", "5", "6", "7"]}
    assert _parse_raw(raw) is None
