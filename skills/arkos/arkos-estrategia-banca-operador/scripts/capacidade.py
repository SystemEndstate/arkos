"""capacidade.py - capacidade × demanda, mês do estouro, custo de servir e fila (arkos-estrategia-banca-operador).

Horas por mês de um papel = horas_semana × pessoas × 52 ÷ 12.
Demanda do papel no mês = clientes_ativos × horas_cliente_mes + clientes_novos × horas_setup_cliente.
Estouro = primeiro mês com uso > 100%.
Custo de servir por cliente/mês = Σ(horas_cliente_mes × custo_hora) + ferramentas_por_cliente_mes.
Fila (Lei de Little): tempo médio na fila W = L ÷ λ, com L = chamados em aberto em média e
λ = chamados que chegam por hora útil.

Uso:
  python capacidade.py entrada.json [--out banca/operador-capacidade.json]
  entrada.json:
  {"meses": 12,
   "papeis": [{"nome": "gestor de tráfego", "pessoas": 1, "horas_semana": 40, "custo_hora": 60,
               "horas_cliente_mes": 6, "horas_setup_cliente": 8}],
   "ferramentas_por_cliente_mes": 25,
   "custo_variavel_financas": 300,                          # o usado em financas-entrada.json
   "demanda": {"base": {"clientes_iniciais": 5, "novos_mes": 3, "churn_mensal": 0.05}, ...},
   "fila": {"chamados_mes_por_cliente": 4, "horas_uteis_mes": 176, "em_aberto_medio": 6}?}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DIFERENCA_ALERTA = 0.15


def horas_mes(p: dict) -> float:
    return p["horas_semana"] * p["pessoas"] * 52 / 12


def serie(d: dict, meses: int) -> list[tuple[float, float]]:
    """[(ativos, novos)] por mês."""
    if not 0 <= d.get("churn_mensal", 0) < 1:
        raise ValueError("churn_mensal entre 0 e 1")
    ativos, out = float(d.get("clientes_iniciais", 0)), []
    for _ in range(meses):
        novos = float(d["novos_mes"])
        ativos = ativos * (1 - d.get("churn_mensal", 0)) + novos
        out.append((ativos, novos))
    return out


def calcular(e: dict) -> dict:
    meses = int(e.get("meses", 12))
    if not e.get("papeis"):
        raise ValueError("precisa de pelo menos 1 papel")
    res = {"cenarios": {}}
    for nome, d in e["demanda"].items():
        s = serie(d, meses)
        papeis = []
        for p in e["papeis"]:
            cap = horas_mes(p)
            usos = [(a * p["horas_cliente_mes"] + n * p.get("horas_setup_cliente", 0)) / cap if cap else float("inf")
                    for a, n in s]
            estouro = next((i + 1 for i, u in enumerate(usos) if u > 1), None)
            por_cliente = p["horas_cliente_mes"]
            papeis.append({"papel": p["nome"], "horas_mes": round(cap, 2),
                           "uso_por_mes": [round(u, 4) for u in usos],
                           "mes_estouro": estouro,
                           "clientes_ativos_max": int(cap // por_cliente) if por_cliente else None})
        gargalo = min(papeis, key=lambda x: (x["mes_estouro"] or meses + 1, -max(x["uso_por_mes"])))
        res["cenarios"][nome] = {"clientes_ativos": [round(a, 2) for a, _ in s], "papeis": papeis,
                                 "gargalo": gargalo["papel"], "mes_estouro_gargalo": gargalo["mes_estouro"]}
    custo = sum(p["horas_cliente_mes"] * p.get("custo_hora", 0) for p in e["papeis"]) + e.get("ferramentas_por_cliente_mes", 0)
    res["custo_servir_cliente_mes"] = round(custo, 2)
    cvf = e.get("custo_variavel_financas")
    if cvf:
        dif = (custo - cvf) / cvf
        res["diferenca_vs_financas_pct"] = round(dif, 4)
        res["alerta_custo"] = abs(dif) > DIFERENCA_ALERTA
    f = e.get("fila")
    if f:
        ativos_base = res["cenarios"].get("base", next(iter(res["cenarios"].values())))["clientes_ativos"]
        lam = [a * f["chamados_mes_por_cliente"] / f["horas_uteis_mes"] for a in ativos_base]
        res["fila"] = {"chegadas_por_hora": [round(x, 4) for x in lam]}
        if f.get("em_aberto_medio") is not None and lam[-1] > 0:
            res["fila"]["tempo_medio_fila_horas_ultimo_mes"] = round(f["em_aberto_medio"] / lam[-1], 2)
    return res


def _main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    r = calcular(json.loads(Path(argv[0]).read_text(encoding="utf-8")))
    txt = json.dumps(r, ensure_ascii=False, indent=2)
    if "--out" in argv:
        Path(argv[argv.index("--out") + 1]).write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
