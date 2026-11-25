"""arkos-artes: criativos estáticos (9:16, 4:5, 1:1), carrossel e PDF do carrossel, por HTML + Chrome headless oculto.

  gerar:  py -3 artes_arkos.py gerar artes.json --casa C --cliente X --projeto Y
  checar: py -3 artes_arkos.py checar <pasta-da-saida>   (tamanho exato de cada PNG, contagem, PDF)

artes.json: {"titulo": str, "formato": "9:16"|"4:5"|"1:1",
  "marca": {"nome": str, "fundo": "#hex", "texto": "#hex", "acento": "#hex", "logo"?: "caminho.svg|png"},
  "pecas": [{"kicker"?: str, "titulo": str, "texto"?: str, "cta"?: str, "imagem"?: "caminho local"}],
  "pdf"?: true}
A marca é a do CLIENTE (não a da ARKOS). Regras duras no SKILL.md: safe zone, limites de texto, contraste.
"""
import argparse
import base64
import html
import json
import mimetypes
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arkos_casa as C  # noqa: E402

FORMATOS = {"9:16": (1080, 1920), "4:5": (1080, 1350), "1:1": (1080, 1080)}
# safe zone em px (topo, base, lados) em 1080 de largura. 9:16 segue o guia de anúncios da Meta para Stories/Reels
# (14% em cima, 35% embaixo, 6% nos lados livres de texto e logo): 1920 x 0,14 = 269 -> 270; 1920 x 0,35 = 672.
# Lados ficam em 90 (mais folgado que os 65 do guia). Mesma regra no arkos-gate.
SAFE = {"9:16": (270, 672, 90), "4:5": (110, 110, 90), "1:1": (100, 100, 90)}
LIMITE = {"kicker": 32, "titulo": 70, "texto": 200, "cta": 28}
FONTES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")


def _lum(hexcor):
    h = hexcor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4  # noqa: E731
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)


def contraste(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + .05) / (lb + .05)


def _data_uri(caminho):
    tipo = mimetypes.guess_type(caminho)[0] or "application/octet-stream"
    with open(caminho, "rb") as f:
        return f"data:{tipo};base64,{base64.b64encode(f.read()).decode()}"


def validar(spec):
    C.exigir(spec, ["titulo", "formato", "marca.nome", "marca.fundo", "marca.texto", "marca.acento", "pecas"])
    erros = []
    if spec["formato"] not in FORMATOS:
        erros.append(f"formato '{spec['formato']}' (use 9:16, 4:5 ou 1:1)")
    for i, p in enumerate(spec["pecas"], 1):
        if not p.get("titulo"):
            erros.append(f"pecas[{i}].titulo")
        for campo, lim in LIMITE.items():
            if len(p.get(campo) or "") > lim:
                erros.append(f"pecas[{i}].{campo} com {len(p[campo])} caracteres (máximo {lim}: corte o texto, não a fonte)")
        if p.get("imagem") and not os.path.isfile(p["imagem"]):
            erros.append(f"pecas[{i}].imagem não encontrada: {p['imagem']}")
    m = spec["marca"]
    if contraste(m["fundo"], m["texto"]) < 4.5:
        erros.append(f"contraste texto/fundo {contraste(m['fundo'], m['texto']):.1f}:1 (mínimo 4,5:1)")
    if m.get("logo") and not os.path.isfile(m["logo"]):
        erros.append(f"marca.logo não encontrado: {m['logo']}")
    if erros:
        C.saida("aguardando", excecao="entrada_incompleta", falta=erros)
        sys.exit(C.ENTRADA_INCOMPLETA)


