"""diagnostico.py - métricas por elo, variação entre períodos e simulação +20% (arkos-estrategia-diagnostico).

Modelo do resultado do período atual:
  vendas = topo × Π(taxas do funil)
  lucro  = vendas × (ticket − custo de entrega por venda) − mídia − custos fixos
Cada folha melhora 20% (taxas ×1,2 com teto 1; custos ×0,8) mantendo o resto igual;
o efeito é a diferença no lucro. Candidatos a gargalo: as folhas que PIORARAM contra o
período anterior, ordenadas pelo efeito; depois as demais.

Uso:
  python diagnostico.py entrada.json [--out diagnostico-dados.json]
  entrada.json:
  {"funil": ["leads", "agendamentos", "vendas"],
   "atual": ["2026-08", "2026-09", "2026-10"], "anterior": ["2026-05", "2026-06", "2026-07"],
   "ano_anterior": ["2025-08", ...]?,                      # opcional, para checar sazonalidade
   "meses": {"2026-05": {"leads": 120, "agendamentos": 46, "vendas": 22, "receita": 11000,
                          "midia": 3000, "custo_entrega": 2200, "custos_fixos": 4000,
                          "clientes_ativos_inicio": 80?, "cancelamentos": 6?, "incompleto": false?}}}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ELO_DA_FOLHA = {"topo": "canal", "midia": "canal", "ticket": "oferta",
                "custo_entrega_venda": "operacao", "custos_fixos": "caixa", "churn": "operacao"}
MAIOR_MELHOR = {"topo": True, "midia": False, "ticket": True, "custo_entrega_venda": False,
                "custos_fixos": False, "churn": False, "cac": False}


def _div(a, b):
    return a / b if b else None


def agregar(funil: list[str], meses: dict, periodo: list[str]) -> dict:
    faltam = [m for m in periodo if m not in meses]
    if faltam:
        raise ValueError(f"meses sem dado: {faltam}")
    soma = lambda k: sum(meses[m].get(k, 0) or 0 for m in periodo)  # noqa: E731
    vol = {k: soma(k) for k in funil}
    vendas = vol[funil[-1]]
    ag = {"volumes": vol, "topo": vol[funil[0]],
          "taxas": {f"{funil[i]}->{funil[i + 1]}": _div(vol[funil[i + 1]], vol[funil[i]]) for i in range(len(funil) - 1)},
          "vendas": vendas, "receita": soma("receita"), "midia": soma("midia"),
          "custo_entrega": soma("custo_entrega"), "custos_fixos": soma("custos_fixos")}
    ag["ticket"] = _div(ag["receita"], vendas)
    ag["cac"] = _div(ag["midia"], vendas)
    ag["custo_entrega_venda"] = _div(ag["custo_entrega"], vendas)
    ag["lucro"] = ag["receita"] - ag["custo_entrega"] - ag["midia"] - ag["custos_fixos"]
    base_ch = soma("clientes_ativos_inicio")
    ag["churn"] = _div(soma("cancelamentos"), base_ch) if base_ch else None
    ag["meses_incompletos"] = [m for m in periodo if meses[m].get("incompleto")]
    return ag


def _lucro(topo, taxas, ticket, ce, midia, fixos):
    vendas = topo
    for t in taxas.values():
        vendas *= t
    return vendas * (ticket - ce) - midia - fixos


def simular(ag: dict) -> list[dict]:
    if ag["vendas"] == 0 or any(t is None for t in ag["taxas"].values()):
        raise ValueError("período atual sem vendas ou com etapa zerada: simulação impossível")
    p = dict(topo=ag["topo"], taxas=dict(ag["taxas"]), ticket=ag["ticket"],
             ce=ag["custo_entrega_venda"], midia=ag["midia"], fixos=ag["custos_fixos"])
    base = _lucro(**p)
    folhas = []

    def efeito(nome, elo, **mud):
        q = dict(p, **mud)
        folhas.append({"folha": nome, "elo": elo, "efeito_lucro": round(_lucro(**q) - base, 2)})

    efeito("topo", "canal", topo=p["topo"] * 1.2)
    efeito("midia", "canal", midia=p["midia"] * 0.8)
    for k, t in p["taxas"].items():
        efeito(k, "funil", taxas=dict(p["taxas"], **{k: min(1.0, t * 1.2)}))
    efeito("ticket", "oferta", ticket=p["ticket"] * 1.2)
    efeito("custo_entrega_venda", "operacao", ce=p["ce"] * 0.8)
    efeito("custos_fixos", "caixa", fixos=p["fixos"] * 0.8)
    return folhas


def _var(atual, anterior, maior_melhor=True):
    if atual is None or anterior is None:
        return {"atual": atual, "anterior": anterior, "variacao": None, "piorou": None}
    v = _div(atual - anterior, abs(anterior)) if anterior else None
    piorou = (atual < anterior) if maior_melhor else (atual > anterior)
    return {"atual": round(atual, 4), "anterior": round(anterior, 4),
            "variacao": None if v is None else round(v, 4), "piorou": piorou}


def comparar(at: dict, an: dict) -> dict:
    out = {k: _var(at[k], an[k], MAIOR_MELHOR[k]) for k in ("topo", "midia", "ticket", "custo_entrega_venda",
                                                           "custos_fixos", "cac", "churn")}
    for k in at["taxas"]:
        out[k] = _var(at["taxas"][k], an["taxas"][k], True)
    out["lucro"] = _var(at["lucro"], an["lucro"], True)
    return out


def diagnosticar(e: dict) -> dict:
    funil = e["funil"]
    if len(funil) < 2:
        raise ValueError("funil precisa de pelo menos 2 etapas")
    at = agregar(funil, e["meses"], e["atual"])
    an = agregar(funil, e["meses"], e["anterior"])
    comp = comparar(at, an)
    folhas = simular(at)
    for f in folhas:
        f["piorou"] = comp.get(f["folha"], {}).get("piorou")
    candidatos = sorted(folhas, key=lambda f: (not f["piorou"], -f["efeito_lucro"]))[:3]
    avisos = []
    if at["meses_incompletos"] or an["meses_incompletos"]:
        avisos.append("há mês incompleto no período: " + ", ".join(at["meses_incompletos"] + an["meses_incompletos"]))
    saz = None
    if e.get("ano_anterior"):
        aa = agregar(funil, e["meses"], e["ano_anterior"])
        saz = comparar(at, aa)
        if comp["lucro"]["piorou"] and saz["lucro"]["piorou"] is False:
            avisos.append("o lucro caiu contra o período anterior mas não contra o mesmo período do ano passado: possível sazonalidade")
    return {"atual": at, "anterior": an, "comparacao": comp, "ano_anterior": saz,
            "simulacao_mais_20": sorted(folhas, key=lambda f: -f["efeito_lucro"]),
            "candidatos_gargalo": candidatos, "avisos": avisos}


def _main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    r = diagnosticar(json.loads(Path(argv[0]).read_text(encoding="utf-8")))
    txt = json.dumps(r, ensure_ascii=False, indent=2)
    if "--out" in argv:
        Path(argv[argv.index("--out") + 1]).write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
