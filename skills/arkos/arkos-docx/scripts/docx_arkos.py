"""arkos-docx: gera e edita Word (.docx) com python-docx, na identidade ARKOS.

  gerar:  py -3 docx_arkos.py gerar spec.json --casa C --cliente X --projeto Y
  editar: py -3 docx_arkos.py editar entrada.docx [--trocar chaves.json] [--anexar spec.json] --casa C --cliente X --projeto Y
  ler:    py -3 docx_arkos.py ler arquivo.docx   (texto e tabelas em JSON, para revisar antes de editar)

spec.json: {"titulo": str, "subtitulo"?: str, "tipo"?: "Proposta", "blocos": [
   {"h": "Seção"} | {"h2": "Subseção"} | {"p": "texto"} | {"lista": [..], "numerada"?: bool}
   | {"tabela": {"colunas": [..], "linhas": [[..]]}} | {"nota": "texto", "rotulo"?: "Estimativa"} | {"quebra": true}]}
"""
import argparse
import re
import json
import os
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arkos_casa as C  # noqa: E402


def rgb(h):
    return RGBColor.from_string(h)


def _fonte(run, tam=None, cor=C.INK, negrito=None, mono=False):
    run.font.name = C.FONTE_MONO if mono else C.FONTE
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), run.font.name)
    if tam:
        run.font.size = Pt(tam)
    run.font.color.rgb = rgb(cor)
    if negrito is not None:
        run.font.bold = negrito


def _sombra(celula, hexcor):
    tcPr = celula._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcor)
    tcPr.append(shd)


def _campo_pagina(par):
    partes = [("fldChar", "begin"), ("instrText", "PAGE"), ("fldChar", "end")]
    for tag, val in partes:
        r = par.add_run()
        el = OxmlElement(f"w:{tag}")
        if tag == "fldChar":
            el.set(qn("w:fldCharType"), val)
        else:
            el.set(qn("xml:space"), "preserve")
            el.text = val
        r._element.append(el)
        _fonte(r, 8, C.STEEL, mono=True)


def preparar(doc, spec, cliente):
    st = doc.styles["Normal"]
    st.font.name = C.FONTE
    st.font.size = Pt(10.5)
    st.font.color.rgb = rgb(C.INK)
    st.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), C.FONTE)
    st.paragraph_format.space_after = Pt(6)
    st.paragraph_format.line_spacing = 1.25
    for nome, tam in (("Heading 1", 18), ("Heading 2", 13)):
        h = doc.styles[nome]
        h.font.name = C.FONTE
        h.font.size = Pt(tam)
        h.font.bold = False
        h.font.color.rgb = rgb(C.INK)
        h.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), C.FONTE)
        h.paragraph_format.space_before = Pt(18 if tam > 15 else 12)
        h.paragraph_format.space_after = Pt(6)
    s = doc.sections[0]
    s.top_margin = s.bottom_margin = Cm(2.2)
    s.left_margin = s.right_margin = Cm(2.3)
    r = s.header.paragraphs[0].add_run(f"ARKOS ENGINE  ·  {cliente.upper()}")
    _fonte(r, 7.5, C.STEEL, mono=True)
    rod = s.footer.paragraphs[0]
    r = rod.add_run(f"{spec.get('tipo', 'Documento')} · {C.hoje()} · página ")
    _fonte(r, 8, C.STEEL, mono=True)
    _campo_pagina(rod)
    cp = doc.core_properties
    cp.title = spec["titulo"]
    cp.author = C.AUTOR
    cp.subject = spec.get("tipo", "Documento")
    cp.comments = f"Cliente: {cliente}"


def capa(doc, spec):
    r = doc.add_paragraph().add_run((spec.get("tipo") or "Documento").upper())
    _fonte(r, 8, C.STEEL, mono=True)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    _fonte(p.add_run(spec["titulo"]), 26, C.INK, negrito=False)
    if spec.get("subtitulo"):
        _fonte(doc.add_paragraph().add_run(spec["subtitulo"]), 12, C.STEEL)
    # régua grafite: Volt não vai em papel claro
    pPr = doc.add_paragraph()._element.get_or_add_pPr()
    borda = OxmlElement("w:pBdr")
    baixo = OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", "8"), ("space", "1"), ("color", C.GRAPHITE)):
        baixo.set(qn(f"w:{k}"), v)
    borda.append(baixo)
    pPr.append(borda)