def _css(spec, w, h):
    m = spec["marca"]
    topo, base, lado = SAFE[spec["formato"]]
    inter = _data_uri(os.path.join(FONTES, "InterTight.ttf")) if os.path.isfile(os.path.join(FONTES, "InterTight.ttf")) else ""
    mono = _data_uri(os.path.join(FONTES, "JetBrainsMono.ttf")) if os.path.isfile(os.path.join(FONTES, "JetBrainsMono.ttf")) else ""
    acento_txt = m["fundo"] if contraste(m["acento"], m["fundo"]) >= 3 else m["texto"]
    cta_txt = m["fundo"] if contraste(m["acento"], m["fundo"]) >= 3 and contraste(m["fundo"], m["acento"]) >= 4.5 else m["texto"]
    escala = w / 1080
    return f"""
@font-face {{ font-family: AS; src: url({inter}) format("truetype"); font-weight: 100 900; }}
@font-face {{ font-family: AM; src: url({mono}) format("truetype"); font-weight: 100 800; }}
@page {{ size: {w}px {h}px; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: {m['fundo']}; }}
.peca {{ position: relative; width: {w}px; height: {h}px; overflow: hidden; background: {m['fundo']}; color: {m['texto']};
  font-family: AS, "Segoe UI", sans-serif; display: flex; flex-direction: column; justify-content: flex-end;
  padding: {topo}px {lado}px {base}px; page-break-after: always; break-after: page; }}
.peca:last-child {{ page-break-after: auto; break-after: auto; }}
.foto {{ position: absolute; inset: 0; background-size: cover; background-position: center; }}
.foto::after {{ content: ""; position: absolute; inset: 0; background: linear-gradient(180deg, transparent 25%, {m['fundo']}EE 72%); }}
.conteudo {{ position: relative; display: grid; gap: {int(28 * escala)}px; }}
.topo {{ position: absolute; top: {topo}px; left: {lado}px; right: {lado}px; display: flex; justify-content: space-between; align-items: center;
  font: 500 {int(24 * escala)}px/1 AM, monospace; letter-spacing: .14em; text-transform: uppercase; opacity: .8; }}
.topo img {{ height: {int(56 * escala)}px; width: auto; }}
.kicker {{ font: 500 {int(26 * escala)}px/1.2 AM, monospace; letter-spacing: .14em; text-transform: uppercase; color: {m['acento'] if contraste(m['acento'], m['fundo']) >= 3 else m['texto']}; }}
h1 {{ font-weight: 600; font-size: {int(88 * escala)}px; line-height: 1.02; letter-spacing: -.03em; text-wrap: balance; }}
p {{ font-size: {int(36 * escala)}px; line-height: 1.35; opacity: .92; text-wrap: pretty; max-width: 26ch; }}
.cta {{ justify-self: start; margin-top: {int(12 * escala)}px; padding: {int(26 * escala)}px {int(40 * escala)}px; border-radius: 999px;
  background: {m['acento']}; color: {cta_txt}; font-weight: 600; font-size: {int(34 * escala)}px; }}
.n {{ font: 500 {int(22 * escala)}px/1 AM, monospace; opacity: .7; }}
"""  # noqa: E501  (acento_txt fica para a variação clara)


def _peca_html(spec, p, i, total):
    m = spec["marca"]
    foto = f'<div class="foto" style="background-image:url({_data_uri(p["imagem"])})"></div>' if p.get("imagem") else ""
    logo = f'<img src="{_data_uri(m["logo"])}" alt="">' if m.get("logo") else f"<span>{html.escape(m['nome'])}</span>"
    num = f'<span class="n">{i:02d}/{total:02d}</span>' if total > 1 else ""
    partes = [f'<span class="kicker">{html.escape(p["kicker"])}</span>' if p.get("kicker") else "",
              f"<h1>{html.escape(p['titulo'])}</h1>",
              f"<p>{html.escape(p['texto'])}</p>" if p.get("texto") else "",
              f'<span class="cta">{html.escape(p["cta"])}</span>' if p.get("cta") else ""]
    # numeração no topo, ao lado da marca: a faixa de baixo é da interface do app (safe zone)
    return f'<section class="peca">{foto}<div class="topo">{logo}{num}</div><div class="conteudo">{"".join(partes)}</div></section>'


def _pagina(spec, pecas_html, w, h):
    return f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{html.escape(spec["titulo"])}</title><style>{_css(spec, w, h)}</style></head><body>{pecas_html}</body></html>'


def _chrome(args, timeout=120):
    chrome = C.achar_chrome()
    if not chrome:
        C.saida("bloqueada", excecao="fora_do_ar", motivo="Chrome/Edge não encontrado",
                como_resolver="instale o Google Chrome ou defina ARKOS_CHROME com o caminho do executável")
        sys.exit(C.FORA_DO_AR)
    with tempfile.TemporaryDirectory() as perfil:
        return C.rodar_oculto([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                               f"--user-data-dir={perfil}", *args], timeout=timeout)


