"""retro.py - projetado × realizado e atualização das premissas (arkos-estrategia-retro).

Uso:
  python retro.py comparar metricas.json [--out retro-dados.json]
    metricas.json: [{"nome": "clientes_novos", "maior_melhor": true,
                     "projetado": {"pessimista": 20, "base": 30, "otimista": 45}, "realizado": 24}]
  python retro.py premissas premissas.yaml julgamentos.json --hoje AAAA-MM-DD --antes retro/<data>-premissas-antes.yaml
    Aplica a regra de confiança comum (premissas.py) e grava a cópia de antes.
  python retro.py decidir decisao.json
    decisao.json: {"refutadas_altas": [...], "metricas_north_star_abaixo_pessimista": 0,
                   "criterio_parada_disparou": false}
    Regra: pivotar-ou-parar se premissa de impacto alto foi refutada; ajustar se 2+ métricas da
    North Star abaixo do pessimista ou critério de parada disparou; perseverar no resto.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

COMP = Path(__file__).resolve().parents[2] / "arkos-estrategia" / "scripts"
sys.path.insert(0, str(COMP))
import premissas as pm  # noqa: E402


def faixa(proj: dict, real: float, maior_melhor: bool = True) -> str:
    p, b, o = proj["pessimista"], proj["base"], proj["otimista"]
    if not maior_melhor:  # inverte para que "acima do otimista" seja sempre o melhor caso
        p, b, o, real = -p, -b, -o, -real
    if not p <= b <= o:
        raise ValueError("projeção fora de ordem: pessimista <= base <= otimista (no sentido da métrica)")
    if real < p:
        return "abaixo do pessimista"
    if real < b:
        return "entre pessimista e base"
    if real <= o:
        return "entre base e otimista"
    return "acima do otimista"


def comparar(metricas: list[dict]) -> dict:
    linhas, erros = [], []
    for m in metricas:
        proj, real = m["projetado"], m.get("realizado")
        if real is None:
            linhas.append({"nome": m["nome"], "realizado": None, "faixa": "sem dado"})
            continue
        dif = real - proj["base"]
        pct = dif / abs(proj["base"]) if proj["base"] else None
        if pct is not None:
            erros.append(abs(pct))
        linhas.append({"nome": m["nome"], "projetado_base": proj["base"], "realizado": real,
                       "diferenca": round(dif, 4), "diferenca_pct": None if pct is None else round(pct, 4),
                       "faixa": faixa(proj, real, m.get("maior_melhor", True))})
    erro_medio = round(sum(erros) / len(erros), 4) if erros else None
    return {"metricas": linhas, "erro_medio_pct": erro_medio,
            "refazer_projecao": erro_medio is not None and erro_medio > 0.30}


def decidir(d: dict) -> dict:
    if d.get("refutadas_altas"):
        return {"decisao": "pivotar ou parar",
                "motivo": "premissa de impacto alto refutada: " + ", ".join(d["refutadas_altas"])}
    if d.get("metricas_north_star_abaixo_pessimista", 0) >= 2 or d.get("criterio_parada_disparou"):
        return {"decisao": "ajustar", "motivo": "métricas da North Star abaixo do pessimista ou critério de parada"}
    return {"decisao": "perseverar", "motivo": "sem refutação de impacto alto nem gatilho de ajuste"}


def _main(argv: list[str]) -> int:
    def opt(n):
        return argv[argv.index(n) + 1] if n in argv else None

    if len(argv) >= 2 and argv[0] == "comparar":
        r = comparar(json.loads(Path(argv[1]).read_text(encoding="utf-8")))
        txt = json.dumps(r, ensure_ascii=False, indent=2)
        if opt("--out"):
            Path(opt("--out")).write_text(txt, encoding="utf-8")
        print(txt)
        return 0
    if len(argv) >= 3 and argv[0] == "premissas":
        if not opt("--hoje") or not opt("--antes"):
            print("premissas exige --hoje e --antes (a cópia de antes é obrigatória na retro)")
            return 2
        return pm._main(["ajustar", argv[1], argv[2], "--hoje", opt("--hoje"), "--antes", opt("--antes")])
    if len(argv) >= 2 and argv[0] == "decidir":
        print(json.dumps(decidir(json.loads(Path(argv[1]).read_text(encoding="utf-8"))), ensure_ascii=False, indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
