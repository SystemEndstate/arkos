"""kwai.py - leitura do export do Kwai for Business com as heurísticas do Kwai.

Usa o leitor comum de arkos-tiktok-ads/scripts/anuncios.py (pasta irmã, tanto em
engine/skills-rascunho quanto em ~/.claude/skills). As colunas do export do Kwai mudam entre
versões do painel: quando faltar coluna, o script para com entrada_incompleta e pede --map.

Uso:
  python kwai.py ler export.csv --cpa-alvo 30 [--roas-alvo 2] [--map map.json] [--out x.json] [--md x.md]
  python kwai.py pronto leitura.json
"""
from __future__ import annotations

import sys
from pathlib import Path

_IRMA = Path(__file__).resolve().parents[2] / "arkos-tiktok-ads" / "scripts"
sys.path.insert(0, str(_IRMA))
import anuncios  # noqa: E402

# Apelidos extras vistos em exports do Kwai (conferir no painel do cliente: a lista muda).
anuncios.ALIASES["views_2s"] += ["reproducoes de 3s", "visualizacoes de 3s", "3s views", "3 second views"]
anuncios.ALIASES["views_6s"] += ["reproducoes de 5s", "visualizacoes de 5s", "5s views"]
anuncios.ALIASES["gasto"] += ["custo total", "investimento"]


def _main(argv: list[str]) -> int:
    if argv and argv[0] == "ler" and "--plataforma" not in argv:
        argv = argv + ["--plataforma", "kwai"]
    return anuncios._main(argv)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