def gerar(a):
    spec = C.carregar_spec(a.spec)
    validar(spec)
    w, h = FORMATOS[spec["formato"]]
    base = C.pasta_casa(a.casa, a.cliente, a.projeto, "criativos")
    raiz = os.path.join(base, f"{C.slug(spec['titulo'])}-{C.hoje()}")
    pasta, n = raiz, 1
    while os.path.exists(pasta):  # pasta nova por lote, nunca sobrescreve
        n += 1
        pasta = f"{raiz}-v{n}"
    os.makedirs(pasta)
    total = len(spec["pecas"])
    pngs = []
    for i, p in enumerate(spec["pecas"], 1):
        src = os.path.join(pasta, f"peca-{i:02d}.html")
        with open(src, "w", encoding="utf-8") as f:
            f.write(_pagina(spec, _peca_html(spec, p, i, total), w, h))
        png = os.path.join(pasta, f"peca-{i:02d}.png")
        _chrome([f"--window-size={w},{h}", f"--screenshot={png}", "file:///" + src.replace("\\", "/")])
        if not os.path.isfile(png):
            C.saida("bloqueada", excecao="fora_do_ar", motivo=f"o Chrome não gerou {png}")
            sys.exit(C.FORA_DO_AR)
        pngs.append(png)
    pdf = None
    if spec.get("pdf", total > 1):
        src = os.path.join(pasta, "carrossel.html")
        with open(src, "w", encoding="utf-8") as f:
            f.write(_pagina(spec, "".join(_peca_html(spec, p, i, total) for i, p in enumerate(spec["pecas"], 1)), w, h))
        pdf = os.path.join(pasta, "carrossel.pdf")
        _chrome(["--no-pdf-header-footer", f"--print-to-pdf={pdf}", "file:///" + src.replace("\\", "/")])
        pdf = pdf if os.path.isfile(pdf) else None
    with open(os.path.join(pasta, "artes.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    problemas = _checar(pasta, spec)
    C.saida("ok" if not problemas else "reprovado", pasta=pasta, pecas=pngs, pdf=pdf, problemas=problemas)


def _checar(pasta, spec=None):
    from PIL import Image
    if spec is None:
        spec = C.carregar_spec(os.path.join(pasta, "artes.json"))
    w, h = FORMATOS[spec["formato"]]
    probs = []
    pngs = sorted(f for f in os.listdir(pasta) if f.startswith("peca-") and f.endswith(".png"))
    if len(pngs) != len(spec["pecas"]):
        probs.append(f"{len(pngs)} PNG para {len(spec['pecas'])} peças")
    for f in pngs:
        im = Image.open(os.path.join(pasta, f))
        if im.size != (w, h):
            probs.append(f"{f}: {im.size[0]}x{im.size[1]}, esperado {w}x{h}")
        # peça vazia: quase uma cor só
        cores = im.convert("RGB").resize((54, 96)).getcolors(54 * 96) or []
        if len(cores) < 8:
            probs.append(f"{f}: parece vazia ({len(cores)} cores)")
    if spec.get("pdf", len(spec["pecas"]) > 1):
        pdf = os.path.join(pasta, "carrossel.pdf")
        if not os.path.isfile(pdf):
            probs.append("carrossel.pdf não gerado")
        else:
            try:
                from pypdf import PdfReader
                n = len(PdfReader(pdf).pages)
                if n != len(spec["pecas"]):
                    probs.append(f"carrossel.pdf com {n} páginas para {len(spec['pecas'])} peças")
            except ImportError:
                pass
    return probs


def checar(a):
    p = _checar(a.pasta)
    C.saida("ok" if not p else "reprovado", pasta=a.pasta, problemas=p)
    sys.exit(0 if not p else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gerar")
    g.add_argument("spec")
    g.add_argument("--casa")
    g.add_argument("--cliente")
    g.add_argument("--projeto")
    sub.add_parser("checar").add_argument("pasta")
    a = ap.parse_args()
    {"gerar": gerar, "checar": checar}[a.cmd](a)


if __name__ == "__main__":
    main()
