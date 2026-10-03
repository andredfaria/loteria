"""Falha se algum link relativo em arquivos .md versionados apontar para nada.

Ignora links externos (http/https/mailto) e âncoras puras (#secao). Uso:
    python .github/scripts/verificar_links.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

RAIZ = Path(__file__).resolve().parents[2]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def arquivos_md() -> list[Path]:
    saida = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z", "*.md"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout
    return [RAIZ / p for p in saida.split("\0") if p]


def links_quebrados(md: Path) -> list[str]:
    quebrados = []
    texto = md.read_text(encoding="utf-8", errors="replace")
    for alvo in LINK.findall(texto):
        if alvo.startswith(("http://", "https://", "mailto:", "#")):
            continue
        caminho = unquote(alvo.split("#", 1)[0])
        if not caminho:
            continue
        destino = (RAIZ / caminho.lstrip("/")) if caminho.startswith("/") else (md.parent / caminho)
        if not destino.exists():
            quebrados.append(alvo)
    return quebrados


def main() -> int:
    falhas = 0
    for md in arquivos_md():
        for alvo in links_quebrados(md):
            print(f"{md.relative_to(RAIZ)}: link quebrado -> {alvo}")
            falhas += 1
    if falhas:
        print(f"\n{falhas} link(s) quebrado(s).")
        return 1
    print("Links relativos OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
