"""arkos-pdf: gera, lê e transforma PDF com bibliotecas livres (reportlab, pypdf) e Chrome headless oculto.

  gerar:   py -3 pdf_arkos.py gerar spec.json      --casa C --cliente X --projeto Y   (mesmo spec do arkos-docx)
  html:    py -3 pdf_arkos.py html pagina.html     --casa C --cliente X --projeto Y [--titulo T]
  juntar:  py -3 pdf_arkos.py juntar a.pdf b.pdf   --casa C --cliente X --projeto Y --titulo T
  paginas: py -3 pdf_arkos.py paginas a.pdf --faixa 1-3,5 --casa C --cliente X --projeto Y
  carimbar:py -3 pdf_arkos.py carimbar a.pdf --texto "RASCUNHO" --casa C --cliente X --projeto Y
  ler:     py -3 pdf_arkos.py ler a.pdf            (texto por página + metadados, JSON)

Sem Chrome, `html` cai para o gerador reportlab só se houver um spec ao lado (--spec); senão sai
com a exceção fora_do_ar (código 3) e diz o que instalar. Nunca sobrescreve o arquivo de entrada.
"""
import argparse
import io
import json
import os
import sys
import tempfile

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arkos_casa as C  # noqa: E402

INK, STEEL, GRAPH, PAPER, LINE = (colors.HexColor("#" + h) for h in (C.INK, C.STEEL, C.GRAPHITE, C.PAPER, C.LINE))
SANS, SANS_B, MONO = "Helvetica", "Helvetica-Bold", "Courier"


def _registrar_fontes():
    """Usa Inter Tight / JetBrains Mono se houver .ttf estático instalado; senão Helvetica/Courier (sempre disponíveis)."""
    global SANS, SANS_B, MONO
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pastas = [os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"),
              os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"),
              "/usr/share/fonts/truetype", os.path.expanduser("~/Library/Fonts")]
    def achar(*nomes):
        for p in pastas:
            for n in nomes:
                f = os.path.join(p, n)
                if os.path.isfile(f):
                    return f
        return None
    for alias, nomes, var in (("ArkosSans", ("InterTight-Regular.ttf",), "SANS"),
                              ("ArkosSansB", ("InterTight-SemiBold.ttf", "InterTight-Bold.ttf"), "SANS_B"),
                              ("ArkosMono", ("JetBrainsMono-Regular.ttf",), "MONO")):
        f = achar(*nomes)
        if f:
            try:
                pdfmetrics.registerFont(TTFont(alias, f))
                globals()[var] = alias
            except Exception:  # fonte variável ou corrompida: fica a padrão
                pass


def _estilos():
    return {
        "kicker": ParagraphStyle("k", fontName=MONO, fontSize=8, textColor=STEEL, leading=11, spaceAfter=6),
        "titulo": ParagraphStyle("t", fontName=SANS, fontSize=26, textColor=INK, leading=30, spaceAfter=6),
        "sub": ParagraphStyle("s", fontName=SANS, fontSize=12, textColor=STEEL, leading=16, spaceAfter=14),
        "h": ParagraphStyle("h", fontName=SANS, fontSize=17, textColor=INK, leading=21, spaceBefore=16, spaceAfter=6),
        "h2": ParagraphStyle("h2", fontName=SANS_B, fontSize=12, textColor=INK, leading=16, spaceBefore=10, spaceAfter=4),
        "p": ParagraphStyle("p", fontName=SANS, fontSize=10.5, textColor=INK, leading=15, spaceAfter=6, alignment=TA_LEFT),
        "cel": ParagraphStyle("c", fontName=SANS, fontSize=9.5, textColor=INK, leading=12.5),
        "th": ParagraphStyle("th", fontName=MONO, fontSize=7.5, textColor=colors.white, leading=10),
    }


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _moldura(cliente, tipo):
    def desenhar(cv, doc):
        cv.saveState()
        cv.setFont(MONO, 7.5)
        cv.setFillColor(STEEL)
        cv.drawString(20 * mm, A4[1] - 12 * mm, f"ARKOS ENGINE  ·  {cliente.upper()}")
        cv.drawRightString(A4[0] - 20 * mm, 12 * mm, f"{tipo} · {C.hoje()} · página {doc.page}")
        cv.setStrokeColor(LINE)
        cv.line(20 * mm, A4[1] - 14 * mm, A4[0] - 20 * mm, A4[1] - 14 * mm)
        cv.restoreState()
    return desenhar


