from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier

from lotofacil.dominio.entidades import Draw
from lotofacil.infra.atributos.builder import FeatureBuilder

logger = logging.getLogger(__name__)

_NUMBERS = list(range(1, 26))


class FrequenciaAnalyzer:
    def __init__(self, draws: List[Draw]):
        self.draws = draws

    def analisar(self, windows: Tuple[int, ...] = (10, 30, 50, 100)) -> Dict[str, Any]:
        total = len(self.draws)
        bin_matrix = np.zeros((total, 25), dtype=np.int32)
        for i, d in enumerate(self.draws):
            for n in d.dezenas:
                bin_matrix[i, n - 1] = 1

        resultados: Dict[str, Any] = {}
        resultados["total_draws"] = total

        windows_list = list(windows) + [total]
        window_labels = [f"ultimos_{w}" for w in windows] + ["total"]

        ranking_table = []
        for numero in _NUMBERS:
            row = {"numero": numero}
            for w, label in zip(windows_list, window_labels):
                if w > total:
                    continue
            row = {"numero": numero}
            for w, label in zip(windows_list, window_labels):
                if w > total:
                    row[label] = None
                    continue
                start = total - w
                row[label] = int(bin_matrix[start:, numero - 1].sum())
            ranking_table.append(row)

        resultados["ranking"] = ranking_table
        for w, label in zip(windows_list, window_labels):
            top = sorted(
                ranking_table, key=lambda r: (r[label] if r[label] is not None else 0), reverse=True
            )[:10]
            resultados[f"top10_{label}"] = [
                {"numero": r["numero"], "frequencia": r[label]} for r in top
            ]

        return resultados


class CoocorrenciaAnalyzer:
    def __init__(self, draws: List[Draw]):
        self.draws = draws

    def _combinacoes_por_draw(self, k: int) -> Counter:
        counter: Counter = Counter()
        for draw in self.draws:
            nums = sorted(draw.dezenas)
            for combo in combinations(nums, k):
                counter[combo] += 1
        return counter

    def analisar(self, top_n: int = 20) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for k, nome in [(2, "pares"), (3, "triplas"), (4, "quadruplas"), (5, "quintuplas")]:
            counter = self._combinacoes_por_draw(k)
            total_unicas = len(counter)
            mais_frequentes = counter.most_common(top_n)
            result[nome] = {
                "total_combos_unicas": total_unicas,
                "top": [
                    {
                        "sequencia": list(combo),
                        "frequencia": freq,
                        "proporcao": round(freq / len(self.draws) * 100, 2),
                    }
                    for combo, freq in mais_frequentes
                ],
            }
        return result


class MLImportanciaAnalyzer:
    def __init__(self, draws: List[Draw]):
        self.draws = draws

    def analisar(self, top_n: int = 20) -> Dict[str, Any]:
        builder = FeatureBuilder()
        X, y = builder.build_dataset(self.draws)
        feature_names = builder.feature_names

        n_features = X.shape[1]
        importances = np.zeros((25, n_features), dtype=np.float32)

        for i in range(25):
            rf = RandomForestClassifier(
                n_estimators=100, max_depth=8, min_samples_leaf=5,
                random_state=42, n_jobs=-1,
            )
            rf.fit(X, y[:, i])
            importances[i] = rf.feature_importances_

        mean_importances = importances.mean(axis=0)
        std_importances = importances.std(axis=0)

        top_indices = np.argsort(mean_importances)[::-1][:top_n]
        top_features = [
            {
                "feature": feature_names[idx],
                "importancia_media": round(float(mean_importances[idx]), 6),
                "importancia_std": round(float(std_importances[idx]), 6),
            }
            for idx in top_indices
        ]

        por_numero = {}
        for i in range(25):
            ti = np.argsort(importances[i])[::-1][:10]
            por_numero[f"numero_{i+1}"] = [
                {"feature": feature_names[idx], "importancia": round(float(importances[i][idx]), 6)}
                for idx in ti
            ]

        return {
            "top_features_globais": top_features,
            "importancia_por_numero": por_numero,
            "total_features": n_features,
        }


