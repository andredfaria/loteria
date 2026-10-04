"""Falha se algum link relativo em arquivos .md versionados apontar para nada.

Ignora links com esquema (http, https, mailto, tel, ftp... em qualquer caixa),
URLs que começam em //, âncoras puras (#secao) e tudo o que estiver em blocos
de código cercados (``` e ~~~) ou em código inline. Uso:
    python .github/scripts/verificar_links.py

Não cobre:
- links por referência ([texto][ref] e a definição "[ref]: alvo");
- <a href> e <img src> em HTML;
- âncoras de arquivo: em arq.md#secao só o arquivo é checado, não a seção;
- alvo entre <...>, como [texto](<arq com espaço.md>);
- texto de link com "]" dentro;
- alvo com parênteses;
- blocos de código por indentação, sem cerca.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

RAIZ = Path(__file__).resolve().parents[2]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
ESQUEMA = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
# Abre um bloco cercado: 3 ou mais crases (sem outra crase na linha, senão é
# código inline) ou 3 ou mais til.
CERCA = re.compile(r"^[ \t]*(`{3,}(?![^\n]*`)|~{3,})")
# Código inline: uma sequência de crases até a próxima de mesmo tamanho.
CODIGO_INLINE = re.compile(r"(`+)(?!`).*?(?<!`)\1(?!`)")


def arquivos_md() -> list[Path]:
    saida = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z", "*.md"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout
    return [RAIZ / p for p in saida.split("\0") if p]


def sem_codigo(texto: str) -> str:
    """Esvazia blocos cercados e código inline. As quebras de linha ficam, então
    o número de uma linha no resultado é o mesmo do arquivo."""
    linhas = []
    aberta = ""  # cerca que abriu o bloco atual (``` ou ~~~, no mesmo tamanho)
    for linha in texto.split("\n"):
        if aberta:
            resto = linha.strip()
            if resto and set(resto) == {aberta[0]} and len(resto) >= len(aberta):
                aberta = ""
            linhas.append("")
            continue
        abre = CERCA.match(linha)
        if abre:
            aberta = abre.group(1)
            linhas.append("")
            continue
        linhas.append(CODIGO_INLINE.sub("", linha))
    return "\n".join(linhas)


def links_quebrados(md: Path) -> list[tuple[int, str]]:
    """(linha, alvo) de cada link relativo de `md` que aponta para nada."""
    quebrados = []
    texto = sem_codigo(md.read_text(encoding="utf-8", errors="replace"))
    for achado in LINK.finditer(texto):
        alvo = achado.group(1)
        if alvo.startswith(("#", "//")) or ESQUEMA.match(alvo):
            continue
        caminho = unquote(alvo.split("#", 1)[0])
        if not caminho:
            continue
        destino = (RAIZ / caminho.lstrip("/")) if caminho.startswith("/") else (md.parent / caminho)
        if not destino.exists():
            quebrados.append((texto.count("\n", 0, achado.start(1)) + 1, alvo))
    return quebrados


def main() -> int:
    falhas = 0
    for md in arquivos_md():
        for linha, alvo in links_quebrados(md):
            print(f"{md.relative_to(RAIZ)}:{linha}: link quebrado -> {alvo}")
            falhas += 1
    if falhas:
        print(f"\n{falhas} link(s) quebrado(s).")
        return 1
    print("Links relativos OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
