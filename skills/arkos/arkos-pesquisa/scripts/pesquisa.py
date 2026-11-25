#!/usr/bin/env python3
"""arkos-pesquisa: ledger de fontes com disciplina de triangulacao. Stdlib.

O Claude busca; este script impoe a disciplina: deduplica por dominio, exige >=2
fontes independentes por afirmacao critica, marca fragil/conflito/lacuna e gradua
confianca. Nao gera texto.
"""
import argparse
import json
import re
import sys
from urllib.parse import urlparse


def dominio(url):
    try:
        net = urlparse(url).netloc.lower()
        return re.sub(r"^www\.", "", net) or url
    except ValueError:
        return url or ""


def _fontes_independentes(fontes):
    return len({dominio(f["url"]) for f in fontes})


def montar_ledger(perguntas, fontes, afirmacoes):
    """afirmacoes: [{texto, fontes:[url], critica:bool, valor?}]."""
    # dedup de fontes por (dominio, afirmacao)
    vistos, fontes_norm = set(), []
    for f in fontes:
        chave = (dominio(f.get("url", "")), f.get("afirmacao", ""))
        if chave in vistos:
            continue
        vistos.add(chave)
        fontes_norm.append({"url": f.get("url"), "dominio": dominio(f.get("url", "")),
                            "afirmacao": f.get("afirmacao", ""), "data": f.get("data")})

    saida_afirm, fragies, conflitos, lacunas = [], [], [], []
    for a in afirmacoes:
        objs = [f for f in fontes_norm if f["url"] in set(a.get("fontes", []))]
        n_indep = _fontes_independentes(objs) if objs else 0
        critica = a.get("critica", True)
        if n_indep == 0:
            lacunas.append(a["texto"])
            conf = "lacuna"
        elif n_indep == 1:
            conf = "baixa"
            if critica:
                fragies.append(a["texto"])
        elif n_indep == 2:
            conf = "media"
        else:
            conf = "alta"
        # conflito: mesma 'chave' com valores diferentes
        if a.get("conflito"):
            conflitos.append(a["texto"])
        saida_afirm.append({"texto": a["texto"], "confianca": conf,
                            "fontes_independentes": n_indep, "critica": critica})
    return {"perguntas": perguntas, "fontes": fontes_norm, "afirmacoes": saida_afirm,
            "fragies": fragies, "conflitos": conflitos, "lacunas": lacunas}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pesquisa")
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("ledger")
    l.add_argument("--arquivo", required=True, help="JSON {perguntas,fontes,afirmacoes}")
    args = ap.parse_args(argv)
    if args.cmd == "ledger":
        with open(args.arquivo, encoding="utf-8") as f:
            d = json.load(f)
        res = montar_ledger(d.get("perguntas", []), d.get("fontes", []),
                            d.get("afirmacoes", []))
        print(json.dumps(res, ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