def gerar(a):
    spec = C.carregar_spec(a.spec)
    C.exigir(spec, ["titulo", "blocos"])
    if getattr(a, "trocar", None):
        spec = C.aplicar_chaves(spec, C.carregar_spec(a.trocar))
    falta = C.pendentes(spec)
    pasta = C.pasta_casa(a.casa, a.cliente, a.projeto, "documentos")
    _registrar_fontes()
    E = _estilos()
    alvo = C.caminho_novo(pasta, spec["titulo"], "pdf")
    tipo = spec.get("tipo", "Documento")
    doc = SimpleDocTemplate(alvo, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=22 * mm,
                            bottomMargin=20 * mm, title=spec["titulo"], author=C.AUTOR, subject=tipo,
                            creator="ARKOS Engine · arkos-pdf")
    h = [Paragraph(_esc(tipo.upper()), E["kicker"]), Paragraph(_esc(spec["titulo"]), E["titulo"])]
    if spec.get("subtitulo"):
        h.append(Paragraph(_esc(spec["subtitulo"]), E["sub"]))
    h.append(Table([[""]], colWidths=[170 * mm], rowHeights=[1.2], style=[("LINEBELOW", (0, 0), (-1, -1), 1, GRAPH)]))
    h.append(Spacer(1, 8))
    for b in spec["blocos"]:
        if "h" in b:
            h.append(Paragraph(_esc(b["h"]), E["h"]))
        elif "h2" in b:
            h.append(Paragraph(_esc(b["h2"]), E["h2"]))
        elif "p" in b:
            h.append(Paragraph(_esc(b["p"]), E["p"]))
        elif "lista" in b:
            itens = [ListItem(Paragraph(_esc(x), E["p"]), leftIndent=12) for x in b["lista"]]
            h.append(ListFlowable(itens, bulletType="1" if b.get("numerada") else "bullet", bulletFontName=SANS,
                                  bulletFontSize=9, leftIndent=14, bulletColor=GRAPH))
        elif "tabela" in b:
            cols = b["tabela"]["colunas"]
            dados = [[Paragraph(_esc(c).upper(), E["th"]) for c in cols]]
            dados += [[Paragraph(_esc(v), E["cel"]) for v in linha] for linha in b["tabela"]["linhas"]]
            t = Table(dados, colWidths=[170 * mm / len(cols)] * len(cols), repeatRows=1)
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), INK), ("LINEBELOW", (0, 1), (-1, -1), .5, LINE),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 6),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
            h += [t, Spacer(1, 8)]
        elif "nota" in b:
            t = Table([[Paragraph(_esc((b.get("rotulo") or "Nota").upper()), E["kicker"]), Paragraph(_esc(b["nota"]), E["p"])]],
                      colWidths=[30 * mm, 140 * mm])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PAPER), ("LINEBEFORE", (0, 0), (0, -1), 2, GRAPH),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 8)]))
            h += [t, Spacer(1, 8)]
        elif b.get("quebra"):
            h.append(PageBreak())
    moldura = _moldura(a.cliente, tipo)
    doc.build(h, onFirstPage=moldura, onLaterPages=moldura)
    C.saida("amarelo" if falta else "ok", arquivo=alvo, paginas=len(PdfReader(alvo).pages), nao_trocadas=falta)


def html(a):
    if not os.path.isfile(a.pagina):
        C.saida("aguardando", excecao="entrada_incompleta", falta=[a.pagina])
        sys.exit(C.ENTRADA_INCOMPLETA)
    pasta = C.pasta_casa(a.casa, a.cliente, a.projeto, "documentos")
    chrome = C.achar_chrome()
    if not chrome:
        if a.spec:  # alternativa do pacote: o mesmo conteúdo pelo reportlab, marcado amarelo
            a.spec_original, a.spec = a.spec, a.spec
            gerar(a)
            C.saida("amarelo", excecao="fora_do_ar", motivo="Chrome/Edge não encontrado; gerado pelo reportlab a partir do spec")
            return
        C.saida("bloqueada", excecao="fora_do_ar", motivo="Chrome/Edge não encontrado",
                como_resolver="instale o Google Chrome ou defina ARKOS_CHROME com o caminho do executável")
        sys.exit(C.FORA_DO_AR)
    alvo = C.caminho_novo(pasta, a.titulo or os.path.splitext(os.path.basename(a.pagina))[0], "pdf")
    with tempfile.TemporaryDirectory() as perfil:
        r = C.rodar_oculto([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                            f"--user-data-dir={perfil}", f"--print-to-pdf={alvo}",
                            "file:///" + os.path.abspath(a.pagina).replace("\\", "/")], timeout=120)
    if not os.path.isfile(alvo):
        C.saida("bloqueada", excecao="fora_do_ar", motivo="o Chrome não gerou o PDF", log=r.stderr[-400:])
        sys.exit(C.FORA_DO_AR)
    _metadados(alvo, a.titulo or os.path.basename(a.pagina))
    C.saida("ok", arquivo=alvo, paginas=len(PdfReader(alvo).pages))


