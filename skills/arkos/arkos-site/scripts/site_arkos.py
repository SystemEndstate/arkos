"""arkos-site: abre, confere e fecha uma landing de alto nível dentro da pasta-casa, usando as skills
distribuíveis design-taste-frontend (taste-skill, com o gate) e impeccable.

  novo:    py -3 site_arkos.py novo brief.json --casa C --cliente X --projeto Y
           cria workspace/<cliente>/<projeto>/site/ com o kit da taste-skill, o starter, o brief.md e o gate armado
  status:  py -3 site_arkos.py status <pasta-do-site>
           roda o gate da taste-skill (oculto) e devolve PASS/FAIL com a contagem; não mexe em nada
  pronto:  py -3 site_arkos.py pronto <pasta-do-site>
           critério de pronto: gate PASS (ou FAIL só com waivers registrados), sem placeholder no HTML,
           CTA principal presente, título e description preenchidos

brief.json: {"negocio": str, "tipo": "software|product|service|place", "o_que_vende": str, "publico": str,
             "acao_principal": str, "fatos": [str], "contato"?: str, "material"?: [caminhos]}
"""
import argparse
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arkos_casa as C  # noqa: E402

TIPOS = {"software": "software", "product": "product", "service": "service", "place": "place"}


def _taste():
    """Ordem: ARKOS_TASTE; pasta irmã (mesma pasta de skills desta); CLAUDE_CONFIG_DIR/skills; ~/.claude/skills."""
    irma = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "design-taste-frontend")
    config = os.environ.get("CLAUDE_CONFIG_DIR", "")
    cands = [os.environ.get("ARKOS_TASTE", ""), irma,
             os.path.join(config, "skills", "design-taste-frontend") if config else "",
             os.path.join(os.path.expanduser("~"), ".claude", "skills", "design-taste-frontend")]
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "scripts", "gate.mjs")):
            return c
    return None


def _node():
    return shutil.which("node")


def _sem_ferramenta():
    falta = [n for n, ok in (("design-taste-frontend (taste-skill)", _taste()), ("node 22+", _node())) if not ok]
    if falta:
        C.saida("bloqueada", excecao="fora_do_ar", motivo="falta " + ", ".join(falta),
                como_resolver="instale a taste-skill na mesma pasta de skills desta (CLAUDE_CONFIG_DIR/skills ou ~/.claude/skills), ou aponte ARKOS_TASTE; e o Node 22+")
        sys.exit(C.FORA_DO_AR)


def novo(a):
    brief = C.carregar_spec(a.brief)
    C.exigir(brief, ["negocio", "tipo", "o_que_vende", "publico", "acao_principal", "fatos"])
    if brief["tipo"] not in TIPOS:
        C.saida("aguardando", excecao="entrada_incompleta", falta=[f"tipo '{brief['tipo']}' (use {', '.join(TIPOS)})"])
        sys.exit(C.ENTRADA_INCOMPLETA)
    _sem_ferramenta()
    taste = _taste()
    pasta = C.pasta_casa(a.casa, a.cliente, a.projeto, "site")
    if os.path.isfile(os.path.join(pasta, "index.html")):
        C.saida("aguardando", excecao="entrada_incompleta",
                falta=[f"já existe um site em {pasta}; use outro --projeto ou continue esse com 'status'"])
        sys.exit(C.ENTRADA_INCOMPLETA)
    shutil.copytree(os.path.join(taste, "assets"), os.path.join(pasta, "assets"), dirs_exist_ok=True)
    shutil.copyfile(os.path.join(taste, "assets", "starter.html"), os.path.join(pasta, "index.html"))
    linhas = [f"# Brief · {brief['negocio']}", "",
              f"- **Tipo (taste-skill):** {brief['tipo']}",
              f"- **O que vende:** {brief['o_que_vende']}",
              f"- **Para quem:** {brief['publico']}",
              f"- **Ação principal (um CTA):** {brief['acao_principal']}",
              f"- **Contato:** {brief.get('contato') or 'a confirmar (nunca inventar telefone; .example até confirmar)'}", "",
              "## Fatos (só estes entram na página; nada inventado)", ""] + [f"- {f}" for f in brief["fatos"]]
    if brief.get("material"):
        linhas += ["", "## Material do cliente", ""] + [f"- {m}" for m in brief["material"]]
    linhas += ["", "## Ordem de trabalho", "",
               "1. design-taste-frontend: copy primeiro, plano por telas, deal, build (o gate já está armado aqui).",
               "2. impeccable: critique e audit; corrigir P0/P1.",
               "3. Emil (animate, mobile-native): entrada do hero, hover, toque; nada de pausa em decoração.",
               "4. `site_arkos.py pronto .` até verde; depois arkos-site-gratis para publicar."]
    with open(os.path.join(pasta, "brief.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    r = C.rodar_oculto([_node(), os.path.join(taste, "scripts", "gate.mjs"), "--start", "index.html",
                        "--kind", brief["tipo"], "--category", brief["o_que_vende"], "--primary", brief["acao_principal"]],
                       timeout=120, cwd=pasta)
    armado = any(os.path.isfile(os.path.join(pasta, ".taste-skill", f)) for f in ("build.json", "gate.json"))
    C.saida("ok" if armado else "amarelo", pasta=pasta, gate_armado=armado, taste=taste,
            log=(r.stdout + r.stderr)[-300:] if not armado else "")


