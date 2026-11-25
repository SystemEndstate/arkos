"""arkos-gate-rag: portão de qualidade de pesquisa e de resposta com RAG. Confere se cada afirmação tem
fonte, se a confiança foi marcada e se a afirmação crítica (com número) foi triangulada.

  checar relatorio.md|ledger.json [--casa C --cliente X --projeto Y]   -> verde (0) | vermelho (1) | entrada_incompleta (2)

Formato do relatório em Markdown (o SKILL.md explica):
  - cada item de lista ou parágrafo fora de Fontes/Lacunas/Método/Perguntas é uma AFIRMAÇÃO;
  - a afirmação termina com as fontes [1] ou [1, 3] e a confiança {alta} {média} {baixa};
  - "Lacuna:" e "Opinião:" no começo dispensam fonte (mas opinião não pode trazer número);
  - seção "## Fontes" com linhas "[n] título — URL (acesso AAAA-MM-DD)".
O ledger JSON do arkos-pesquisa também é aceito: {fontes:[{url,...}], afirmacoes:[{texto,confianca,fontes:[url]}]}.
"""
import argparse
import json
import os
import re
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arkos_casa as C  # noqa: E402

FORA = re.compile(r"^(fontes?|refer[êe]ncias|lacunas?|m[ée]todo|perguntas?|como foi feito)\b", re.I)
CIT = re.compile(r"\[(\d+(?:\s*[,;]\s*\d+)*)\]")
CONF = re.compile(r"\{\s*(alta|m[ée]dia|baixa)\s*\}|\(confian[çc]a:\s*(alta|m[ée]dia|baixa)\)", re.I)
FONTE = re.compile(r"^\s*[-*]?\s*\[(\d+)\]\s*(.+)$")
URL = re.compile(r"https?://[^\s)>\]]+")
DATA = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
NUMERO = re.compile(r"(?<![A-Za-zÀ-ÿ])\d")
ISENTA = re.compile(r"^\s*(lacuna|opini[ãa]o)\s*:", re.I)


def dominio(url):
    d = urlparse(url).netloc.lower()
    return d[4:] if d.startswith("www.") else d


def _nivel(m):
    v = (m.group(1) or m.group(2)).lower()
    return "media" if v.startswith("m") else v


def ler_md(texto):
    fontes, unidades, secao, buf, ini = {}, [], "", [], 0
    linhas = texto.splitlines()

    def fecha(fim):
        if buf and not FORA.match(secao):
            unidades.append({"linha": ini, "texto": " ".join(buf).strip()})
        buf.clear()

    for i, l in enumerate(linhas, 1):
        h = re.match(r"^#{1,6}\s+(.*)", l)
        if h:
            fecha(i)
            secao = h.group(1).strip()
            continue
        if re.match(r"^\s*(fontes?|refer[êe]ncias)\s*:?\s*$", l, re.I):
            fecha(i)
            secao = "Fontes"
            continue
        if FORA.match(secao) and secao.lower().startswith(("fonte", "refer")):
            m = FONTE.match(l)
            if m:
                u = URL.search(m.group(2))
                fontes[m.group(1)] = {"texto": m.group(2), "url": u.group(0) if u else "", "linha": i,
                                      "data": bool(DATA.search(m.group(2)))}
            continue
        item = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)", l)
        if not l.strip() or l.strip().startswith(("|", ">", "```", "---")):
            fecha(i)
            continue
        if item:
            fecha(i)
            ini = i
            buf.append(item.group(1))
            fecha(i)
            continue
        if not buf:
            ini = i
        buf.append(l.strip())
    fecha(len(linhas))
    return fontes, unidades


