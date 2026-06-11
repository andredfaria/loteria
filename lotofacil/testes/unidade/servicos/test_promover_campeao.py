"""Testes da seleção e promoção do modelo campeão."""

from __future__ import annotations

import json

from lotofacil.servicos.promover_campeao import (
    MODELO_PADRAO,
    CampeaoInfo,
    baseline_hits_simulados,
    carregar_campeao,
    coletar_acertos_jogos,
    promover_campeao_do_historico,
    salvar_campeao,
    selecionar_campeao,
)


def test_sem_validacoes_suficientes_mantem_padrao():
    candidatos = {"ensemble": [10, 11, 9]}  # apenas 3 validações
    baseline = [9] * 30

    info = selecionar_campeao(candidatos, baseline, min_validacoes=20)

    assert info.modelo == MODELO_PADRAO
    assert "insuficientes" in info.motivo.lower()
    assert info.n_validacoes == 0


def test_modelo_supera_baseline_com_significancia_e_promovido():
    # 30 validações com média bem acima do acaso (~8.9), com alguma variância
    candidatos = {"ml": ([11, 12, 13, 12, 11, 13, 12, 11, 12, 13] * 3)}
    baseline = [8, 9, 9, 10, 9, 8, 10, 9, 9, 8] * 3

    info = selecionar_campeao(candidatos, baseline, min_validacoes=20)

    assert info.modelo == "ml"
    assert info.p_value < 0.05
    assert info.mean_hits > info.baseline_mean_hits
    assert "promovido" in info.motivo.lower()


def test_modelo_empata_com_acaso_mantem_padrao():
    candidatos = {"ml": [9, 10, 8, 9, 10, 9, 8, 9, 10, 9] * 3}  # média ~ baseline
    baseline = [9] * 30

    info = selecionar_campeao(candidatos, baseline, min_validacoes=20)

    assert info.modelo == MODELO_PADRAO
    assert "p >= 0.05" in info.motivo or "supera o acaso" in info.motivo.lower()


def test_desafiante_dentro_da_margem_nao_troca_campeao():
    atual = CampeaoInfo(
        modelo="ml", tipo="ml", mean_hits=11.0, baseline_mean_hits=9.0,
        p_value=0.001, n_validacoes=30, promovido_em="2026-01-01T00:00:00",
        motivo="campeão anterior",
    )
    # neural: media 11.05 (29x11 + 1x12.5) -- 0.05 acima do atual, abaixo da margem (0.1)
    candidatos = {"neural": [11] * 29 + [12.5], "ml": [11] * 30}
    baseline = [9] * 30

    info = selecionar_campeao(candidatos, baseline, atual=atual, min_validacoes=20)

    assert info.modelo == "ml"
    assert "margem" in info.motivo.lower()


def test_desafiante_acima_da_margem_promove():
    atual = CampeaoInfo(
        modelo="ml", tipo="ml", mean_hits=9.0, baseline_mean_hits=9.0,
        p_value=0.001, n_validacoes=30, promovido_em="2026-01-01T00:00:00",
        motivo="campeão anterior",
    )
    # neural: media ~11.93, bem acima da margem em relacao ao atual (9.0)
    candidatos = {"neural": [12] * 29 + [10], "ml": [9] * 30}
    baseline = [9] * 30

    info = selecionar_campeao(candidatos, baseline, atual=atual, min_validacoes=20)

    assert info.modelo == "neural"


def test_baseline_hits_simulados_tamanho_e_intervalo():
    draws = [list(range(1, 16)) for _ in range(10)]
    hits = baseline_hits_simulados(draws)

    assert len(hits) == 10
    assert all(0 <= h <= 15 for h in hits)


def test_salvar_e_carregar_campeao(tmp_path):
    path = tmp_path / "campeao.json"
    historico_path = tmp_path / "campeao_historico.json"
    info = CampeaoInfo(
        modelo="ml", tipo="ml", mean_hits=10.5, baseline_mean_hits=9.0,
        p_value=0.01, n_validacoes=25, promovido_em="2026-01-01T00:00:00",
        motivo="teste",
    )

    salvar_campeao(info, path=path, historico_path=historico_path)

    assert path.exists()
    carregado = carregar_campeao(path=path)
    assert carregado == info

    historico = json.loads(historico_path.read_text(encoding="utf-8"))
    assert len(historico) == 1
    assert historico[0]["modelo"] == "ml"


def test_carregar_campeao_sem_arquivo_retorna_padrao(tmp_path):
    info = carregar_campeao(path=tmp_path / "nao_existe.json")
    assert info.modelo == MODELO_PADRAO
    assert info.n_validacoes == 0


def test_coletar_acertos_jogos_calcula_hits_em_ordem_cronologica(tmp_path):
    jogos_dir = tmp_path / "jogos"
    jogos_dir.mkdir()
    (jogos_dir / "predicao_ordem_102.json").write_text(
        json.dumps({"concurso": 102, "abordagem": "ordem", "dezenas": list(range(1, 16))}),
        encoding="utf-8",
    )
    (jogos_dir / "predicao_ordem_101.json").write_text(
        json.dumps({"concurso": 101, "abordagem": "ordem", "dezenas": list(range(11, 26))}),
        encoding="utf-8",
    )
    # outra abordagem não deve ser considerada
    (jogos_dir / "predicao_ensemble_101.json").write_text(
        json.dumps({"concurso": 101, "abordagem": "ensemble", "dezenas": list(range(1, 16))}),
        encoding="utf-8",
    )

    draws = {101: list(range(1, 16)), 102: list(range(1, 16))}

    hits = coletar_acertos_jogos("ordem", draws, jogos_dir=jogos_dir)

    # ordenado por concurso: 101 (predicao 11-25 vs real 1-15 -> intersecao 11-15 = 5)
    # depois 102 (predicao 1-15 vs real 1-15 -> 15)
    assert hits == [5, 15]


def test_coletar_acertos_jogos_sem_diretorio_retorna_vazio(tmp_path):
    hits = coletar_acertos_jogos("ordem", {}, jogos_dir=tmp_path / "nao_existe")
    assert hits == []


def test_promover_campeao_do_historico_persiste(tmp_path):
    path = tmp_path / "campeao.json"
    historico_path = tmp_path / "campeao_historico.json"
    candidatos = {"ml": [12] * 25}
    draws_dezenas = [list(range(1, 16)) for _ in range(25)]

    novo = promover_campeao_do_historico(
        candidatos, draws_dezenas, path=path, historico_path=historico_path, min_validacoes=20,
    )

    assert path.exists()
    assert novo.modelo == "ml"
    assert carregar_campeao(path=path).modelo == "ml"
