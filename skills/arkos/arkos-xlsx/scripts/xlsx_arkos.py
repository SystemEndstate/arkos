"""arkos-xlsx: gera, edita e confere planilhas Excel (.xlsx) com openpyxl, na identidade ARKOS.

  gerar:    py -3 xlsx_arkos.py gerar planilha.json --casa C --cliente X --projeto Y
  editar:   py -3 xlsx_arkos.py editar entrada.xlsx --celulas mudancas.json --casa C --cliente X --projeto Y
  conferir: py -3 xlsx_arkos.py conferir arquivo.xlsx   (fórmulas quebradas, refs fora da aba, erros #REF!/#DIV/0!)
  ler:      py -3 xlsx_arkos.py ler arquivo.xlsx        (abas, cabeçalho e primeiras linhas, JSON)

planilha.json: {"titulo": str, "abas": [{"nome": str, "colunas": [{"nome": str, "formato"?: "moeda"|"int"|"pct"|"data"|"texto", "largura"?: n}],
                 "linhas": [[..]], "total"?: {"rotulo": "Total", "somar": ["Receita", ...]}, "notas"?: [str]}]}
Uma célula pode ser fórmula ("=B2*C2"); o total usa SUM nas colunas pedidas (a planilha recalcula ao abrir).
mudancas.json: {"Aba!B3": 120, "Aba!D2": "=B2*C2"}
"""
import argparse
import json
import os
import re
import sys

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter, range_boundaries
from openpyxl.worksheet.properties import WorksheetProperties

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arkos_casa as C  # noqa: E402

FORMATOS = {"moeda": 'R$ #,##0.00;[Red]-R$ #,##0.00', "int": "#,##0", "pct": "0.0%", "data": "dd/mm/yyyy", "texto": "@"}
CAB = Font(name=C.FONTE_MONO, size=9, bold=True, color="FFFFFF")
CORPO = Font(name=C.FONTE, size=10.5, color=C.INK)
TOT = Font(name=C.FONTE, size=10.5, bold=True, color=C.INK)
LINHA = Border(bottom=Side(style="thin", color=C.LINE))
ERROS = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!")


def _aba(wb, cfg, primeira):
    ws = wb.active if primeira else wb.create_sheet()
    ws.title = str(cfg["nome"])[:31]
    ws.sheet_properties = WorksheetProperties(tabColor=C.INK)
    cols = cfg["colunas"]
    for c, col in enumerate(cols, 1):
        cel = ws.cell(row=1, column=c, value=col["nome"])
        cel.font, cel.fill = CAB, PatternFill("solid", fgColor=C.INK)
        cel.alignment = Alignment(vertical="center")
        ws.column_dimensions[get_column_letter(c)].width = col.get("largura") or max(12, min(42, len(str(col["nome"])) + 6))
    ws.row_dimensions[1].height = 22
    for r, linha in enumerate(cfg.get("linhas", []), 2):
        for c, v in enumerate(linha, 1):
            cel = ws.cell(row=r, column=c, value=v)
            cel.font, cel.border = CORPO, LINHA
            fmt = cols[c - 1].get("formato") if c <= len(cols) else None
            if fmt in FORMATOS:
                cel.number_format = FORMATOS[fmt]
    ult = len(cfg.get("linhas", [])) + 1
    if cfg.get("total") and ult > 1:
        tr = ult + 1
        ws.cell(row=tr, column=1, value=cfg["total"].get("rotulo", "Total")).font = TOT
        nomes = [c["nome"] for c in cols]
        for nome in cfg["total"].get("somar", []):
            if nome not in nomes:
                C.saida("aguardando", excecao="entrada_incompleta", falta=[f"coluna '{nome}' do total não existe na aba {cfg['nome']}"])
                sys.exit(C.ENTRADA_INCOMPLETA)
            c = nomes.index(nome) + 1
            L = get_column_letter(c)
            cel = ws.cell(row=tr, column=c, value=f"=SUM({L}2:{L}{ult})")
            cel.font = TOT
            cel.number_format = FORMATOS.get(cols[c - 1].get("formato"), "General")
            cel.border = Border(top=Side(style="medium", color=C.INK))
    ws.freeze_panes = "A2"
    if ult > 1:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{ult}"
    for k, nota in enumerate(cfg.get("notas", [])):
        cel = ws.cell(row=ult + 3 + k, column=1, value=nota)
        cel.font = Font(name=C.FONTE, size=9, italic=True, color=C.STEEL)