def _rodar_gate(pasta):
    _sem_ferramenta()
    r = C.rodar_oculto([_node(), os.path.join(_taste(), "scripts", "gate.mjs"), "index.html"], timeout=900, cwd=pasta)
    out = r.stdout + r.stderr
    m = re.search(r"GATE:\s*(\w+)\s*(\d+)?", out)
    with open(os.path.join(pasta, ".taste-skill", "gate-ultimo.txt"), "w", encoding="utf-8") as f:
        f.write(out)
    return (m.group(1) if m else "ERRO"), int(m.group(2) or 0) if m else -1, out


def status(a):
    estado, n, _ = _rodar_gate(a.pasta)
    C.saida("ok" if estado == "PASS" else "reprovado", gate=estado, fails=n,
            detalhe=os.path.join(a.pasta, ".taste-skill", "gate-ultimo.txt"))


def _checar_html(pasta):
    probs = []
    caminho = os.path.join(pasta, "index.html")
    if not os.path.isfile(caminho):
        return ["index.html não existe"]
    h = open(caminho, encoding="utf-8").read()
    if re.search(r"\{\{[^}]+\}\}|lorem ipsum|TODO|PLACEHOLDER", h, re.I):
        probs.append("placeholder no HTML ({{..}}, lorem, TODO)")
    if not re.search(r"<title>[^<]{4,}</title>", h):
        probs.append("<title> vazio")
    if not re.search(r'<meta name="description" content="[^"]{20,}"', h):
        probs.append("meta description vazia ou curta")
    brief = os.path.join(pasta, "brief.md")
    if os.path.isfile(brief):
        acao = re.search(r"\*\*Ação principal \(um CTA\):\*\* (.+)", open(brief, encoding="utf-8").read())
        if acao and acao.group(1).strip().lower() not in h.lower():
            probs.append(f"CTA principal '{acao.group(1).strip()}' não aparece na página")
    return probs


def pronto(a):
    probs = _checar_html(a.pasta)
    estado, n, _ = _rodar_gate(a.pasta)
    waivers = os.path.join(a.pasta, ".taste-skill", "waivers.json")
    nw = len(json.load(open(waivers, encoding="utf-8"))) if os.path.isfile(waivers) else 0
    if estado != "PASS":
        probs.append(f"gate da taste-skill {estado} {n} (waivers registrados: {nw})")
    C.saida("verde" if not probs else "vermelho", gate=estado, fails=n, waivers=nw, problemas=probs)
    sys.exit(0 if not probs else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("novo")
    n.add_argument("brief")
    n.add_argument("--casa")
    n.add_argument("--cliente")
    n.add_argument("--projeto")
    sub.add_parser("status").add_argument("pasta")
    sub.add_parser("pronto").add_argument("pasta")
    a = ap.parse_args()
    {"novo": novo, "status": status, "pronto": pronto}[a.cmd](a)


if __name__ == "__main__":
    main()
