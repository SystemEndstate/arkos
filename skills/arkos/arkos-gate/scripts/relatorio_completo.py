"""Sub-gate "relatório completo" do arkos-gate (engine/report/SCHEMA.md, regra de 2026-11-23).

Confere o JSON do relatório antes de gerar o site: os 7 papéis obrigatórios, seção genérica, frase de
"procure um especialista", origem do método (limite A) e, para plano membro, nome de skill (limite B) e
temas do plano VIP.

  python relatorio_completo.py resultado.json [--plano membro|vip] [--pacote cli/skills/pacote.json]
Saída: JSON {status: aprovado|reprovado, vermelhos: [...]}; código 0 aprovado, 1 reprovado, 3 entrada inválida.
"""
import argparse, json, re, sys
from pathlib import Path

PAPEIS = ("diagnostico", "plano", "material", "numeros", "riscos", "cronograma", "medicao")
MIN_PALAVRAS = 60
GENERICO = re.compile(r"(\ba definir\b|\bTODO\b|\blorem\b|\[preencher\]|\bTBD\b|\bxxx\b)", re.I)
TERCEIRIZA = re.compile(
    r"(procur\w* (um|uma)? ?(especialista|profissional|ag[êe]ncia|consultor)|contrat\w* (algu[ée]m|um especialista|um profissional|uma ag[êe]ncia|um consultor)"
    r"|consult\w* (um|uma) (especialista|profissional|consultor)|busque ajuda profissional)", re.I)
ORIGEM = re.compile(
    r"(youtube\.com|youtu\.be|x\.com/|twitter\.com|reddit\.com|tiktok\.com/@|instagram\.com/|hotmart|kiwify|udemy|eduzz|skool\.com"
    r"|segundo o (professor|mentor|curso)|\bno curso\b|\bna aula\b|aprendi com|\bdo mentor\b|como ensina (o|a) )", re.I)
TEMA_VIP = re.compile(
    r"(\bvsls?\b|video ?sales ?letter|advertorial|\bugc\b|tiktok ?shop|\be-?commerce\b|loja (virtual|online)|\bshopify\b|ticket m[ée]dio|\baov\b|dropship)", re.I)


def textos(no):
    """Todo texto do bloco/seção, recursivo (campos de string e listas)."""
    if isinstance(no, str):
        yield no
    elif isinstance(no, dict):
        for k, v in no.items():
            if k not in ("type", "status", "owner", "tone", "papel", "id", "lang"):
                yield from textos(v)
    elif isinstance(no, list):
        for v in no:
            yield from textos(v)


def tipos(sec):
    return [b.get("type") for b in sec.get("blocks", []) if isinstance(b, dict)]


def tem_passos(sec):
    for b in sec.get("blocks", []):
        if b.get("type") == "steps" and sum(len(f.get("steps", [])) for f in b.get("phases", [])) + len(b.get("items", [])) >= 3:
            return True
        if b.get("type") == "list" and b.get("ordered") and len(b.get("items", [])) >= 3:
            return True
    return False


def nomes_de_skill(pacote):
    try:
        return [s["nome"] for s in json.loads(Path(pacote).read_text(encoding="utf-8"))["skills"] if len(s["nome"]) >= 6 and "-" in s["nome"]]
    except (OSError, ValueError, KeyError):
        return []


def checar(rel, plano="membro", skills=()):
    vermelhos = []
    secoes = rel.get("sections") or []
    por_papel = {}
    for s in secoes:
        if s.get("papel") in PAPEIS:
            por_papel.setdefault(s["papel"], []).append(s)
    for p in PAPEIS:
        if p not in por_papel:
            vermelhos.append(f"falta a seção '{p}'")
    for p, lista in por_papel.items():
        t = " ".join(x for s in lista for x in textos(s))
        if len(t.split()) < MIN_PALAVRAS:
            vermelhos.append(f"seção '{p}' genérica: {len(t.split())} palavras (mínimo {MIN_PALAVRAS})")
        if GENERICO.search(t):
            vermelhos.append(f"seção '{p}' com marcador genérico: '{GENERICO.search(t).group(0)}'")
        if p in ("diagnostico", "numeros") and not re.search(r"\d", t):
            vermelhos.append(f"seção '{p}' sem número")
        if p == "numeros" and not any(x in ("kpis", "table") for s in lista for x in tipos(s)):
            vermelhos.append("seção 'numeros' sem kpis nem tabela")
        if p == "plano" and not any(tem_passos(s) for s in lista):
            vermelhos.append("seção 'plano' sem passo a passo (steps ou lista numerada com 3+ passos)")
        if p == "cronograma":
            for d in ("7", "30", "90"):
                if not re.search(rf"\b{d}\s*(dias|d)\b", t, re.I):
                    vermelhos.append(f"cronograma sem o marco de {d} dias")
            if not any("checklist" in tipos(s) for s in lista):
                vermelhos.append("cronograma sem checklist marcável")
    tudo = " ".join(textos(rel))
    m = TERCEIRIZA.search(tudo)
    if m:
        vermelhos.append(f"manda terceirizar: '{m.group(0)}'")
    m = ORIGEM.search(tudo)
    if m:
        vermelhos.append(f"revela origem do método (limite A): '{m.group(0)}'")
    if plano != "vip":
        achadas = sorted({n for n in skills if re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", tudo)})
        if achadas:
            vermelhos.append(f"nome técnico de skill para membro (limite B): {', '.join(achadas[:5])}")
        m = TEMA_VIP.search(tudo)
        if m:
            vermelhos.append(f"tema do plano VIP em relatório de membro: '{m.group(0)}'")
    return {"status": "reprovado" if vermelhos else "aprovado", "vermelhos": vermelhos}


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("relatorio"); ap.add_argument("--plano", default="membro", choices=["membro", "vip"])
    ap.add_argument("--pacote", default=str(Path(__file__).resolve().parents[3] / "pacote.json"))
    a = ap.parse_args(argv)
    try:
        rel = json.loads(Path(a.relatorio).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(json.dumps({"status": "reprovado", "vermelhos": [f"relatório ilegível: {e}"]}, ensure_ascii=False)); return 3
    r = checar(rel, a.plano, nomes_de_skill(a.pacote))
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r["status"] == "aprovado" else 1


if __name__ == "__main__":
    sys.exit(main())