def _metadados(caminho, titulo):
    r = PdfReader(caminho)
    w = PdfWriter(clone_from=r)
    w.add_metadata({"/Title": titulo, "/Author": C.AUTOR, "/Creator": "ARKOS Engine · arkos-pdf"})
    with open(caminho, "wb") as f:
        w.write(f)


def _faixa(txt, total):
    pags = []
    for parte in txt.split(","):
        if "-" in parte:
            i, f = parte.split("-")
            pags += range(int(i), int(f) + 1)
        elif parte.strip():
            pags.append(int(parte))
    fora = [p for p in pags if p < 1 or p > total]
    if fora:
        C.saida("aguardando", excecao="entrada_incompleta", falta=[f"páginas fora do arquivo (1-{total}): {fora}"])
        sys.exit(C.ENTRADA_INCOMPLETA)
    return [p - 1 for p in pags]


def juntar(a):
    faltam = [f for f in a.arquivos if not os.path.isfile(f)]
    if faltam or not a.titulo:
        C.saida("aguardando", excecao="entrada_incompleta", falta=faltam + ([] if a.titulo else ["--titulo"]))
        sys.exit(C.ENTRADA_INCOMPLETA)
    w = PdfWriter()
    for f in a.arquivos:
        w.append(f)
    w.add_metadata({"/Title": a.titulo, "/Author": C.AUTOR})
    alvo = C.caminho_novo(C.pasta_casa(a.casa, a.cliente, a.projeto, "documentos"), a.titulo, "pdf")
    with open(alvo, "wb") as fh:
        w.write(fh)
    C.saida("ok", arquivo=alvo, paginas=len(PdfReader(alvo).pages))


def paginas(a):
    r = PdfReader(a.arquivo)
    w = PdfWriter()
    for i in _faixa(a.faixa, len(r.pages)):
        w.add_page(r.pages[i])
    base = C.base_sem_data(a.arquivo)
    alvo = C.caminho_novo(C.pasta_casa(a.casa, a.cliente, a.projeto, "documentos"), f"{base}-p{a.faixa}", "pdf")
    with open(alvo, "wb") as fh:
        w.write(fh)
    C.saida("ok", arquivo=alvo, paginas=len(w.pages))


def carimbar(a):
    r = PdfReader(a.arquivo)
    w = PdfWriter()
    for pg in r.pages:
        larg, alt = float(pg.mediabox.width), float(pg.mediabox.height)
        buf = io.BytesIO()
        cv = rl_canvas.Canvas(buf, pagesize=(larg, alt))
        cv.setFont("Helvetica", 42)
        cv.setFillColor(colors.Color(.42, .44, .47, alpha=.16))  # aço translúcido: legível sem tampar o texto
        cv.translate(larg / 2, alt / 2)
        cv.rotate(35)
        cv.drawCentredString(0, 0, a.texto.upper())
        cv.save()
        buf.seek(0)
        pg.merge_page(PdfReader(buf).pages[0])
        w.add_page(pg)
    base = C.base_sem_data(a.arquivo)
    alvo = C.caminho_novo(C.pasta_casa(a.casa, a.cliente, a.projeto, "documentos"), f"{base}-{C.slug(a.texto, 16)}", "pdf")
    with open(alvo, "wb") as fh:
        w.write(fh)
    C.saida("ok", arquivo=alvo, paginas=len(w.pages))


def ler(a):
    r = PdfReader(a.arquivo)
    meta = {k.strip("/"): str(v) for k, v in (r.metadata or {}).items()}
    print(json.dumps({"metadados": meta, "paginas": [p.extract_text() or "" for p in r.pages]}, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    cmds = {}
    p = sub.add_parser("gerar"); p.add_argument("spec"); p.add_argument("--trocar"); cmds["gerar"] = (p, gerar)
    p = sub.add_parser("html"); p.add_argument("pagina"); p.add_argument("--titulo"); p.add_argument("--spec"); cmds["html"] = (p, html)
    p = sub.add_parser("juntar"); p.add_argument("arquivos", nargs="+"); p.add_argument("--titulo"); cmds["juntar"] = (p, juntar)
    p = sub.add_parser("paginas"); p.add_argument("arquivo"); p.add_argument("--faixa", required=True); cmds["paginas"] = (p, paginas)
    p = sub.add_parser("carimbar"); p.add_argument("arquivo"); p.add_argument("--texto", required=True); cmds["carimbar"] = (p, carimbar)
    for p, _ in cmds.values():
        p.add_argument("--casa"); p.add_argument("--cliente"); p.add_argument("--projeto")
    p = sub.add_parser("ler"); p.add_argument("arquivo"); cmds["ler"] = (p, ler)
    a = ap.parse_args()
    cmds[a.cmd][1](a)


if __name__ == "__main__":
    main()
