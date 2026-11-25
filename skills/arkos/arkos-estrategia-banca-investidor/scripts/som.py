"""som.py - mercado alcançável (SOM) bottom-up para a banca-investidor.

SOM = Σ por segmento (contagem real × fração alcançável × ticket anual).
Recusa conta top-down: todo segmento precisa de contagem com fonte; campo
'percentual_de_mercado' é rejeitado.

Uso:
  python som.py entrada.json
  entrada.json: {"moeda": "BRL",
                 "segmentos": [{"nome": "escritórios contábeis em 3 capitais", "contagem": 4200,
                                "fonte": "base pública de CNPJ por CNAE, consulta 2026-11",
                                "alcancavel": 0.15, "ticket_anual": 2400}],
                 "tam_contexto": {"valor": 0, "fonte": ""}?}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def calcular(e: dict) -> dict:
    segs = e.get("segmentos") or []
    if not segs:
        raise ValueError("precisa de pelo menos 1 segmento")
    linhas, total = [], 0.0
    for s in segs:
        nome = s.get("nome", "?")
        if "percentual_de_mercado" in s:
            raise ValueError(f"{nome}: conta top-down não vale; use contagem real × fração alcançável")
        if not str(s.get("fonte", "")).strip():
            raise ValueError(f"{nome}: contagem sem fonte")
        if not isinstance(s.get("contagem"), (int, float)) or s["contagem"] < 0:
            raise ValueError(f"{nome}: contagem >= 0")
        if not 0 < s.get("alcancavel", 0) <= 1:
            raise ValueError(f"{nome}: alcancavel entre 0 (exclusivo) e 1")
        if not s.get("ticket_anual", 0) > 0:
            raise ValueError(f"{nome}: ticket_anual > 0")
        clientes = s["contagem"] * s["alcancavel"]
        valor = clientes * s["ticket_anual"]
        total += valor
        linhas.append({"nome": nome, "clientes_alcancaveis": round(clientes, 2),
                       "som_anual": round(valor, 2), "fonte": s["fonte"]})
    out = {"moeda": e.get("moeda", "BRL"), "segmentos": linhas, "som_anual": round(total, 2)}
    tam = e.get("tam_contexto")
    if tam and tam.get("valor"):
        out["tam_contexto"] = tam
        out["som_sobre_tam"] = round(total / tam["valor"], 6)
    return out


def _main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    print(json.dumps(calcular(json.loads(Path(argv[0]).read_text(encoding="utf-8"))), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