def avaliar(fontes, unidades):
    probs, avisos, usadas = [], [], set()
    for u in unidades:
        t, ln = u["texto"], u["linha"]
        curto = (t[:70] + "…") if len(t) > 70 else t
        if ISENTA.match(t):
            if t.lower().lstrip().startswith("opini") and NUMERO.search(re.sub(CIT, "", t)):
                probs.append({"linha": ln, "regra": "opiniao_com_numero", "trecho": curto})
            continue
        ids = [x.strip() for m in CIT.finditer(t) for x in re.split(r"[,;]", m.group(1))]
        conf = CONF.search(t)
        if not ids:
            probs.append({"linha": ln, "regra": "sem_fonte", "trecho": curto})
        if not conf:
            probs.append({"linha": ln, "regra": "sem_confianca", "trecho": curto})
        doms = set()
        for i in ids:
            usadas.add(i)
            if i not in fontes:
                probs.append({"linha": ln, "regra": "fonte_inexistente", "fonte": i, "trecho": curto})
            elif fontes[i]["url"]:
                doms.add(dominio(fontes[i]["url"]))
        nivel = _nivel(conf) if conf else None
        texto_sem = CONF.sub("", CIT.sub("", t))
        if ids and NUMERO.search(texto_sem) and len(doms) < 2 and nivel != "baixa":
            probs.append({"linha": ln, "regra": "critica_sem_triangular", "dominios": sorted(doms), "trecho": curto,
                          "como_resolver": "2ª fonte de outro domínio ou confiança {baixa}"})
        if nivel == "alta" and len(doms) < 2:
            probs.append({"linha": ln, "regra": "alta_com_fonte_unica", "dominios": sorted(doms), "trecho": curto})
    for i, f in fontes.items():
        if not f["url"]:
            probs.append({"linha": f["linha"], "regra": "fonte_sem_url", "fonte": i})
        if not f["data"]:
            probs.append({"linha": f["linha"], "regra": "fonte_sem_data_de_acesso", "fonte": i})
        if i not in usadas:
            avisos.append({"linha": f["linha"], "regra": "fonte_nao_citada", "fonte": i})
    return probs, avisos


def ler_ledger(d):
    fontes, unidades, idx = {}, [], {}
    for n, f in enumerate(d.get("fontes", []), 1):
        idx[f.get("url", "")] = str(n)
        fontes[str(n)] = {"texto": f.get("afirmacao", ""), "url": f.get("url", ""), "linha": n, "data": bool(f.get("data"))}
    for n, a in enumerate(d.get("afirmacoes", []), 1):
        refs = "".join(f"[{idx[u]}]" for u in a.get("fontes", []) if u in idx)
        conf = f" {{{a['confianca']}}}" if a.get("confianca") else ""
        unidades.append({"linha": n, "texto": f"{a.get('texto', '')} {refs}{conf}"})
    return fontes, unidades


def checar(a):
    if not os.path.isfile(a.arquivo):
        C.saida("aguardando", excecao="entrada_incompleta", falta=[f"arquivo não existe: {a.arquivo}"])
        sys.exit(C.ENTRADA_INCOMPLETA)
    txt = open(a.arquivo, encoding="utf-8").read()
    if a.arquivo.lower().endswith(".json"):
        fontes, unidades = ler_ledger(json.loads(txt))
    else:
        fontes, unidades = ler_md(txt)
    falta = []
    if not fontes:
        falta.append("seção '## Fontes' com linhas '[n] título — URL (acesso AAAA-MM-DD)'")
    if not unidades:
        falta.append("nenhuma afirmação encontrada no corpo")
    if falta:
        C.saida("aguardando", excecao="entrada_incompleta", falta=falta)
        sys.exit(C.ENTRADA_INCOMPLETA)
    probs, avisos = avaliar(fontes, unidades)
    cont = {}
    for p in probs:
        cont[p["regra"]] = cont.get(p["regra"], 0) + 1
    res = {"arquivo": a.arquivo, "afirmacoes": len(unidades), "fontes": len(fontes),
           "dominios": len({dominio(f["url"]) for f in fontes.values() if f["url"]}),
           "por_regra": cont, "problemas": probs, "avisos": avisos}
    if a.casa:
        pasta = C.pasta_casa(a.casa, a.cliente, a.projeto, "pesquisa")
        alvo = C.caminho_novo(pasta, "gate-rag-" + C.base_sem_data(os.path.splitext(os.path.basename(a.arquivo))[0]), "json")
        with open(alvo, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        res["registro"] = alvo
    C.saida("verde" if not probs else "vermelho", **res)
    sys.exit(0 if not probs else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("checar")
    c.add_argument("arquivo")
    c.add_argument("--casa")
    c.add_argument("--cliente")
    c.add_argument("--projeto")
    a = ap.parse_args()
    {"checar": checar}[a.cmd](a)


if __name__ == "__main__":
    main()