class JogosHistoricosAnalyzer:
    def __init__(self, draws: List[Draw]):
        self.draws = draws

    def _frequencia_total(self) -> np.ndarray:
        freq = np.zeros(25, dtype=np.int32)
        for d in self.draws:
            for n in d.dezenas:
                freq[n - 1] += 1
        return freq

    def _avaliar_jogo(self, jogo: List[int]) -> Dict[str, Any]:
        jogo_set = set(jogo)
        acertos_por_concurso = []
        for d in self.draws:
            hits = len(jogo_set & set(d.dezenas))
            acertos_por_concurso.append(hits)

        arr = np.array(acertos_por_concurso)
        return {
            "jogo": sorted(jogo),
            "soma": sum(jogo),
            "media_acertos": round(float(arr.mean()), 2),
            "mediana_acertos": int(np.median(arr)),
            "max_acertos": int(arr.max()),
            "total_concursos": len(acertos_por_concurso),
            "distribuicao": {
                f"acertos_{h}": int((arr >= h).sum())
                for h in [11, 12, 13, 14, 15]
            },
        }

    def _gerar_candidatos_pool(self, ranking: np.ndarray, tamanho: int, n_candidatos: int) -> List[List[int]]:
        pool_size = min(17 + tamanho, 25)
        pool = [int(i + 1) for i in ranking[:pool_size]]
        seen = set()
        candidatos = []
        for combo in combinations(pool, tamanho):
            key = tuple(sorted(combo))
            if key in seen:
                continue
            seen.add(key)
            candidatos.append(sorted(combo))
            if len(candidatos) >= n_candidatos:
                break
        return candidatos

    def _gerar_candidatos_por_frequencia(self, tamanho: int, n_candidatos: int) -> List[List[int]]:
        freq = self._frequencia_total()
        ranking = np.argsort(freq)[::-1]
        return self._gerar_candidatos_pool(ranking, tamanho, n_candidatos)

    def _gerar_candidatos_por_probabilidade(
        self, tamanho: int, n_candidatos: int, probas: np.ndarray
    ) -> List[List[int]]:
        ranking = np.argsort(probas)[::-1]
        return self._gerar_candidatos_pool(ranking, tamanho, n_candidatos)

    def _backtest_lote(self, candidatos: List[List[int]], top_n: int) -> List[Dict[str, Any]]:
        seen = set()
        results = []
        for jogo in candidatos:
            key = tuple(jogo)
            if key in seen:
                continue
            seen.add(key)
            r = self._avaliar_jogo(jogo)
            score = (
                r["distribuicao"].get("acertos_15", 0) * 1000000
                + r["distribuicao"].get("acertos_14", 0) * 10000
                + r["distribuicao"].get("acertos_13", 0) * 100
                + r["distribuicao"].get("acertos_12", 0) * 1
            )
            results.append((score, r))

        results.sort(key=lambda x: -x[0])
        return [r for _, r in results[:top_n]]

    def analisar(
        self, target: int, top_n: int = 10, n_candidatos: int = 5000
    ) -> Dict[str, Any]:
        if target not in (11, 15):
            raise ValueError("target deve ser 11 ou 15")

        result: Dict[str, Any] = {"tamanho_jogo": target}

        candidatos_freq = self._gerar_candidatos_por_frequencia(target, n_candidatos)
        top_por_freq = self._backtest_lote(candidatos_freq, top_n)
        result["top_por_frequencia"] = top_por_freq

        try:
            builder = FeatureBuilder()
            X, y = builder.build_dataset(self.draws)
            rf = MultiOutputClassifier(
                RandomForestClassifier(
                    n_estimators=100, max_depth=8, min_samples_leaf=5,
                    random_state=42, n_jobs=-1,
                ),
                n_jobs=1,
            )
            rf.fit(X, y)
            x_infer = builder.build_inference(self.draws)
            probas_list = rf.predict_proba(x_infer)
            probas = np.empty(25, dtype=np.float32)
            for j, p in enumerate(probas_list):
                if p.shape[1] == 2:
                    probas[j] = p[0, 1]
                else:
                    probas[j] = float(p[0, 0]) if p.shape[1] == 1 else 0.5

            candidatos_ml = self._gerar_candidatos_por_probabilidade(target, n_candidatos, probas)
            top_por_ml = self._backtest_lote(candidatos_ml, top_n)
            result["top_por_ml"] = top_por_ml
            result["probabilidades_ml"] = probas.tolist()
        except Exception as e:
            logger.warning("Erro ao treinar modelo ML para jogos: %s", e)
            result["top_por_ml"] = []
            result["erro_ml"] = str(e)

        return result


class AnalisadorCompleto:
    def __init__(self, draws: List[Draw]):
        self.draws = draws
        self._freq_analyzer = FrequenciaAnalyzer(draws)
        self._cooc_analyzer = CoocorrenciaAnalyzer(draws)
        self._ml_analyzer = MLImportanciaAnalyzer(draws)
        self._jogos_analyzer = JogosHistoricosAnalyzer(draws)

    def analisar(
        self,
        top_n: int = 20,
        windows: Tuple[int, ...] = (10, 30, 50, 100),
        targets: Tuple[int, ...] = (11, 15),
    ) -> Dict[str, Any]:
        logger.info("Iniciando análise completa...")
        result: Dict[str, Any] = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_draws": len(self.draws),
                "concurso_range": (
                    self.draws[0].concurso if self.draws else None,
                    self.draws[-1].concurso if self.draws else None,
                ),
                "data_range": (
                    self.draws[0].data if self.draws else None,
                    self.draws[-1].data if self.draws else None,
                ),
            }
        }

        logger.info("Analisando frequências...")
        result["frequencia"] = self._freq_analyzer.analisar(windows=windows)

        logger.info("Analisando co-ocorrências...")
        result["coocorrencia"] = self._cooc_analyzer.analisar(top_n=top_n)

        logger.info("Analisando importância de features (RandomForest)...")
        result["importancia_ml"] = self._ml_analyzer.analisar(top_n=top_n)

        for target in targets:
            logger.info("Analisando jogos históricos (%d dezenas)...", target)
            result[f"jogos_{target}_dezenas"] = self._jogos_analyzer.analisar(
                target=target, top_n=min(top_n, 10)
            )

        logger.info("Análise completa finalizada.")
        return result


def salvar_relatorio(resultado: Dict[str, Any], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Relatório salvo em %s", path)
    return path
