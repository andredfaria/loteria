"""Tuning de hiperparâmetros por busca aleatória avaliada com walk-forward.

Cada trial amostra hiperparâmetros do espaço definido em
`config.TUNING_ESPACO`, treina/avalia um NeuralModular via
`evaluation/walkforward.py` (apenas dados estritamente passados — sem
vazamento) e é ranqueado por mean_hits com p-value vs baseline aleatório.
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from lotofacil.experimentos.config import (
    BACKTEST_MIN_TRAIN,
    PRESETS_TREINO,
    RANDOM_SEED,
    TUNING_DIR,
    TUNING_ESPACO,
)
from lotofacil.experimentos.data.feature_flags import FeatureConfig
from lotofacil.experimentos.evaluation.metrics import mean_hits, vs_random_p_value
from lotofacil.experimentos.evaluation.walkforward import walk_forward
from lotofacil.experimentos.models.neural_modular import NeuralModular

logger = logging.getLogger(__name__)

# Acertos esperados do acaso (hipergeométrica 25/15/15): 15*15/25 = 9.0
BASELINE_ALEATORIO_HITS = 9.0


def amostrar_hiperparametros(espaco: dict, rng: random.Random) -> dict:
    """Amostra um conjunto de hiperparâmetros do espaço de busca.

    Args:
        espaco: dict no formato de TUNING_ESPACO (chave = nome da constante
            de config; valor = spec com "tipo" log_uniforme/uniforme/escolha).
        rng: gerador random.Random (seed controlada pelo chamador).

    Returns:
        Dict de overrides prontos para `NeuralModular(hp_overrides=...)`.
    """
    amostrados: dict = {}
    for nome, spec in espaco.items():
        tipo = spec.get("tipo")
        if tipo == "log_uniforme":
            expoente = rng.uniform(math.log10(spec["min"]), math.log10(spec["max"]))
            amostrados[nome] = 10 ** expoente
        elif tipo == "uniforme":
            amostrados[nome] = rng.uniform(spec["min"], spec["max"])
        elif tipo == "escolha":
            escolhido = rng.choice(spec["valores"])
            # Copia listas (ex.: LSTM_UNITS) para não compartilhar referência.
            amostrados[nome] = list(escolhido) if isinstance(escolhido, list) else escolhido
        else:
            raise ValueError(
                f"Tipo de amostragem desconhecido: {tipo!r} (hiperparâmetro {nome!r}). "
                "Tipos válidos: log_uniforme, uniforme, escolha."
            )
    return amostrados


def executar_tuning(
    draws: list,
    config_sig: str = "base+temp+priors",
    n_trials: int = 10,
    n_test: int = 30,
    retrain_every: int = 15,
    min_train: int = BACKTEST_MIN_TRAIN,
    fast: bool = False,
    seed: int = RANDOM_SEED,
    espaco: dict | None = None,
) -> dict:
    """Executa o tuning por busca aleatória com validação walk-forward.

    Cada trial cria um NeuralModular novo com os hiperparâmetros amostrados
    (sobre o preset "rapido" quando fast=True) e o avalia com `walk_forward`,
    que treina somente com concursos anteriores ao concurso previsto.

    Args:
        draws: histórico de sorteios (ordenado ou não — walk_forward ordena).
        config_sig: assinatura das features (ex.: "base+temp+priors").
        n_trials: quantos conjuntos de hiperparâmetros amostrar.
        n_test: janela de teste do walk-forward por trial.
        retrain_every: retreina o modelo a cada N passos do walk-forward.
        min_train: mínimo de concursos antes do primeiro treino.
        fast: usa o preset "rapido" como base de cada trial (CPU amigável).
        seed: seed da amostragem (reprodutibilidade).
        espaco: espaço de busca; default TUNING_ESPACO de config.py.

    Returns:
        Dict com parâmetros da execução e "trials" ordenados por mean_hits
        desc; cada trial tem hiperparâmetros, mean_hits, p_value_vs_random
        e n_avaliados.
    """
    espaco = espaco if espaco is not None else TUNING_ESPACO
    rng = random.Random(seed)
    cfg = FeatureConfig.from_signature(config_sig)
    base_overrides = dict(PRESETS_TREINO["rapido"]) if fast else {}
    iniciado_em = datetime.now().isoformat()

    trials: List[dict] = []
    for i in range(1, n_trials + 1):
        amostrados = amostrar_hiperparametros(espaco, rng)
        # Preset entra primeiro; hiperparâmetros amostrados sobrescrevem.
        hp_overrides = {**base_overrides, **amostrados}
        logger.info("Trial %d/%d: %s", i, n_trials, amostrados)
        t0 = time.monotonic()
        try:
            resultados = walk_forward(
                draws,
                model_factory=lambda hp=hp_overrides: NeuralModular(
                    cfg, hp_overrides=dict(hp)
                ),
                n_test=n_test,
                retrain_every=retrain_every,
                min_train=min_train,
            )
        except Exception as exc:  # trial falho não derruba o tuning inteiro
            logger.error("Trial %d falhou: %s", i, exc)
            trials.append({"trial": i, "hiperparametros": amostrados, "erro": str(exc)})
            continue

        hits = [r["hits"] for r in resultados]
        trials.append({
            "trial": i,
            "hiperparametros": amostrados,
            "mean_hits": round(mean_hits(resultados), 4),
            "p_value_vs_random": vs_random_p_value(hits),
            "n_avaliados": len(resultados),
            "duracao_s": round(time.monotonic() - t0, 2),
        })

    trials.sort(key=lambda t: t.get("mean_hits", -1.0), reverse=True)

    return {
        "config": cfg.signature(),
        "n_trials": n_trials,
        "n_test": n_test,
        "retrain_every": retrain_every,
        "min_train": min_train,
        "fast": fast,
        "seed": seed,
        "baseline_aleatorio_hits": BASELINE_ALEATORIO_HITS,
        "iniciado_em": iniciado_em,
        "finalizado_em": datetime.now().isoformat(),
        "trials": trials,
    }


def salvar_relatorio(resultado: dict) -> Tuple[Path, Path]:
    """Persiste o resultado do tuning em JSON + markdown em TUNING_DIR.

    Returns:
        (caminho_json, caminho_markdown)
    """
    TUNING_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = TUNING_DIR / f"tuning_{ts}.json"
    md_path = TUNING_DIR / f"tuning_{ts}.md"

    json_path.write_text(
        json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    md_path.write_text(_construir_markdown(resultado), encoding="utf-8")
    logger.info("Relatórios gravados: %s / %s", json_path, md_path)
    return json_path, md_path


def _construir_markdown(resultado: dict) -> str:
    """Monta o resumo markdown com a tabela de trials ranqueados."""
    trials = resultado.get("trials", [])

    # Colunas de hiperparâmetros: união ordenada das chaves amostradas.
    hp_nomes: List[str] = []
    for trial in trials:
        for nome in trial.get("hiperparametros", {}):
            if nome not in hp_nomes:
                hp_nomes.append(nome)

    linhas = [
        "# Lotofácil Lab — Tuning por Busca Aleatória",
        "",
        f"**Config:** {resultado.get('config', '?')}  ",
        f"**Trials:** {resultado.get('n_trials', '?')} | "
        f"**n_test:** {resultado.get('n_test', '?')} | "
        f"**retrain_every:** {resultado.get('retrain_every', '?')} | "
        f"**min_train:** {resultado.get('min_train', '?')}  ",
        f"**Fast:** {'sim' if resultado.get('fast') else 'não'} | "
        f"**Seed:** {resultado.get('seed', '?')}  ",
        f"**Início:** {resultado.get('iniciado_em', '?')} | "
        f"**Fim:** {resultado.get('finalizado_em', '?')}",
        "",
        f"Baseline aleatório esperado: **{BASELINE_ALEATORIO_HITS:.1f} acertos** "
        "por jogo (hipergeométrica 25/15/15).",
        "",
        "## Ranking (mean_hits desc)",
        "",
        "| # | Trial | mean_hits | p-value vs random | n avaliados | "
        + " | ".join(hp_nomes) + " |",
        "|---|-------|-----------|-------------------|-------------|"
        + "|".join(["---"] * len(hp_nomes)) + "|",
    ]

    for pos, trial in enumerate(trials, start=1):
        hp = trial.get("hiperparametros", {})
        hp_cols = " | ".join(_formatar_hp(hp.get(nome)) for nome in hp_nomes)
        if "erro" in trial:
            linhas.append(
                f"| {pos} | {trial.get('trial', '?')} | ERRO | — | — | {hp_cols} |"
            )
            continue
        p = trial.get("p_value_vs_random", 1.0)
        linhas.append(
            f"| {pos} | {trial.get('trial', '?')} "
            f"| {trial.get('mean_hits', 0):.4f} "
            f"| {p:.4f} "
            f"| {trial.get('n_avaliados', 0)} "
            f"| {hp_cols} |"
        )

    linhas += [
        "",
        "## Interpretação",
        "",
        "Trials com p-value ≥ 0.05 estão dentro da margem de ruído do acaso — "
        "não trate o ranking como vantagem real sem significância estatística.",
        "",
        "_Relatório gerado automaticamente pelo lotofacil_lab (`lotofacil lab tune`)._",
    ]
    return "\n".join(linhas)


def _formatar_hp(valor) -> str:
    """Formata um hiperparâmetro para célula de tabela markdown."""
    if valor is None:
        return "—"
    if isinstance(valor, float):
        return f"{valor:.6g}"
    if isinstance(valor, list):
        return ",".join(str(v) for v in valor)
    return str(valor)
