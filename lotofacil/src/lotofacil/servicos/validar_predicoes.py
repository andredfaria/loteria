from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from lotofacil.dominio.entidades import Predicao, Sorteio
from lotofacil.infra.config import DADOS_DIR
from lotofacil.infra.dados.banco import DatabaseManager


@dataclass(frozen=True)
class ResultadoValidacaoPredicao:
    concurso_alvo: int
    dezenas_sugeridas: List[int]
    dezenas_reais: List[int]
    acertos: int
    confianca_media: float
    estrategia: str
    validado: bool


def validar_predicoes(
    concurso_alvo: int,
    predicao: Optional[Predicao] = None,
    usar_banco: bool = True,
) -> ResultadoValidacaoPredicao:
    result_path = DADOS_DIR / f"concurso_{concurso_alvo}.json"
    if not result_path.exists():
        raise FileNotFoundError(f"Sorteio do concurso {concurso_alvo} não encontrado")

    raw = json.loads(result_path.read_text(encoding="utf-8"))
    dezenas_reais = sorted(int(d) for d in raw["dezenas"])

    if predicao is None and usar_banco:
        db = DatabaseManager()
        historico = db.get_prediction_history(limit=100)
        for h in historico:
            if h["concurso_alvo"] == concurso_alvo:
                dezenas = h["dezenas_sugeridas"]
                confianca = h.get("confianca_media", 0.0)
                acertos = len(set(dezenas) & set(dezenas_reais))
                db.update_validation(concurso_alvo, acertos)
                return ResultadoValidacaoPredicao(
                    concurso_alvo=concurso_alvo,
                    dezenas_sugeridas=sorted(dezenas),
                    dezenas_reais=dezenas_reais,
                    acertos=acertos,
                    confianca_media=confianca,
                    estrategia="banco",
                    validado=True,
                )
        raise ValueError(f"Nenhuma predição encontrada no banco para concurso {concurso_alvo}")

    if predicao is None:
        raise ValueError("Nenhuma predição fornecida e usar_banco=False")

    acertos = len(set(predicao.dezenas) & set(dezenas_reais))
    if usar_banco:
        db = DatabaseManager()
        db.update_validation(concurso_alvo, acertos)

    return ResultadoValidacaoPredicao(
        concurso_alvo=concurso_alvo,
        dezenas_sugeridas=sorted(predicao.dezenas),
        dezenas_reais=dezenas_reais,
        acertos=acertos,
        confianca_media=predicao.confianca_media,
        estrategia=predicao.estrategia,
        validado=True,
    )


def validar_todas_pendentes(
    dados_dir: Optional[Path] = None,
    db: Optional[DatabaseManager] = None,
) -> List[ResultadoValidacaoPredicao]:
    """Valida todas as predições pendentes cujo resultado real já está em disco.

    `dados_dir` e `db` são injetáveis para facilitar testes; por padrão usam
    `DADOS_DIR` e o banco padrão do projeto.
    """
    db = db or DatabaseManager()
    dados_dir = dados_dir or DADOS_DIR
    pendentes = db.get_pending_validations()
    resultados = []
    for p in pendentes:
        concurso = p["concurso_alvo"]
        result_path = dados_dir / f"concurso_{concurso}.json"
        if not result_path.exists():
            continue
        raw = json.loads(result_path.read_text(encoding="utf-8"))
        dezenas_reais = sorted(int(d) for d in raw["dezenas"])
        acertos = len(set(p["dezenas_sugeridas"]) & set(dezenas_reais))
        db.update_validation(concurso, acertos)
        resultados.append(
            ResultadoValidacaoPredicao(
                concurso_alvo=concurso,
                dezenas_sugeridas=sorted(p["dezenas_sugeridas"]),
                dezenas_reais=dezenas_reais,
                acertos=acertos,
                confianca_media=0.0,
                estrategia="pendente",
                validado=True,
            )
        )
    return resultados


def resumo_validacoes(resultados: List[ResultadoValidacaoPredicao]) -> str:
    """Monta o resumo PT-BR de um lote de validações.

    Exemplo: "3 predições validadas para o concurso 3701: 10, 9 e 11 acertos".
    """
    if not resultados:
        return "Nenhuma predição pendente foi validada"

    acertos = [str(r.acertos) for r in resultados]
    if len(acertos) == 1:
        acertos_txt = acertos[0]
    else:
        acertos_txt = ", ".join(acertos[:-1]) + " e " + acertos[-1]
    sufixo = "acerto" if len(resultados) == 1 and resultados[0].acertos == 1 else "acertos"

    qtd = len(resultados)
    predicoes_txt = "1 predição validada" if qtd == 1 else f"{qtd} predições validadas"

    concursos = sorted({r.concurso_alvo for r in resultados})
    if len(concursos) == 1:
        return f"{predicoes_txt} para o concurso {concursos[0]}: {acertos_txt} {sufixo}"
    concursos_txt = ", ".join(str(c) for c in concursos)
    return f"{predicoes_txt} para os concursos {concursos_txt}: {acertos_txt} {sufixo}"
