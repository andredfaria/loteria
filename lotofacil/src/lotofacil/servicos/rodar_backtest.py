from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from lotofacil.infra.config import DADOS_DIR, MODELOS_DIR
from lotofacil.infra.dados.leitor import load_draws
from lotofacil.infra.avaliacao.backtest import BacktestEngine, BacktestSummary
from lotofacil.infra.avaliacao.baseline import random_game
from lotofacil.infra.avaliacao.metricas import LotofacilMetrics
from lotofacil.infra.avaliacao.gerador_html import HTMLReportGenerator
from lotofacil.infra.modelos.frequency_model import FrequencyModel
from lotofacil.infra.modelos.frequency_ensemble import FrequencyEnsembleModel
from lotofacil.infra.modelos.probabilistic import ProbabilisticModel
from lotofacil.infra.modelos.ensemble import EnsemblePredictor


@dataclass(frozen=True)
class ResultadoBacktest:
    modelos_testados: list[str]
    resumo: dict
    relatorio_path: Optional[str] = None


def rodar_backtest(
    dados_dir: Optional[Path] = None,
    start: Optional[int] = None,
    end: Optional[int] = None,
    train_window: int = 300,
    retrain_every: int = 50,
    out: Optional[Path] = None,
) -> ResultadoBacktest:
    dados_dir = dados_dir or DADOS_DIR

    draws = load_draws(dados_dir)

    concurso_nums = [d.concurso for d in draws]
    start_idx = (
        concurso_nums.index(start) if start and start in concurso_nums
        else max(train_window, len(draws) - 500)
    )
    end_idx = (
        concurso_nums.index(end) + 1 if end and end in concurso_nums
        else len(draws)
    )

    model_configs = [
        ("frequency", FrequencyModel),
        ("frequency_ensemble", FrequencyEnsembleModel),
        ("probabilistic", ProbabilisticModel),
        ("ensemble", EnsemblePredictor),
    ]

    summaries: dict[str, BacktestSummary] = {}
    baseline_results = []

    for name, cls in model_configs:
        engine = BacktestEngine(cls(), train_window=train_window, retrain_every=retrain_every)
        results = engine.run(draws, start_idx=start_idx, end_idx=end_idx)
        summaries[name] = BacktestSummary(model_name=name, results=results)

        if not baseline_results:
            for r in results:
                idx = concurso_nums.index(r.concurso)
                rg = random_game()
                hits = len(set(rg) & set(draws[idx].dezenas))
                baseline_results.append(type("BR", (), {"hits": hits, "concurso": r.concurso})())

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        from lotofacil.infra.config import COST_PER_GAME, PRIZE_TABLE
        HTMLReportGenerator(cost=COST_PER_GAME, prize_table=PRIZE_TABLE).generate(summaries, baseline_results, out)

    resumo = {
        m: {
            "acertos_medio": s.mean_hits,
            "taxas": s.rate_ge,
            "total_testados": len(s.results),
        }
        for m, s in summaries.items()
    }

    return ResultadoBacktest(
        modelos_testados=list(summaries.keys()),
        resumo=resumo,
        relatorio_path=str(out) if out else None,
    )
