#!/usr/bin/env python3
"""arkos-impacto: antecipa bugs de impacto antes de codar. Somente stdlib.

radar: mede o raio de impacto (quem referencia os simbolos tocados) e casa a
mudanca com padroes de bug de impacto, devolvendo cenarios + checklist de prova.
"""
import argparse
import json
import os
import re
import sys

# padroes de bug de impacto: (categoria, gatilhos, como provar)
PADROES = [
    ("estado_compartilhado", ["global", "singleton", "cache", "estado", "config", "sessao"],
     "dois chamadores concorrentes; o 2o nao deve ver o estado do 1o"),
    ("migracao_schema", ["migration", "migracao", "schema", "coluna", "tabela", "alter", "drop"],
     "rodar a migracao e o rollback; dados antigos continuam legiveis"),
    ("forma_api", ["api", "contrato", "endpoint", "payload", "resposta", "json", "campo"],
     "cliente antigo com a resposta nova; campo removido/renomeado quebra?"),
    ("concorrencia", ["async", "thread", "paralelo", "fila", "lock", "concorr", "race"],
     "disparar N em paralelo; sem duplicar efeito nem perder item"),
    ("nulo_vazio", ["opcional", "null", "none", "vazio", "lista", "default", "faltando"],
     "entrada vazia/None/lista de 0 e 1 item nao quebra a tela"),
    ("encoding_i18n", ["acento", "utf", "encoding", "idioma", "locale", "emoji", "nome"],
     "nome com acento/emoji e texto longo renderizam sem vazar"),
    ("limite_overflow", ["limite", "pagina", "overflow", "grande", "max", "timeout", "lote"],
     "volume no teto (muitos itens, numero enorme) sem estourar"),
    ("retrocompat", ["versao", "release", "deploy", "compat", "legado", "breaking"],
     "versao anterior do cliente/estado continua funcionando apos subir"),
]

PULAR = {".git", "node_modules", "graphify-out", "__pycache__", ".arkos", "dist", "build"}
EXTS = {".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".go", ".vue", ".sql", ".json"}


def raio_de_impacto(repo, simbolos):
    """Quem referencia cada simbolo. Devolve dict simbolo -> [arquivos]."""
    out = {s: [] for s in simbolos if s}
    if not repo or not os.path.isdir(repo):
        return out
    regexes = {s: re.compile(r"\b" + re.escape(s) + r"\b") for s in out}
    for raiz, dirs, arqs in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in PULAR]
        for a in arqs:
            if os.path.splitext(a)[1].lower() not in EXTS:
                continue
            caminho = os.path.join(raiz, a)
            try:
                with open(caminho, encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
            except OSError:
                continue
            rel = os.path.relpath(caminho, repo)
            for s, rx in regexes.items():
                if rx.search(txt):
                    out[s].append(rel)
    return out


def cenarios(descricao):
    t = (descricao or "").lower()
    achados = []
    for categoria, gatilhos, como in PADROES:
        if any(g in t for g in gatilhos):
            achados.append({"categoria": categoria, "risco": "alto", "como_provar": como})
    # sempre inclui nulo_vazio como piso minimo se nada casou
    if not achados:
        c = next(p for p in PADROES if p[0] == "nulo_vazio")
        achados.append({"categoria": c[0], "risco": "medio", "como_provar": c[2]})
    return achados


def radar(descricao, simbolos, arquivos, repo):
    raio = raio_de_impacto(repo, simbolos)
    cen = cenarios(descricao)
    contrato = list(simbolos) + list(arquivos)
    checklist = [f"provar '{c['categoria']}': {c['como_provar']}" for c in cen if c["risco"] == "alto"]
    if not checklist:
        checklist = [f"provar '{cen[0]['categoria']}': {cen[0]['como_provar']}"]
    medido = bool(repo and os.path.isdir(repo))
    return {
        "raio_de_impacto": raio,
        "raio_medido": medido,
        "contrato": contrato,
        "cenarios": cen,
        "checklist": checklist,
    }


def _lista(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="impacto")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("radar")
    r.add_argument("--descricao", default="")
    r.add_argument("--simbolos", default="")
    r.add_argument("--arquivos", default="")
    r.add_argument("--repo", default="")
    args = ap.parse_args(argv)
    if args.cmd == "radar":
        res = radar(args.descricao, _lista(args.simbolos), _lista(args.arquivos),
                    args.repo or None)
        print(json.dumps(res, ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
