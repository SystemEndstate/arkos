"""arkos-sop: cria e valida SOPs (procedimento operacional padrão) + checklist no formato da ARKOS.

Uso:
  python sop.py novo     --casa C --projeto P --titulo "Subir campanha Meta" --dono ana --gatilho "cliente aprovou criativos"
                         --passos "a;b;c" --pronto "x;y" [--excecoes "se X: Y"] [--ferramentas "Meta Ads"]
  python sop.py validar  --arquivo sop.md
  python sop.py checklist --arquivo sop.md          (gera checklist-<slug>.md ao lado)

SOP de operação fica em <casa>/workspace/_operacao/<projeto>/sop-<slug>.md; de cliente, em workspace/<cliente>/<projeto>/.
Saída: 0 ok · 2 recusa · 3 exceção tratada (SOP incompleto: lista o que falta).
"""
import argparse, json, re, sys, unicodedata
from datetime import date
from pathlib import Path

OBRIGATORIAS = ("Objetivo", "Dono", "Gatilho", "Passos", "Pronto quando", "Exceções")
SEGREDO = re.compile(r"(senha|password|token|api[_-]?key|secret)\s*[:=]\s*\S+|EAA[A-Za-z0-9]{20,}|sk_(live|test)_\w+", re.I)
VAGO = re.compile(r"\b(etc|e assim por diante|conforme necessário|quando der|se possível)\b", re.I)


def slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60]


def partes(s):
    return [x.strip() for x in (s or "").split(";") if x.strip()]


def novo(casa, projeto, titulo, dono, gatilho, passos, pronto, excecoes=None, ferramentas=None, objetivo=None, hoje=None):
    if SEGREDO.search(" ".join(filter(None, (titulo, gatilho, passos, pronto, excecoes, ferramentas, objetivo)))):
        return 2, {"recusado": "SOP não leva senha nem token; escreva 'pegar no cofre do cliente'"}
    falta = [n for n, v in (("dono", dono), ("gatilho", gatilho), ("passos", passos), ("pronto", pronto)) if not v]
    if falta:
        return 3, {"excecao": "entrada_incompleta", "pergunta": f"falta: {', '.join(falta)}"}
    ps = partes(passos)
    L = [f"# SOP · {titulo}", "", f"_versão 1 · {hoje or date.today().isoformat()}_", "",
         "## Objetivo", "", objetivo or f"Executar \"{titulo}\" sempre do mesmo jeito, por qualquer prestador.", "",
         "## Dono", "", dono, "", "## Gatilho", "", gatilho, ""]
    if ferramentas:
        L += ["## Ferramentas", ""] + [f"- {f}" for f in partes(ferramentas)] + [""]
    L += ["## Passos", ""] + [f"{i}. {p}" for i, p in enumerate(ps, 1)] + [""]
    L += ["## Pronto quando", ""] + [f"- {p}" for p in partes(pronto)] + [""]
    L += ["## Exceções", ""] + ([f"- {e}" for e in partes(excecoes)] or ["- Travou ou fugiu do padrão: parar e avisar o dono com o que já foi feito."]) + [""]
    pasta = Path(casa) / "workspace" / "_operacao" / slug(projeto)
    pasta.mkdir(parents=True, exist_ok=True)
    f = pasta / f"sop-{slug(titulo)}.md"
    f.write_text("\n".join(L), encoding="utf-8")
    ok, prob = validar_texto(f.read_text(encoding="utf-8"))
    return (0 if ok else 3), {"arquivo": str(f), "problemas": prob}


def secoes(t):
    out, atual = {}, None
    for linha in t.splitlines():
        m = re.match(r"^##\s+(.+)", linha)
        if m:
            atual = m.group(1).strip(); out[atual] = []
        elif atual:
            out[atual].append(linha)
    return out


def validar_texto(t):
    s = secoes(t)
    prob = [f"falta a seção '{n}'" for n in OBRIGATORIAS if n not in s or not "".join(s[n]).strip()]
    passos = [l for l in s.get("Passos", []) if re.match(r"^\d+\.\s+\S", l)]
    if "Passos" in s and len(passos) < 2:
        prob.append("Passos precisa de pelo menos 2 passos numerados")
    longos = [p for p in passos if len(p) > 220]
    if longos:
        prob.append(f"{len(longos)} passo(s) com mais de 220 caracteres: quebrar em passos menores")
    vagos = [l.strip() for l in passos if VAGO.search(l)]
    if vagos:
        prob.append(f"passo vago (sem critério): {vagos[0]}")
    if SEGREDO.search(t):
        prob.append("contém algo com cara de senha/token")
    return not prob, prob


def checklist(arq):
    t = Path(arq).read_text(encoding="utf-8")
    s = secoes(t)
    titulo = (re.search(r"^# SOP · (.+)", t, re.M) or [None, Path(arq).stem])[1]
    L = [f"# Checklist · {titulo}", ""] + ["- [ ] " + re.sub(r"^\d+\.\s+", "", p) for p in s.get("Passos", []) if re.match(r"^\d+\.", p)]
    L += ["", "**Pronto quando:**", ""] + [f"- [ ] {p[2:]}" for p in s.get("Pronto quando", []) if p.startswith("- ")]
    f = Path(arq).with_name(Path(arq).name.replace("sop-", "checklist-", 1))
    f.write_text("\n".join(L) + "\n", encoding="utf-8")
    return f


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["novo", "validar", "checklist"])
    for o in ("--casa", "--projeto", "--titulo", "--dono", "--gatilho", "--passos", "--pronto", "--excecoes", "--ferramentas", "--objetivo", "--arquivo"):
        ap.add_argument(o)
    a = ap.parse_args(argv)
    if a.cmd == "novo":
        code, r = novo(a.casa, a.projeto, a.titulo, a.dono, a.gatilho, a.passos, a.pronto, a.excecoes, a.ferramentas, a.objetivo)
    elif a.cmd == "validar":
        ok, prob = validar_texto(Path(a.arquivo).read_text(encoding="utf-8")); code, r = (0 if ok else 3), {"ok": ok, "problemas": prob}
    else:
        code, r = 0, {"checklist": str(checklist(a.arquivo))}
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
