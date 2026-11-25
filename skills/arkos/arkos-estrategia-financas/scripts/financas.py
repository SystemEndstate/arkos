"""financas.py - projeção, unit economics, caixa e sensibilidade (arkos-estrategia-financas).

Determinístico, só biblioteca padrão. Nenhum número da leitura sai fora daqui ou da planilha.

Uso:
  python financas.py calcular financas-entrada.json [--out financas-resultado.json]
  python financas.py conferir financas.xlsx mapa.json financas-resultado.json
      mapa.json: [{"aba": "Caixa", "celula": "C30", "chave": "cenarios.base.caixa_minimo"}]
      Lê os valores já recalculados da planilha (cache do xlsx) e compara com o resultado.

Entrada (por cenário: pessimista, base, otimista):
{
  "moeda": "BRL", "meses": 24, "caixa_inicial": 60000,
  "cenarios": {
    "base": {
      "cobranca": "mensal",              # mensal | unico
      "ticket": 99.0,
      "canais": [{"nome": "meta", "clientes_mes": 12, "cac": 140, "crescimento_mes": 0.05}],
      "churn_mensal": 0.04,              # mensal
      "recompra_media": 0.0,             # unico: compras extras por cliente na vida
      "clientes_iniciais": 0,
      "custo_variavel_cliente": 18.0,    # por cliente ativo/mês (mensal) ou por venda (unico)
      "imposto_receita": 0.06, "taxa_pagamento": 0.035,
      "prazo_recebimento_meses": 0,      # mensal: atraso do recebimento
      "parcelas": 1, "antecipacao": false, "taxa_antecipacao": 0.0,   # unico parcelado
      "custos_fixos_mes": 9000, "crescimento_fixos_mes": 0.0,
      "capital": "nenhum"                # nenhum | credito | risco: teto do payback de caixa (90/180/365 dias) e portão LTV:CAC
    }   # break_even_clientes: ativos (mensal) ou novos por mês (unico), "pessimista": {...}, "otimista": {...}
  }
}
"""
from __future__ import annotations

import copy
import json
import math
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

CENARIOS = ("pessimista", "base", "otimista")
SENSIBILIDADE = ("ticket", "churn_mensal", "cac", "clientes_mes", "custo_variavel_cliente", "custos_fixos_mes")
VARIACAO = 0.20


def _r(x, n=2):
    return None if x is None else round(x + 0.0, n)


PAYBACK_TETO_DIAS = {"nenhum": 90, "credito": 180, "risco": 365}


def _portao(ltv_cac, payback_dias, capital="nenhum"):
    """Portão de unit economics (auditoria e-commerce #5/#6):
    - LTV:CAC >= 2,5:1; sem capital externo exige 3:1 OU payback de caixa dentro do teto;
    - payback de caixa: <= 90 dias sem capital externo, <= 180 com crédito, <= 365 com capital de risco."""
    teto = PAYBACK_TETO_DIAS.get(capital, 90)
    pb_ok = payback_dias is not None and payback_dias <= teto
    pb_txt = f"{payback_dias:g} dias" if payback_dias is not None else "não medido"
    if ltv_cac is None:
        return {"status": "sem_dado", "capital": capital, "ltv_cac_min": 2.5, "payback_teto_dias": teto,
                "motivo": "faltou CAC ou LTV para julgar"}
    if ltv_cac < 2.5:
        status, motivo = "ruim", f"LTV:CAC {ltv_cac:.2f} abaixo do portão 2,5:1"
    elif capital == "nenhum" and ltv_cac < 3.0 and not pb_ok:
        status, motivo = "atencao", (f"sem capital externo pede LTV:CAC >= 3:1 (está {ltv_cac:.2f}) "
                                      f"ou payback de caixa <= {teto} dias ({pb_txt})")
    elif not pb_ok:
        status, motivo = "atencao", f"payback de caixa {pb_txt} acima do teto {teto} para capital '{capital}'"
    else:
        status, motivo = "ok", f"LTV:CAC {ltv_cac:.2f} e payback de caixa {pb_txt} dentro do teto {teto}"
    return {"status": status, "capital": capital, "ltv_cac_min": 3.0 if capital == "nenhum" else 2.5,
            "payback_teto_dias": teto, "motivo": motivo}


