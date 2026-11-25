"""arkos-pptx: gera e edita PowerPoint (.pptx) com python-pptx, 16:9, na identidade ARKOS.

  gerar:  py -3 pptx_arkos.py gerar deck.json [--trocar chaves.json] --casa C --cliente X --projeto Y
  editar: py -3 pptx_arkos.py editar entrada.pptx --trocar chaves.json --casa C --cliente X --projeto Y
  ler:    py -3 pptx_arkos.py ler arquivo.pptx   (texto por slide, JSON)

deck.json: {"titulo": str, "tema"?: "escuro"|"claro", "slides": [
   {"capa": "Título", "sub"?: str} | {"secao": "Nome", "n"?: "01"}
 | {"titulo": str, "texto": str} | {"titulo": str, "lista": [..]}
 | {"titulo": str, "numeros": [{"valor": "3", "rotulo": "posts por semana"}]}
 | {"titulo": str, "tabela": {"colunas": [..], "linhas": [[..]]}}
 | {"fim": "Próximo passo", "sub"?: str}], "notas"?: por slide em "nota": str}
Tema escuro (padrão): fundo Ink com Volt como acento. Tema claro: papel com marca monocromática (sem Volt).
"""
import argparse
import json
import os
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Pt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arkos_casa as C  # noqa: E402

W, H = Emu(12192000), Emu(6858000)  # 16:9
M = Emu(640080)  # margem 0,7"


def rgb(h):
    return RGBColor.from_string(h)


class Tema:
    def __init__(self, escuro):
        self.escuro = escuro
        self.fundo = C.INK if escuro else C.PAPER
        self.texto = "F1F2EF" if escuro else C.INK
        self.mudo = "A9AFB7" if escuro else C.STEEL
        self.acento = C.VOLT if escuro else C.INK      # Volt só no escuro
        self.cartao = C.GRAPHITE if escuro else "FFFFFF"


def _fundo(slide, t):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = rgb(t.fundo)


