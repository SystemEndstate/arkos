"""rice.py - priorização RICE ou ICE e corte pelo prazo (arkos-estrategia-produto).

RICE = alcance × impacto × confiança ÷ esforço
  impacto ∈ {0.25, 0.5, 1, 2, 3}; confiança ∈ {0.5, 0.8, 1}; esforço em semanas-pessoa (> 0).
ICE  = impacto × confiança × facilidade, cada um de 1 a 10.

Corte: segue a ordem da nota e para no primeiro item que não cabe na capacidade
(prazo_semanas × pessoas), para não pular prioridade. Sem 'job' = vai para "depois".

Uso:
  python rice.py entrada.json [--out produto-rice.json]
  entrada.json: {"modo": "rice"|"ice", "prazo_semanas": 6, "pessoas": 1.5,
                 "itens": [{"id": "F1", "nome": "...", "job": "J1", "alcance": 200, "impacto": 2,
                            "confianca": 0.8, "esforco": 2}]}
  (ICE: "impacto", "confianca", "facilidade" de 1 a 10 e "esforco" em semanas-pessoa)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

IMPACTOS = {0.25, 0.5, 1, 2, 3}
CONFIANCAS = {0.5, 0.8, 1}


def _nota(item: dict, modo: str) -> float:
    if modo == "rice":
        if item.get("impacto") not in IMPACTOS:
            raise ValueError(f"{item['id']}: impacto RICE deve ser um de {sorted(IMPACTOS)}")
        if item.get("confianca") not in CONFIANCAS:
            raise ValueError(f"{item['id']}: confiança RICE deve ser 0.5, 0.8 ou 1")
        if not item.get("alcance", 0) >= 0:
            raise ValueError(f"{item['id']}: alcance >= 0")
        return item["alcance"] * item["impacto"] * item["confianca"] / item["esforco"]
    for k in ("impacto", "confianca", "facilidade"):
        if not 1 <= item.get(k, 0) <= 10:
            raise ValueError(f"{item['id']}: {k} ICE de 1 a 10")
    return item["impacto"] * item["confianca"] * item["facilidade"]


def priorizar(e: dict) -> dict:
    modo = e.get("modo", "rice")
    if modo not in ("rice", "ice"):
        raise ValueError("modo deve ser rice ou ice")
    capacidade = float(e["prazo_semanas"]) * float(e["pessoas"])
    ids = set()
    pontuados, sem_job = [], []
    for it in e["itens"]:
        if it["id"] in ids:
            raise ValueError(f"id repetido: {it['id']}")
        ids.add(it["id"])
        if not it.get("esforco", 0) > 0:
            raise ValueError(f"{it['id']}: esforço > 0")
        linha = dict(it, nota=round(_nota(it, modo), 2))
        (pontuados if it.get("job") else sem_job).append(linha)
    pontuados.sort(key=lambda x: (-x["nota"], x["esforco"], x["id"]))
    agora, proximo, usado, cheio = [], [], 0.0, False
    for it in pontuados:
        if not cheio and usado + it["esforco"] <= capacidade + 1e-9:
            agora.append(it)
            usado += it["esforco"]
        else:
            cheio = True
            proximo.append(it)
    return {"modo": modo, "capacidade_semanas_pessoa": round(capacidade, 2),
            "esforco_agora": round(usado, 2), "agora": agora, "proximo": proximo,
            "depois_sem_job": sem_job,
            "aviso": None if agora or not pontuados else "nem o primeiro item cabe no prazo: rever escopo ou prazo"}


def _main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    r = priorizar(json.loads(Path(argv[0]).read_text(encoding="utf-8")))
    txt = json.dumps(r, ensure_ascii=False, indent=2)
    if "--out" in argv:
        Path(argv[argv.index("--out") + 1]).write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