def _validar(c: dict, nome: str) -> None:
    if c.get("cobranca", "mensal") not in ("mensal", "unico"):
        raise ValueError(f"{nome}: cobranca deve ser mensal ou unico")
    for k in ("ticket", "custos_fixos_mes"):
        if not isinstance(c.get(k), (int, float)) or c[k] < 0:
            raise ValueError(f"{nome}: '{k}' obrigatório e >= 0")
    if not c.get("canais"):
        raise ValueError(f"{nome}: precisa de pelo menos 1 canal")
    if c.get("cobranca", "mensal") == "mensal" and not 0 < c.get("churn_mensal", 0) < 1:
        raise ValueError(f"{nome}: churn_mensal entre 0 e 1 (exclusivo) na cobrança mensal")
    if c.get("parcelas", 1) < 1:
        raise ValueError(f"{nome}: parcelas >= 1")


def projetar(c: dict, meses: int, caixa_inicial: float) -> dict:
    mensal = c.get("cobranca", "mensal") == "mensal"
    churn = c.get("churn_mensal", 0.0)
    ded = c.get("imposto_receita", 0.0) + c.get("taxa_pagamento", 0.0)
    cv = c.get("custo_variavel_cliente", 0.0)
    ticket = c["ticket"]
    atraso = int(c.get("prazo_recebimento_meses", 0))
    parcelas = int(c.get("parcelas", 1))
    antecipa = bool(c.get("antecipacao", False))
    t_antec = c.get("taxa_antecipacao", 0.0)
    recompra = c.get("recompra_media", 0.0)

    ativos = float(c.get("clientes_iniciais", 0))
    caixa = float(caixa_inicial)
    receitas, linhas = [], []
    for t in range(meses):
        novos = sum(k["clientes_mes"] * (1 + k.get("crescimento_mes", 0.0)) ** t for k in c["canais"])
        mkt = sum(k["clientes_mes"] * (1 + k.get("crescimento_mes", 0.0)) ** t * k["cac"] for k in c["canais"])
        if mensal:
            ativos = ativos * (1 - churn) + novos
            vendas = ativos
        else:
            vendas = novos * (1 + recompra)
            ativos += novos
        receita = vendas * ticket
        receitas.append(receita)
        deducoes = receita * ded
        custo_var = vendas * cv
        fixos = c["custos_fixos_mes"] * (1 + c.get("crescimento_fixos_mes", 0.0)) ** t
        resultado = receita - deducoes - custo_var - mkt - fixos
        if mensal:
            recebido = receitas[t - atraso] if t >= atraso else 0.0
            custo_antec = 0.0
        elif parcelas > 1 and not antecipa:
            recebido = sum(receitas[t - i] / parcelas for i in range(parcelas) if t - i >= 0)
            custo_antec = 0.0
        else:
            custo_antec = receita * t_antec if parcelas > 1 else 0.0
            recebido = receita - custo_antec
        resultado -= custo_antec
        caixa += recebido - deducoes - custo_var - mkt - fixos
        linhas.append({"mes": t + 1, "clientes_novos": _r(novos), "clientes_ativos": _r(ativos),
                       "receita": _r(receita), "deducoes": _r(deducoes), "custo_variavel": _r(custo_var),
                       "marketing": _r(mkt), "custos_fixos": _r(fixos), "custo_antecipacao": _r(custo_antec),
                       "resultado": _r(resultado), "recebido": _r(recebido), "caixa": _r(caixa)})

    # unit economics no mês 1
    n1 = sum(k["clientes_mes"] for k in c["canais"])
    cac = sum(k["clientes_mes"] * k["cac"] for k in c["canais"]) / n1 if n1 else None
    mc = ticket * (1 - ded) - cv - (ticket * t_antec if (not mensal and parcelas > 1 and antecipa) else 0.0)
    capital = c.get("capital", "nenhum")
    if mensal:
        vida = 1 / churn
        # LTV = CM2 acumulada da coorte em 12 meses (não a vida infinita): sum (1-churn)^m, m=0..11
        meses_retidos_12 = (1 - (1 - churn) ** 12) / churn
        ltv = mc * meses_retidos_12
        payback = (cac / mc) if (cac is not None and mc > 0) else None
        be_clientes = math.ceil(c["custos_fixos_mes"] / mc) if mc > 0 else None
    else:
        vida = None
        ltv = mc * (1 + recompra)  # recompra = compras extras na janela de 12 meses
        payback = 0.0 if (cac is not None and ltv >= cac) else None
        # venda única: clientes NOVOS por mês para cobrir os fixos
        be_clientes = math.ceil(c["custos_fixos_mes"] / (ltv - (cac or 0))) if ltv - (cac or 0) > 0 else None
    ltv_cac = ltv / cac if cac else None
    payback_caixa_dias = _r(payback * 30, 0) if payback is not None else None
    caixas = [l["caixa"] for l in linhas]
    minimo = min(caixas)
    mes_min = caixas.index(minimo) + 1
    mes_be = next((l["mes"] for l in linhas if l["resultado"] >= 0), None)
    acaba = next((l["mes"] for l in linhas if l["caixa"] < 0), None)
    return {
        "unit_economics": {
            "cac_misto": _r(cac), "margem_contribuicao_cliente": _r(mc), "vida_media_meses": _r(vida),
            "ltv": _r(ltv), "ltv_base": "CM2 acumulada da coorte em 12 meses",
            "ltv_cac": _r(ltv_cac), "payback_meses": _r(payback), "payback_caixa_dias": payback_caixa_dias,
            "break_even_clientes": be_clientes,
            "portao": _portao(ltv_cac, payback_caixa_dias, capital),
        },
        "mes_break_even": mes_be,
        "caixa_minimo": _r(minimo), "mes_caixa_minimo": mes_min,
        "vale_de_caixa": _r(min(0.0, minimo - caixa_inicial)),
        "mes_caixa_acaba": acaba, "caixa_final": _r(caixas[-1]),
        "receita_total": _r(sum(l["receita"] for l in linhas)),
        "meses": linhas,
    }


