#!/usr/bin/env python3
"""arkos-roteador: roteia o pedido para skills do PROPRIO pacote.

Sala limpa: nao usa qual-skill/catalogo pessoal nem jev. Pontua por palavra-chave
no catalogo.json do pacote e desempata pelo arkos-decisor (quando instalado);
sem desempate, pergunta ao usuario. Somente stdlib.
"""
import argparse
import json
import os
import re
import sys
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
CATALOGO_PADRAO = os.path.join(AQUI, "catalogo.json")
TRAVA_ESCRITA = "arkos-guarda-escrita"
TRAVA_ENVIO = "arkos-guarda-envio"
PERTO = 0.05


def carregar_catalogo(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)["skills"]


def _norm(t):
    # tira acento (NFKD) antes de comparar: "orcamento" casa com "orcamento"
    base = unicodedata.normalize("NFKD", (t or "").lower())
    base = "".join(c for c in base if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9\s]", " ", base)


def catalogo_de_playbooks(playbooks):
    """Gera o catalogo a partir de playbooks.json (gatilhos + skills[]), para o
    roteador nao divergir do terminal. `playbooks`: lista de dicts do cli/data."""
    skills = {}
    for pb in playbooks:
        gatilhos = pb.get("gatilhos", [])
        modulos = pb.get("modulos", []) or ([pb["modulo"]] if pb.get("modulo") else [])
        for sk in pb.get("skills", []) or [e.get("skill") for e in pb.get("etapas", [])]:
            if not sk:
                continue
            ent = skills.setdefault(sk, {"skill": sk, "categoria": pb.get("categoria", ""),
                                         "modulos": [], "palavras": set(),
                                         "escreve": False, "envia": False})
            ent["modulos"] = sorted(set(ent["modulos"]) | set(modulos))
            ent["palavras"] |= set(gatilhos)
    for ent in skills.values():
        ent["palavras"] = sorted(ent["palavras"])
    return list(skills.values())


def pontuar(pedido, entry):
    texto = _norm(pedido)
    palavras = entry.get("palavras", [])
    if not palavras:
        return 0.0
    achou = sum(1 for p in palavras if _norm(p) in texto)
    return achou / len(palavras)


def travas_de(entry):
    t = []
    if entry.get("escreve"):
        t.append(TRAVA_ESCRITA)
    if entry.get("envia"):
        t.append(TRAVA_ENVIO)
    return t


def rotear(pedido, catalogo, desempatar=None):
    """desempatar(scores, opcoes) -> dict do arkos-decisor (opcional)."""
    ranking = sorted(
        ((pontuar(pedido, e), e) for e in catalogo),
        key=lambda x: x[0], reverse=True,
    )
    top1_s, top1 = ranking[0]
    top2_s = ranking[1][0] if len(ranking) > 1 else 0.0

    if top1_s == 0:
        sugest = [e["skill"] for _, e in ranking[:2]]
        return {"perguntar": True, "motivo": "nenhum gatilho bateu", "top": sugest,
                "skills": [], "travas": []}

    if (top1_s - top2_s) < PERTO and len(ranking) > 1 and top2_s > 0:
        opcoes = [top1["skill"], ranking[1][1]["skill"]]
        if desempatar is not None:
            scores = {top1["skill"]: top1_s, ranking[1][1]["skill"]: top2_s}
            d = desempatar(scores, opcoes)
            if not d.get("decidir_com_claude") and d.get("escolha"):
                esc = next(e for _, e in ranking if e["skill"] == d["escolha"])
                return _montar(esc, "desempate arkos-decisor")
        return {"perguntar": True, "motivo": "empate", "top": opcoes,
                "skills": [], "travas": []}

    return _montar(top1, f"gatilho {round(top1_s, 2)}")


def _montar(entry, motivo):
    return {"perguntar": False, "skills": [entry["skill"]],
            "travas": travas_de(entry), "categoria": entry.get("categoria"),
            "modulos": entry.get("modulos", []), "motivo": motivo}


def _dirs_decisor():
    """Onde procurar o arkos-decisor, em ordem: pasta irma desta skill, depois
    CLAUDE_CONFIG_DIR/skills, depois ~/.claude/skills. Perfil com CLAUDE_CONFIG_DIR
    nao pode perder o desempate em silencio (padrao do arkos-site)."""
    cands = []
    irma = os.path.join(os.path.dirname(os.path.dirname(AQUI)), "arkos-decisor", "scripts")
    cands.append(irma)
    cfg = os.environ.get("CLAUDE_CONFIG_DIR")
    if cfg:
        cands.append(os.path.join(cfg, "skills", "arkos-decisor", "scripts"))
    cands.append(os.path.expanduser("~/.claude/skills/arkos-decisor/scripts"))
    return cands


def _carregar_desempatador():
    """Liga o arkos-decisor como Sistema 1 do desempate, se estiver instalado."""
    cand = next((d for d in _dirs_decisor() if os.path.isdir(d)), None)
    if not cand:
        return None
    sys.path.insert(0, cand)
    try:
        import decisor  # noqa: PLC0415
    except ImportError:
        return None

    def desempatar(scores, opcoes):
        return decisor.decidir("Qual skill resolve este pedido?", opcoes, "",
                               limiar=0.6, scores=scores)
    return desempatar


def main(argv=None):
    ap = argparse.ArgumentParser(prog="roteador")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rotear")
    r.add_argument("--pedido", required=True)
    r.add_argument("--catalogo", default=CATALOGO_PADRAO)
    r.add_argument("--sem-decisor", action="store_true", help="nao usar arkos-decisor no desempate")
    g = sub.add_parser("gerar-catalogo")
    g.add_argument("--playbooks", required=True)
    g.add_argument("--saida", default=CATALOGO_PADRAO)
    args = ap.parse_args(argv)

    if args.cmd == "rotear":
        if not os.path.exists(args.catalogo):
            print(json.dumps({"erro": "catalogo ausente", "acao": "arkos-atualizar"},
                             ensure_ascii=False))
            return 2
        cat = carregar_catalogo(args.catalogo)
        desemp = None if args.sem_decisor else _carregar_desempatador()
        print(json.dumps(rotear(args.pedido, cat, desempatar=desemp), ensure_ascii=False))
        return 0
    if args.cmd == "gerar-catalogo":
        with open(args.playbooks, encoding="utf-8") as f:
            pbs = json.load(f)
        skills = catalogo_de_playbooks(pbs if isinstance(pbs, list) else pbs.get("playbooks", []))
        with open(args.saida, "w", encoding="utf-8") as f:
            json.dump({"gerado": "de playbooks.json", "skills": skills}, f, ensure_ascii=False, indent=1)
        print(json.dumps({"ok": True, "skills": len(skills), "saida": args.saida}, ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