def gerar(a):
    spec = C.carregar_spec(a.spec)
    C.exigir(spec, ["titulo", "abas"])
    for i, aba in enumerate(spec["abas"]):
        C.exigir(aba, ["nome", "colunas"], contexto=f"abas[{i}]")
    wb = Workbook()
    for i, aba in enumerate(spec["abas"]):
        _aba(wb, aba, i == 0)
    wb.properties.title, wb.properties.creator, wb.properties.subject = spec["titulo"], C.AUTOR, f"Cliente: {a.cliente}"
    alvo = C.caminho_novo(C.pasta_casa(a.casa, a.cliente, a.projeto, "planilhas"), spec["titulo"], "xlsx")
    wb.save(alvo)
    problemas = _conferir(alvo)
    C.saida("ok" if not problemas else "reprovado", arquivo=alvo, abas=len(spec["abas"]), problemas=problemas)


def _conferir(caminho):
    wb = load_workbook(caminho)
    nomes = set(wb.sheetnames)
    probs = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cel in row:
                v = cel.value
                if isinstance(v, str) and v.strip() in ERROS:
                    probs.append(f"{ws.title}!{cel.coordinate}: valor de erro {v}")
                if isinstance(v, str) and v.startswith("="):
                    if v.count("(") != v.count(")"):
                        probs.append(f"{ws.title}!{cel.coordinate}: parênteses desbalanceados em {v}")
                    for aba in re.findall(r"'?([^'!=(),]+)'?!", v):
                        if aba not in nomes:
                            probs.append(f"{ws.title}!{cel.coordinate}: aba '{aba}' não existe ({v})")
                    for ref in re.findall(r"(?<![A-Za-z!])\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?", v):
                        if ref[1] and int(ref[1]) > max(ws.max_row, 1) + 1:
                            probs.append(f"{ws.title}!{cel.coordinate}: referência {ref[0]}{ref[1]} fora dos dados")
                    if f"{cel.coordinate}" in re.sub(r"\$", "", v.split("(", 1)[-1]).split(":"):
                        probs.append(f"{ws.title}!{cel.coordinate}: referência circular direta")
    return probs


def editar(a):
    if not os.path.isfile(a.entrada) or not a.celulas:
        C.saida("aguardando", excecao="entrada_incompleta", falta=[a.entrada if not os.path.isfile(a.entrada) else "--celulas"])
        sys.exit(C.ENTRADA_INCOMPLETA)
    wb = load_workbook(a.entrada)
    mud = C.carregar_spec(a.celulas)
    erros = []
    for alvo_cel, valor in mud.items():
        if "!" not in alvo_cel or alvo_cel.split("!")[0] not in wb.sheetnames:
            erros.append(alvo_cel)
            continue
        aba, coord = alvo_cel.split("!")
        cel = wb[aba][coord]
        cel.value = valor  # mantém fonte, borda e formato que a célula já tinha
    if erros:
        C.saida("aguardando", excecao="entrada_incompleta", falta=[f"aba inexistente em: {e}" for e in erros])
        sys.exit(C.ENTRADA_INCOMPLETA)
    alvo = C.caminho_novo(C.pasta_casa(a.casa, a.cliente, a.projeto, "planilhas"), C.base_sem_data(a.entrada) + "-editado", "xlsx")
    wb.save(alvo)
    problemas = _conferir(alvo)
    C.saida("ok" if not problemas else "reprovado", arquivo=alvo, celulas=len(mud), problemas=problemas)


def conferir(a):
    p = _conferir(a.arquivo)
    C.saida("ok" if not p else "reprovado", arquivo=a.arquivo, problemas=p)
    sys.exit(0 if not p else 1)


def ler(a):
    wb = load_workbook(a.arquivo)
    out = {ws.title: {"dimensao": ws.dimensions, "linhas": [[c.value for c in r] for r in ws.iter_rows(max_row=8)]} for ws in wb.worksheets}
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gerar")
    g.add_argument("spec")
    e = sub.add_parser("editar")
    e.add_argument("entrada")
    e.add_argument("--celulas")
    for p in (g, e):
        p.add_argument("--casa")
        p.add_argument("--cliente")
        p.add_argument("--projeto")
    for nome in ("conferir", "ler"):
        sub.add_parser(nome).add_argument("arquivo")
    a = ap.parse_args()
    {"gerar": gerar, "editar": editar, "conferir": conferir, "ler": ler}[a.cmd](a)


if __name__ == "__main__":
    main()
