#!/usr/bin/env python3
"""arkos-prospeccao-local: processa negocios locais de fonte PERMITIDA. Stdlib.

Sala limpa (substitui o sellbird AGPL). Nao raspa aqui: recebe dados de fonte
permitida, normaliza, deduplica e marca que numero publico NAO autoriza contato.
"""
import argparse
import json
import re
import sys

AVISO = ("Numero publico nao autoriza contato. Contato so apos opt-in, por "
         "template, pela Cloud API (regra da casa). Envio passa pelo arkos-guarda-envio.")


def so_digitos(s):
    return re.sub(r"\D", "", s or "")


def normalizar(reg):
    tel = so_digitos(reg.get("telefone", ""))
    nome = (reg.get("nome", "") or "").strip()
    incompleto = not (tel and (reg.get("endereco") or "").strip())
    return {
        "nome": nome,
        "categoria": (reg.get("categoria", "") or "").strip(),
        "telefone": tel,
        "endereco": (reg.get("endereco", "") or "").strip(),
        "site": (reg.get("site", "") or "").strip(),
        "contato_autorizado": False,
        "status": "incompleto" if incompleto else "ok",
    }


def processar(fonte, fonte_permitida, registros):
    if not fonte_permitida:
        return {"ok": False, "acao": "recusar",
                "motivo": "fonte nao marcada como permitida (termos de uso)",
                "leads": []}
    leads, vistos, dup = [], set(), 0
    for r in registros:
        n = normalizar(r)
        chave = (n["nome"].lower(), n["telefone"])
        if chave in vistos:
            dup += 1
            continue
        vistos.add(chave)
        leads.append(n)
    return {"ok": True, "fonte": fonte, "permitida": True, "leads": leads,
            "descartados_dup": dup, "aviso": AVISO}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="prospeccao")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("processar")
    p.add_argument("--arquivo", required=True, help="JSON [{nome,telefone,...}]")
    p.add_argument("--fonte", default="desconhecida")
    p.add_argument("--fonte-permitida", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "processar":
        with open(args.arquivo, encoding="utf-8") as f:
            regs = json.load(f)
        res = processar(args.fonte, args.fonte_permitida, regs)
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res["ok"] else 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