def _variar(c: dict, driver: str, fator: float) -> dict:
    v = copy.deepcopy(c)
    if driver in ("cac", "clientes_mes"):
        for k in v["canais"]:
            k[driver] *= fator
    elif driver == "churn_mensal":
        v[driver] = min(0.99, v.get(driver, 0.0) * fator) if v.get(driver) else v.get(driver, 0.0)
    else:
        v[driver] = v.get(driver, 0.0) * fator
    return v


def sensibilidade(c: dict, meses: int, caixa: float) -> list[dict]:
    base = projetar(c, meses, caixa)["caixa_minimo"]
    out = []
    for d in SENSIBILIDADE:
        if d == "churn_mensal" and c.get("cobranca", "mensal") != "mensal":
            continue
        baixo = projetar(_variar(c, d, 1 - VARIACAO), meses, caixa)["caixa_minimo"]
        alto = projetar(_variar(c, d, 1 + VARIACAO), meses, caixa)["caixa_minimo"]
        out.append({"driver": d, "caixa_minimo_menos_20": baixo, "caixa_minimo_mais_20": alto,
                    "efeito": _r(max(abs(baixo - base), abs(alto - base)))})
    return sorted(out, key=lambda x: -x["efeito"])


def calcular(e: dict) -> dict:
    meses = int(e.get("meses", 24))
    if not 1 <= meses <= 60:
        raise ValueError("meses entre 1 e 60")
    caixa = float(e.get("caixa_inicial", 0.0))
    faltam = [n for n in CENARIOS if n not in e.get("cenarios", {})]
    if faltam:
        raise ValueError(f"faltam cenários: {faltam}")
    res = {"moeda": e.get("moeda", "BRL"), "meses": meses, "caixa_inicial": caixa, "cenarios": {}}
    for n in CENARIOS:
        _validar(e["cenarios"][n], n)
        res["cenarios"][n] = projetar(e["cenarios"][n], meses, caixa)
    res["sensibilidade_base"] = sensibilidade(e["cenarios"]["base"], meses, caixa)
    res["top3_drivers"] = [s["driver"] for s in res["sensibilidade_base"][:3]]
    p, b = res["cenarios"]["pessimista"], res["cenarios"]["base"]
    res["avisos"] = []
    if p["receita_total"] > b["receita_total"] or p["caixa_minimo"] > b["caixa_minimo"]:
        res["avisos"].append("cenário pessimista não é pior que o base em receita ou caixa")
    return res


