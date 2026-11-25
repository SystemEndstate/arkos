#!/usr/bin/env python3
"""arkos-engenharia-reversa: ledger de obrigacoes de reconstrucao. Stdlib.

Cada comportamento a reconstruir e uma obrigacao; coleta-se evidencia (estatica,
dinamica, rede) por obrigacao e mede-se cobertura. Sem evidencia = em_aberto.
"""
import argparse
import json
import sys

TIPOS_EVIDENCIA = {"estatica", "dinamica", "rede"}


def montar(obrigacoes):
    """obrigacoes: [{id, descricao, evidencias:[{tipo, ref}]}]."""
    saida, em_aberto = [], []
    com_evid = 0
    for o in obrigacoes:
        evid = [e for e in o.get("evidencias", []) if e.get("tipo") in TIPOS_EVIDENCIA and e.get("ref")]
        status = "coberta" if evid else "em_aberto"
        if evid:
            com_evid += 1
        else:
            em_aberto.append(o.get("id") or o.get("descricao"))
        saida.append({"id": o.get("id"), "descricao": o.get("descricao"),
                      "evidencias": evid, "status": status})
    total = len(obrigacoes)
    cobertura = round(com_evid / total, 3) if total else 0.0
    return {"obrigacoes": saida, "cobertura": cobertura, "total": total,
            "em_aberto": em_aberto}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="er")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("ledger")
    m.add_argument("--arquivo", required=True, help="JSON [{id,descricao,evidencias}]")
    args = ap.parse_args(argv)
    if args.cmd == "ledger":
        with open(args.arquivo, encoding="utf-8") as f:
            obr = json.load(f)
        print(json.dumps(montar(obr), ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