def blocos(doc, lista):
    for b in lista:
        if "h" in b:
            doc.add_heading(b["h"], level=1)
        elif "h2" in b:
            doc.add_heading(b["h2"], level=2)
        elif "p" in b:
            doc.add_paragraph(b["p"])
        elif "lista" in b:
            for item in b["lista"]:
                doc.add_paragraph(item, style="List Number" if b.get("numerada") else "List Bullet")
        elif "tabela" in b:
            cols = b["tabela"]["colunas"]
            tab = doc.add_table(rows=1, cols=len(cols))
            tab.style = "Table Grid"
            tab.alignment = WD_TABLE_ALIGNMENT.CENTER
            for i, c in enumerate(cols):
                cel = tab.rows[0].cells[i]
                cel.text = ""
                _fonte(cel.paragraphs[0].add_run(str(c).upper()), 7.5, "FFFFFF", mono=True)
                _sombra(cel, C.INK)
            for linha in b["tabela"]["linhas"]:
                cels = tab.add_row().cells
                for i, v in enumerate(linha):
                    cels[i].text = str(v)
            doc.add_paragraph()
        elif "nota" in b:
            cel = doc.add_table(rows=1, cols=1).rows[0].cells[0]
            _sombra(cel, C.PAPER)
            cel.text = ""
            p = cel.paragraphs[0]
            _fonte(p.add_run((b.get("rotulo") or "Nota").upper() + "   "), 7.5, C.STEEL, mono=True)
            _fonte(p.add_run(b["nota"]), 10.5, C.INK)
            doc.add_paragraph()
        elif b.get("quebra"):
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def gerar(a):
    spec = C.carregar_spec(a.spec)
    C.exigir(spec, ["titulo", "blocos"])
    if getattr(a, "trocar", None):
        spec = C.aplicar_chaves(spec, C.carregar_spec(a.trocar))
    falta = C.pendentes(spec)
    pasta = C.pasta_casa(a.casa, a.cliente, a.projeto, "documentos")
    doc = Document()
    preparar(doc, spec, a.cliente)
    capa(doc, spec)
    blocos(doc, spec["blocos"])
    alvo = C.caminho_novo(pasta, spec["titulo"], "docx")
    doc.save(alvo)
    C.saida("amarelo" if falta else "ok", arquivo=alvo, blocos=len(spec["blocos"]), nao_trocadas=falta)


def _paragrafos(doc):
    yield from doc.paragraphs
    for t in doc.tables:
        for row in t.rows:
            for cel in row.cells:
                yield from cel.paragraphs
    for s in doc.sections:
        yield from s.header.paragraphs
        yield from s.footer.paragraphs


def _trocar(par, chaves):
    texto = "".join(r.text for r in par.runs)
    n = 0
    for k, v in chaves.items():
        alvo = "{{" + k + "}}"
        if alvo in texto:
            n += texto.count(alvo)
            texto = texto.replace(alvo, str(v))
    if n:  # placeholder pode estar partido em vários runs: guarda a formatação do 1º
        for i, r in enumerate(par.runs):
            r.text = texto if i == 0 else ""
    return n


def editar(a):
    if not os.path.isfile(a.entrada):
        C.saida("aguardando", excecao="entrada_incompleta", falta=[a.entrada])
        sys.exit(C.ENTRADA_INCOMPLETA)
    doc = Document(a.entrada)
    trocas, restantes = 0, []
    if a.trocar:
        chaves = C.carregar_spec(a.trocar)
        trocas = sum(_trocar(p, chaves) for p in _paragrafos(doc))
        restantes = sorted({k for p in _paragrafos(doc) for k in chaves if "{{" + k + "}}" in p.text})
    if a.anexar:
        blocos(doc, C.carregar_spec(a.anexar).get("blocos", []))
    pasta = C.pasta_casa(a.casa, a.cliente, a.projeto, "documentos")
    base = C.base_sem_data(a.entrada)
    alvo = C.caminho_novo(pasta, base + "-editado", "docx")
    doc.save(alvo)  # o original nunca é sobrescrito
    C.saida("ok", arquivo=alvo, trocas=trocas, nao_trocadas=restantes)


def ler(a):
    doc = Document(a.arquivo)
    out = {"titulo": doc.core_properties.title, "autor": doc.core_properties.author,
           "paragrafos": [p.text for p in doc.paragraphs if p.text.strip()],
           "tabelas": [[[c.text for c in r.cells] for r in t.rows] for t in doc.tables]}
    print(json.dumps(out, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gerar")
    g.add_argument("spec")
    g.add_argument("--trocar")
    e = sub.add_parser("editar")
    e.add_argument("entrada")
    e.add_argument("--trocar")
    e.add_argument("--anexar")
    for p in (g, e):
        p.add_argument("--casa")
        p.add_argument("--cliente")
        p.add_argument("--projeto")
    r = sub.add_parser("ler")
    r.add_argument("arquivo")
    a = ap.parse_args()
    {"gerar": gerar, "editar": editar, "ler": ler}[a.cmd](a)


if __name__ == "__main__":
    main()