def _caixa(slide, x, y, w, h, texto, tam, cor, mono=False, negrito=False, ancora=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = ancora
    tf.margin_left = tf.margin_right = 0
    linhas = texto if isinstance(texto, list) else [texto]
    for i, linha in enumerate(linhas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = str(linha)
        r.font.size = Pt(tam)
        r.font.name = C.FONTE_MONO if mono else C.FONTE
        r.font.bold = negrito
        r.font.color.rgb = rgb(cor)
        p.space_after = Pt(tam * .5)
    return tb


# pás oficiais do Rotor (grade 256, mesma geometria do relatório e do site); a de cima é a pá de ação
PAS = {
    "t": [(32, 32), (148, 32), (148, 66), (118, 96), (32, 96)],
    "r": [(224, 32), (224, 148), (190, 148), (160, 118), (160, 32)],
    "b": [(224, 224), (108, 224), (108, 190), (138, 160), (224, 160)],
    "l": [(32, 224), (32, 108), (66, 108), (96, 138), (96, 224)],
}


def _rotor(slide, x, y, lado, t):
    """Marca ARKOS com as 4 pás chanfradas reais. Escuro: pá de cima em Volt; claro: tudo em Ink."""
    esc = lado / 208  # viewBox 24..232
    for nome, pts in PAS.items():
        px = [(int(x + (a - 24) * esc), int(y + (b - 24) * esc)) for a, b in pts]
        fb = slide.shapes.build_freeform(px[0][0], px[0][1], scale=1.0)
        fb.add_line_segments(px[1:], close=True)
        s = fb.convert_to_shape()
        s.name = f"arkos-rotor-{nome}"
        s.fill.solid()
        s.fill.fore_color.rgb = rgb(t.acento if nome == "t" else t.texto)
        s.line.fill.background()


def _cabeca(slide, t, cliente, n, total):
    _rotor(slide, M, Emu(300000), Emu(190000), t)
    _caixa(slide, M + Emu(260000), Emu(290000), Emu(5000000), Emu(240000), "ARKOS ENGINE  ·  " + cliente.upper(), 9, t.mudo, mono=True)
    tb = _caixa(slide, W - M - Emu(1500000), Emu(290000), Emu(1500000), Emu(240000), f"{n:02d} / {total:02d}", 9, t.mudo, mono=True)
    tb.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT


def _titulo(slide, t, texto):
    _caixa(slide, M, Emu(820000), W - 2 * M, Emu(900000), texto, 32, t.texto)


def construir(prs, spec, cliente):
    t = Tema(spec.get("tema", "escuro") != "claro")
    layout = prs.slide_layouts[6]  # em branco
    total = len(spec["slides"])
    for i, s in enumerate(spec["slides"], 1):
        sl = prs.slides.add_slide(layout)
        _fundo(sl, t)
        if "capa" in s:
            _rotor(sl, M, M, Emu(560000), t)
            _caixa(sl, M, Emu(2300000), W - 2 * M, Emu(2200000), s["capa"], 46, t.texto, ancora=MSO_ANCHOR.BOTTOM)
            if s.get("sub"):
                _caixa(sl, M, Emu(4650000), W - 2 * M, Emu(700000), s["sub"], 18, t.mudo)
            _caixa(sl, M, H - Emu(700000), W - 2 * M, Emu(300000), f"ARKOS ENGINE  ·  {cliente.upper()}  ·  {C.hoje()}", 10, t.mudo, mono=True)
        elif "secao" in s:
            _caixa(sl, M, Emu(2200000), Emu(2000000), Emu(900000), s.get("n", f"{i:02d}"), 54, t.acento, mono=True)
            _caixa(sl, M, Emu(3200000), W - 2 * M, Emu(1200000), s["secao"], 40, t.texto)
        elif "fim" in s:
            _rotor(sl, M, Emu(1500000), Emu(760000), t)
            _caixa(sl, M, Emu(2600000), W - 2 * M, Emu(1300000), s["fim"], 40, t.texto)
            if s.get("sub"):
                _caixa(sl, M, Emu(4000000), W - 2 * M, Emu(900000), s["sub"], 18, t.mudo)
        else:
            _cabeca(sl, t, cliente, i, total)
            _titulo(sl, t, s.get("titulo", ""))
            topo, larg = Emu(1900000), W - 2 * M
            if "texto" in s:
                _caixa(sl, M, topo, Emu(int(larg * .72)), Emu(3800000), s["texto"], 20, t.texto)
            elif "lista" in s:
                _caixa(sl, M, topo, larg, Emu(4200000), [f"—  {x}" for x in s["lista"]], 20, t.texto)
            elif "numeros" in s:
                nums = s["numeros"][:4]
                cw = (larg - Emu(200000) * (len(nums) - 1)) // max(len(nums), 1)
                for k, item in enumerate(nums):
                    x = M + k * (cw + Emu(200000))
                    cx = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, topo, cw, Emu(2600000))
                    cx.fill.solid()
                    cx.fill.fore_color.rgb = rgb(t.cartao)
                    cx.line.fill.background()
                    _caixa(sl, x + Emu(220000), topo + Emu(300000), cw - Emu(440000), Emu(1200000), item["valor"], 48, t.acento)
                    _caixa(sl, x + Emu(220000), topo + Emu(1550000), cw - Emu(440000), Emu(900000), item["rotulo"], 14, t.mudo)
            elif "tabela" in s:
                cols, linhas = s["tabela"]["colunas"], s["tabela"]["linhas"]
                tb = sl.shapes.add_table(len(linhas) + 1, len(cols), M, topo, larg, Emu(420000 * (len(linhas) + 1))).table
                for c, nome in enumerate(cols):
                    cel = tb.cell(0, c)
                    cel.fill.solid()
                    cel.fill.fore_color.rgb = rgb(C.GRAPHITE if t.escuro else C.INK)
                    cel.text = str(nome).upper()
                    r = cel.text_frame.paragraphs[0].runs[0]
                    r.font.size, r.font.name, r.font.color.rgb = Pt(10), C.FONTE_MONO, rgb("FFFFFF")
                for li, linha in enumerate(linhas, 1):
                    for c, v in enumerate(linha):
                        cel = tb.cell(li, c)
                        cel.fill.solid()
                        cel.fill.fore_color.rgb = rgb(t.fundo if li % 2 else t.cartao)
                        cel.text = str(v)
                        r = cel.text_frame.paragraphs[0].runs[0]
                        r.font.size, r.font.name, r.font.color.rgb = Pt(14), C.FONTE, rgb(t.texto)
        if s.get("nota"):
            sl.notes_slide.notes_text_frame.text = s["nota"]


def gerar(a):
    spec = C.carregar_spec(a.spec)
    C.exigir(spec, ["titulo", "slides"])
    if a.trocar:
        spec = C.aplicar_chaves(spec, C.carregar_spec(a.trocar))
    falta = C.pendentes(spec)
    pasta = C.pasta_casa(a.casa, a.cliente, a.projeto, "apresentacoes")
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    construir(prs, spec, a.cliente)
    cp = prs.core_properties
    cp.title, cp.author, cp.subject = spec["titulo"], C.AUTOR, f"Cliente: {a.cliente}"
    alvo = C.caminho_novo(pasta, spec["titulo"], "pptx")
    prs.save(alvo)
    C.saida("amarelo" if falta else "ok", arquivo=alvo, slides=len(prs.slides), nao_trocadas=falta)


def _textos(prs):
    for sl in prs.slides:
        for sh in sl.shapes:
            if sh.has_text_frame:
                yield from sh.text_frame.paragraphs
            if sh.has_table:
                for row in sh.table.rows:
                    for cel in row.cells:
                        yield from cel.text_frame.paragraphs


def editar(a):
    if not os.path.isfile(a.entrada) or not a.trocar:
        C.saida("aguardando", excecao="entrada_incompleta", falta=[x for x in (a.entrada if not os.path.isfile(a.entrada) else None, None if a.trocar else "--trocar") if x])
        sys.exit(C.ENTRADA_INCOMPLETA)
    prs = Presentation(a.entrada)
    chaves = C.carregar_spec(a.trocar)
    n = 0
    for p in _textos(prs):
        txt = "".join(r.text for r in p.runs)
        novo = C.aplicar_chaves(txt, chaves)
        if novo != txt:
            n += 1
            for i, r in enumerate(p.runs):
                r.text = novo if i == 0 else ""
    alvo = C.caminho_novo(C.pasta_casa(a.casa, a.cliente, a.projeto, "apresentacoes"), C.base_sem_data(a.entrada) + "-editado", "pptx")
    prs.save(alvo)
    sobra = C.pendentes([p.text for p in _textos(prs)])
    C.saida("amarelo" if sobra else "ok", arquivo=alvo, paragrafos_trocados=n, nao_trocadas=sobra)


def ler(a):
    prs = Presentation(a.arquivo)
    out = [{"slide": i, "textos": [sh.text_frame.text for sh in sl.shapes if sh.has_text_frame and sh.text_frame.text.strip()],
            "nota": sl.notes_slide.notes_text_frame.text if sl.has_notes_slide else ""} for i, sl in enumerate(prs.slides, 1)]
    print(json.dumps({"titulo": prs.core_properties.title, "slides": out}, ensure_ascii=False, indent=1))


def previa(a):
    """Folha PNG de todos os slides, desenhada pelo PIL (sem precisar de PowerPoint). Mostra posição, cor e texto;
    a renderização final da fonte é a do PowerPoint/Keynote de quem abrir."""
    from PIL import Image, ImageDraw, ImageFont
    pasta_f = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
    def fonte(tam, mono=False):
        f = os.path.join(pasta_f, "JetBrainsMono.ttf" if mono else "InterTight.ttf")
        try:
            return ImageFont.truetype(f, tam)
        except OSError:
            return ImageFont.load_default()
    prs = Presentation(a.arquivo)
    esc = 960 / prs.slide_width
    quadros = []
    for sl in prs.slides:
        fill = sl.background.fill
        fundo = "#" + str(fill.fore_color.rgb) if fill.type is not None else "#FFFFFF"
        im = Image.new("RGB", (960, int(prs.slide_height * esc)), fundo)
        d = ImageDraw.Draw(im)
        for sh in sl.shapes:
            x, y, w, h = (int(v * esc) for v in (sh.left, sh.top, sh.width, sh.height))
            if sh.name.startswith("arkos-rotor-") and sh.fill.type == 1:
                pts = PAS[sh.name[-1]]
                xs, ys = [a for a, _ in pts], [b for _, b in pts]
                sx, sy = w / (max(xs) - min(xs)), h / (max(ys) - min(ys))
                d.polygon([(x + (a - min(xs)) * sx, y + (b - min(ys)) * sy) for a, b in pts], fill="#" + str(sh.fill.fore_color.rgb))
            elif sh.shape_type == 1 and sh.fill.type == 1:  # autoshape com preenchimento sólido
                d.rectangle([x, y, x + w, y + h], fill="#" + str(sh.fill.fore_color.rgb))
            if sh.has_table:
                tb = sh.table
                rh = h // max(len(tb.rows), 1)
                cw = w // max(len(tb.columns), 1)
                for ri, row in enumerate(tb.rows):
                    for ci, cel in enumerate(row.cells):
                        cor = "#" + str(cel.fill.fore_color.rgb) if cel.fill.type == 1 else fundo
                        d.rectangle([x + ci * cw, y + ri * rh, x + (ci + 1) * cw, y + (ri + 1) * rh], fill=cor)
                        r = cel.text_frame.paragraphs[0].runs
                        if r:
                            d.text((x + ci * cw + 8, y + ri * rh + 6), cel.text, font=fonte(max(8, int(r[0].font.size.pt * 12700 * esc)), r[0].font.name == C.FONTE_MONO), fill="#" + str(r[0].font.color.rgb))
            if sh.has_text_frame:
                yy = y
                for p in sh.text_frame.paragraphs:
                    for r in p.runs:
                        tam = max(8, int(r.font.size.pt * 12700 * esc)) if r.font.size else 14
                        f = fonte(tam, r.font.name == C.FONTE_MONO)
                        cor = "#" + str(r.font.color.rgb) if r.font.color and r.font.color.type else "#000000"
                        palavras, linha = r.text.split(), ""
                        for pal in palavras:
                            tenta = (linha + " " + pal).strip()
                            if d.textlength(tenta, font=f) > max(w, 40) and linha:
                                d.text((x, yy), linha, font=f, fill=cor)
                                yy += int(tam * 1.15)
                                linha = pal
                            else:
                                linha = tenta
                        dx = w - d.textlength(linha, font=f) if p.alignment == PP_ALIGN.RIGHT else 0
                        d.text((x + dx, yy), linha, font=f, fill=cor)
                        yy += int(tam * 1.4)
        quadros.append(im)
    colunas = 2
    lw, lh = quadros[0].size
    folha = Image.new("RGB", (colunas * lw + (colunas + 1) * 16, ((len(quadros) + 1) // colunas) * (lh + 16) + 16), "#D9DBD6")
    for i, q in enumerate(quadros):
        folha.paste(q, (16 + (i % colunas) * (lw + 16), 16 + (i // colunas) * (lh + 16)))
    alvo = os.path.splitext(a.arquivo)[0] + "-previa.png"
    folha.save(alvo)
    C.saida("ok", arquivo=alvo, slides=len(quadros))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("previa").add_argument("arquivo")
    g = sub.add_parser("gerar")
    g.add_argument("spec")
    e = sub.add_parser("editar")
    e.add_argument("entrada")
    for p in (g, e):
        p.add_argument("--trocar")
        p.add_argument("--casa")
        p.add_argument("--cliente")
        p.add_argument("--projeto")
    r = sub.add_parser("ler")
    r.add_argument("arquivo")
    a = ap.parse_args()
    {"gerar": gerar, "editar": editar, "ler": ler, "previa": previa}[a.cmd](a)


if __name__ == "__main__":
    main()