# ---------- conferência com a planilha ----------

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def ler_xlsx(caminho: str | Path) -> dict[str, dict[str, object]]:
    """{aba: {celula: valor}} com os valores em cache (planilha já recalculada)."""
    with zipfile.ZipFile(caminho) as z:
        nomes = z.namelist()
        compart = []
        if "xl/sharedStrings.xml" in nomes:
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
                compart.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
        rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        out = {}
        for s in wb.find("m:sheets", NS):
            alvo = rels[s.get(RNS)].lstrip("/")
            alvo = alvo if alvo.startswith("xl/") else "xl/" + alvo
            celulas = {}
            for c in ET.fromstring(z.read(alvo)).iter(f"{{{NS['m']}}}c"):
                v = c.find("m:v", NS)
                if v is None or v.text is None:
                    continue
                t = c.get("t")
                if t == "s":
                    celulas[c.get("r")] = compart[int(v.text)]
                elif t in ("str", "inlineStr"):
                    celulas[c.get("r")] = v.text
                elif t == "e":
                    celulas[c.get("r")] = "#ERRO:" + v.text
                else:
                    celulas[c.get("r")] = float(v.text)
            out[s.get("name")] = celulas
    return out


def _pegar(d, chave: str):
    for parte in chave.split("."):
        d = d[int(parte)] if re.fullmatch(r"\d+", parte) else d[parte]
    return d


def conferir(xlsx: dict, mapa: list[dict], resultado: dict, tol: float = 0.01) -> dict:
    erros_formula = [f"{aba}!{cel}" for aba, cs in xlsx.items() for cel, v in cs.items()
                     if isinstance(v, str) and v.startswith("#ERRO:")]
    difs = []
    for m in mapa:
        planilha = xlsx.get(m["aba"], {}).get(m["celula"])
        esperado = _pegar(resultado, m["chave"])
        ok = isinstance(planilha, float) and esperado is not None and abs(planilha - esperado) <= tol + 1e-9 * abs(esperado)
        difs.append({"aba": m["aba"], "celula": m["celula"], "chave": m["chave"],
                     "planilha": planilha, "script": esperado, "ok": ok})
    return {"ok": not erros_formula and all(d["ok"] for d in difs),
            "erros_formula": erros_formula, "comparacoes": difs}


def _main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "calcular":
        res = calcular(json.loads(Path(argv[1]).read_text(encoding="utf-8")))
        txt = json.dumps(res, ensure_ascii=False, indent=2)
        if "--out" in argv:
            Path(argv[argv.index("--out") + 1]).write_text(txt, encoding="utf-8")
            print(json.dumps({k: res[k] for k in ("top3_drivers", "avisos")}, ensure_ascii=False))
        else:
            print(txt)
        return 0
    if len(argv) == 4 and argv[0] == "conferir":
        r = conferir(ler_xlsx(argv[1]), json.loads(Path(argv[2]).read_text(encoding="utf-8")),
                     json.loads(Path(argv[3]).read_text(encoding="utf-8")))
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r["ok"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
