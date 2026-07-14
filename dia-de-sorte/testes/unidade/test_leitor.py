from pathlib import Path

from diadesorte.infra.dados.leitor import load_draws, _parse_raw

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


def test_load_draws_dezenas_validas():
    sorteios = load_draws(FIXTURES)
    for s in sorteios:
        assert len(s.dezenas) == 7
        assert all(1 <= n <= 31 for n in s.dezenas)
        assert len(set(s.dezenas)) == 7


def test_load_draws_mes():
    sorteios = load_draws(FIXTURES)
    assert sorteios[0].mes_sorte == "Julho"
    assert sorteios[1].mes_sorte == "Janeiro"
    assert sorteios[2].mes_sorte == "Dezembro"


def test_parse_raw_valido():
    raw = {"concurso": 1, "data": "01/01/2020", "dezenas": ["01", "02", "03", "04", "05", "06", "07"], "mesSorte": "Março"}
    rec = _parse_raw(raw)
    assert rec is not None
    assert rec.concurso == 1
    assert rec.dezenas == [1, 2, 3, 4, 5, 6, 7]
    assert rec.mes_sorte == "Março"


def test_parse_raw_com_mes_sorte_minusculo():
    raw = {"concurso": 1, "data": "01/01/2020", "dezenas": ["01", "02", "03", "04", "05", "06", "07"], "mes_sorte": "Abril"}
    rec = _parse_raw(raw)
    assert rec is not None
    assert rec.mes_sorte == "Abril"


def test_parse_raw_sem_mes_sorte():
    raw = {"concurso": 1, "data": "01/01/2020", "dezenas": ["01", "02", "03", "04", "05", "06", "07"]}
    rec = _parse_raw(raw)
    assert rec is not None
    assert rec.mes_sorte == ""


def test_parse_raw_dezenas_insuficientes():
    raw = {"concurso": 1, "data": "01/01/2020", "dezenas": ["01", "02", "03", "04", "05", "06"]}
    assert _parse_raw(raw) is None


def test_parse_raw_sem_concurso():
    raw = {"data": "01/01/2020", "dezenas": ["01", "02", "03", "04", "05", "06", "07"]}
    assert _parse_raw(raw) is None
