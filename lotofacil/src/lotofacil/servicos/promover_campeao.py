"""Seleção e promoção do modelo campeão.

O "campeão" é o modelo cuja predição é usada por padrão (ex.: na tela
"Próximo Concurso"). A escolha é honesta: um candidato só é promovido se
tiver validações suficientes E superar o baseline aleatório com
significância estatística (p < 0.05). Caso contrário o sistema usa o
ensemble e registra o motivo.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from lotofacil.infra.avaliacao.significancia import compare_vs_baseline
from lotofacil.infra.config import RANDOM_SEED, SAIDA_DIR

CAMPEAO_PATH = SAIDA_DIR / "campeao.json"
CAMPEAO_HISTORICO_PATH = SAIDA_DIR / "campeao_historico.json"

MIN_VALIDACOES = 20
MARGEM_MINIMA_HITS = 0.1
MODELO_PADRAO = "ensemble"


@dataclass(frozen=True)
class CampeaoInfo:
    modelo: str
    tipo: str
    mean_hits: float
    baseline_mean_hits: float
    p_value: float
    n_validacoes: int
    promovido_em: str
    motivo: str


def _campeao_padrao(motivo: str, baseline_mean_hits: float = 9.0) -> CampeaoInfo:
    return CampeaoInfo(
        modelo=MODELO_PADRAO,
        tipo=MODELO_PADRAO,
        mean_hits=0.0,
        baseline_mean_hits=baseline_mean_hits,
        p_value=1.0,
        n_validacoes=0,
        promovido_em=datetime.now().isoformat(),
        motivo=motivo,
    )


def baseline_hits_simulados(draws_dezenas: list[list[int]], seed: int = RANDOM_SEED) -> list[int]:
    """Simula acertos de 15 dezenas escolhidas ao acaso para cada sorteio real."""
    rng = random.Random(seed)
    todos = list(range(1, 26))
    hits = []
    for dezenas_reais in draws_dezenas:
        chute = set(rng.sample(todos, 15))
        hits.append(len(chute & set(dezenas_reais)))
    return hits


def selecionar_campeao(
    candidatos: dict[str, list[int]],
    baseline_hits: list[int],
    atual: Optional[CampeaoInfo] = None,
    min_validacoes: int = MIN_VALIDACOES,
    margem_minima: float = MARGEM_MINIMA_HITS,
) -> CampeaoInfo:
    """Escolhe o melhor candidato entre os elegíveis (com validações suficientes).

    `candidatos`: mapa abordagem -> lista de acertos (1 por validação, mais
    recente por último). `baseline_hits`: acertos do baseline aleatório nos
    mesmos sorteios (mesma ordem/tamanho mínimo).
    """
    if not baseline_hits:
        return _campeao_padrao("Sem baseline disponível para comparação")

    baseline_media = sum(baseline_hits) / len(baseline_hits)

    elegiveis = {nome: hits for nome, hits in candidatos.items() if len(hits) >= min_validacoes}
    if not elegiveis:
        return _campeao_padrao(
            f"Validações insuficientes (mínimo {min_validacoes}) — mantendo {MODELO_PADRAO} padrão",
            baseline_mean_hits=baseline_media,
        )

    avaliados = []
    for nome, hits in elegiveis.items():
        n = min(len(hits), len(baseline_hits))
        sig = compare_vs_baseline(hits[:n], baseline_hits[:n])
        avaliados.append((nome, sig, n))

    avaliados.sort(key=lambda t: t[1].model_mean, reverse=True)
    nome, sig, n = avaliados[0]

    if sig.p_value >= 0.05 or sig.model_mean <= sig.baseline_mean:
        return _campeao_padrao(
            "Nenhum modelo supera o acaso com significância estatística (p >= 0.05)",
            baseline_mean_hits=sig.baseline_mean,
        )

    if atual is not None and atual.modelo in elegiveis and atual.modelo != nome:
        if (sig.model_mean - atual.mean_hits) < margem_minima:
            return CampeaoInfo(
                modelo=atual.modelo,
                tipo=atual.tipo,
                mean_hits=atual.mean_hits,
                baseline_mean_hits=sig.baseline_mean,
                p_value=atual.p_value,
                n_validacoes=atual.n_validacoes,
                promovido_em=atual.promovido_em,
                motivo=(
                    f"Desafiante '{nome}' não supera margem mínima de "
                    f"{margem_minima} acertos — mantendo '{atual.modelo}'"
                ),
            )

    return CampeaoInfo(
        modelo=nome,
        tipo=nome,
        mean_hits=round(sig.model_mean, 4),
        baseline_mean_hits=round(sig.baseline_mean, 4),
        p_value=round(sig.p_value, 6),
        n_validacoes=n,
        promovido_em=datetime.now().isoformat(),
        motivo=f"Promovido: mean_hits={sig.model_mean:.3f} vs baseline={sig.baseline_mean:.3f} (p={sig.p_value:.4f})",
    )


def carregar_campeao(path: Path = CAMPEAO_PATH) -> CampeaoInfo:
    if not path.exists():
        return _campeao_padrao(f"Nenhuma promoção registrada — usando {MODELO_PADRAO} padrão")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return CampeaoInfo(**raw)


def salvar_campeao(campeao: CampeaoInfo, path: Path = CAMPEAO_PATH, historico_path: Path = CAMPEAO_HISTORICO_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(campeao), ensure_ascii=False, indent=2), encoding="utf-8")

    historico = []
    if historico_path.exists():
        try:
            historico = json.loads(historico_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            historico = []
    historico.append(asdict(campeao))
    historico_path.write_text(json.dumps(historico, ensure_ascii=False, indent=2), encoding="utf-8")


def promover_campeao_do_historico(
    candidatos: dict[str, list[int]],
    draws_dezenas: list[list[int]],
    path: Path = CAMPEAO_PATH,
    historico_path: Path = CAMPEAO_HISTORICO_PATH,
    min_validacoes: int = MIN_VALIDACOES,
    margem_minima: float = MARGEM_MINIMA_HITS,
) -> CampeaoInfo:
    """Recalcula o campeão a partir do histórico de validações e persiste o resultado."""
    baseline_hits = baseline_hits_simulados(draws_dezenas)
    atual = carregar_campeao(path) if path.exists() else None
    novo = selecionar_campeao(
        candidatos, baseline_hits, atual=atual,
        min_validacoes=min_validacoes, margem_minima=margem_minima,
    )
    salvar_campeao(novo, path=path, historico_path=historico_path)
    return novo
