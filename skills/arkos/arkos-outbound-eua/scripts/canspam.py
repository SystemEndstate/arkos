"""canspam.py - checagem CAN-SPAM de e-mail e preparo do lote de outbound para os EUA.

NUNCA envia. Só confere o texto, limpa a lista e grava o lote como RASCUNHO para o arkos-guarda-envio,
que é quem pede a aprovação e libera a ferramenta de envio (Instantly, Smartlead, etc.).

Regras do CAN-SPAM (15 U.S.C. 7701-7713; 16 CFR 316), conferidas no guia da FTC em 2026-11-22:
  cabeçalho verdadeiro (From/Reply-To/domínio) · assunto que não engana · identificar como anúncio ·
  endereço postal físico válido · forma clara de sair · atender o opt-out em até 10 dias úteis (a ARKOS: no mesmo dia)
  · quem contrata o envio também responde. Multa: até US$ 53.088 por e-mail (ajuste da FTC de 17/01/2025).

Uso:
  python canspam.py checar email.json            (from_nome, from_email, reply_to, dominio, assunto, corpo, eh_anuncio)
  python canspam.py lote leads.csv --supressao supressao.csv --caixas 3 --dia 1 [--out lote.csv] [--relatorio lote.json]
  python canspam.py bounce [--hard 0.025] [--plataforma 0.04] [--spam 0.002]   (decisão de pausa por entrega)
Saída 0 = ok · 1 = reprovado / pausar · 2 = entrada incompleta.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

MULTA_POR_EMAIL_USD = 53088  # FTC, ajuste de 2025-01-17; conferir em janeiro de cada ano
ASSUNTO_ENGANOSO = [r"^\s*(re|fwd?|enc)\s*:", r"\binvoice\b", r"\byour order\b", r"\bpayment (failed|due)\b",
                    r"\baccount (suspended|locked)\b", r"\bfinal notice\b", r"\burgent\b", r"\bwinner\b",
                    r"\byou('ve| have) won\b", r"\bfree money\b"]
SAIDA = [r"unsubscribe", r"opt[- ]?out", r"reply (with )?[\"']?(stop|remove|no)", r"don'?t want (to hear|these)",
         r"stop receiving", r"let me know if (you'?d|you would) (rather|prefer) not"]
ENDERECO = r"\b\d{1,6}\s+[A-Za-z0-9 .'-]+\b(st|street|ave|avenue|rd|road|blvd|suite|ste|dr|drive|ln|lane|way|pkwy|box)\b.*\b[A-Z]{2}\s+\d{5}(-\d{4})?\b"
PO_BOX = r"\b(p\.?\s?o\.?\s?box|pmb)\s*\d+.*\b[A-Z]{2}\s+\d{5}\b"
ROLE = {"info", "contact", "sales", "support", "admin", "hello", "office", "billing", "noreply", "no-reply", "abuse", "postmaster"}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
# Aquecimento por caixa/dia (heurística ARKOS, não é regra legal). Agências de 15-110 mil/dia operam
# ~15-20 por caixa, 2-3 caixas por domínio, com 2 semanas só de warmup. Regime: sobe no warmup (dias 1-14)
# e estabiliza em 15-20, com teto de 25 por caixa.
RAMPA = [(3, 5), (7, 10), (14, 15), (10**6, 20)]
TETO_POR_CAIXA = 25           # nunca passar disso por caixa/dia, mesmo com --limiar
CAIXAS_POR_DOMINIO = (2, 3)   # heurística: 2 a 3 caixas por domínio
# Limiares de entrega (RevenueFlow 1,41M envios; Yahoo oficial para spam):
BOUNCE_HARD_REAL = 0.02       # hard bounce real (endereço inexistente) > 2% pausa o LOTE
BOUNCE_PLATAFORMA = 0.03      # bounce total reportado pela plataforma > 3% pausa a CAIXA
SPAM_MAX = 0.003              # taxa de spam >= 0,3% pausa (Yahoo/Google, oficial)


def checar(e: dict) -> dict:
    falt = [k for k in ("from_nome", "from_email", "dominio", "assunto", "corpo") if not str(e.get(k, "")).strip()]
    if falt:
        return {"status": "entrada_incompleta", "faltando": falt}
    viol, avisos = [], []
    dom_from = e["from_email"].split("@")[-1].lower()
    if dom_from != e["dominio"].lower() and not dom_from.endswith("." + e["dominio"].lower()):
        viol.append(f"cabeçalho: From em {dom_from} não bate com o domínio de envio {e['dominio']}")
    if e.get("reply_to") and e["reply_to"].split("@")[-1].lower() not in (dom_from, e["dominio"].lower()):
        avisos.append("Reply-To em outro domínio: conferir se é da mesma empresa")
    for p in ASSUNTO_ENGANOSO:
        if re.search(p, e["assunto"], re.I):
            viol.append(f"assunto que engana: '{e['assunto']}' casa com {p}")
    corpo = e["corpo"]
    if not (re.search(ENDERECO, corpo, re.I | re.S) or re.search(PO_BOX, corpo, re.I | re.S)):
        viol.append("falta endereço postal físico válido (rua ou caixa postal registrada, cidade, UF, ZIP)")
    if not any(re.search(p, corpo, re.I) for p in SAIDA):
        viol.append("falta forma clara de sair (link de unsubscribe ou 'reply STOP')")
    if e.get("eh_anuncio", True) and not re.search(r"\b(advertisement|ad|promotional|this is a commercial)\b", corpo, re.I):
        avisos.append("mensagem comercial sem identificação como anúncio: o CAN-SPAM pede identificação clara "
                      "(exceto com consentimento prévio); decidir com o dono e registrar")
    if re.search(r"\{\{?\s*\w+\s*\}?\}", corpo + e["assunto"]):
        viol.append("variável de personalização sem preencher ({{...}})")
    return {"status": "ok" if not viol else "reprovado", "violacoes": viol, "avisos": avisos,
            "multa_maxima_usd_por_email": MULTA_POR_EMAIL_USD}


def _csv(texto: str) -> list[dict]:
    texto = texto.lstrip("﻿")
    delim = ";" if texto[:2048].count(";") > texto[:2048].count(",") else ","
    return [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(io.StringIO(texto), delimiter=delim)]


def teto_dia(caixas: int, dia: int) -> int:
    por = min(next(v for limite, v in RAMPA if dia <= limite), TETO_POR_CAIXA)
    return caixas * por


def bounce(hard_real: float | None = None, plataforma: float | None = None, spam: float | None = None) -> dict:
    """Decisão de pausa por entrega. hard_real = bounce de endereço inexistente; plataforma = bounce total
    reportado pela ferramenta (infla); spam = taxa de reclamação. Tudo em fração (0.02 = 2%)."""
    acoes = []
    if hard_real is not None and hard_real > BOUNCE_HARD_REAL:
        acoes.append({"gatilho": "hard_bounce_real", "valor": hard_real, "limite": BOUNCE_HARD_REAL,
                      "acao": "pausar o LOTE e limpar a lista (verificação de e-mail) antes de retomar"})
    if plataforma is not None and plataforma > BOUNCE_PLATAFORMA:
        acoes.append({"gatilho": "bounce_plataforma", "valor": plataforma, "limite": BOUNCE_PLATAFORMA,
                      "acao": "pausar a CAIXA e deixar reaquecer; o número da plataforma infla, conferir o hard real"})
    if spam is not None and spam >= SPAM_MAX:
        acoes.append({"gatilho": "spam", "valor": spam, "limite": SPAM_MAX,
                      "acao": "pausar: >= 0,3% é o teto oficial do Yahoo/Google; revisar oferta, segmento e aquecimento"})
    return {"status": "pausar" if acoes else "ok", "acoes": acoes,
            "regra": "hard real > 2% pausa o lote; bounce de plataforma > 3% pausa a caixa; spam >= 0,3% pausa (oficial)"}


def lote(leads_txt: str, supressao_txt: str, caixas: int, dia: int) -> dict:
    leads = _csv(leads_txt)
    if not leads:
        return {"status": "entrada_incompleta", "faltando": ["leads"]}
    if "email" not in leads[0]:
        return {"status": "entrada_incompleta", "faltando": ["coluna email"]}
    sup = {r.get("email", "").lower() for r in _csv(supressao_txt)} if supressao_txt.strip() else set()
    sup_dom = {s[1:] for s in sup if s.startswith("@")}
    ok, fora, vistos = [], [], set()
    for l in leads:
        em = l["email"].lower()
        motivo = None
        if not EMAIL_RE.match(em):
            motivo = "e-mail inválido"
        elif em in vistos:
            motivo = "duplicado"
        elif em in sup or em.split("@")[1] in sup_dom:
            motivo = "na lista de supressão (opt-out)"
        elif not l.get("fonte"):
            motivo = "sem fonte do lead (de onde veio)"
        elif em.split("@")[0] in ROLE:
            motivo = "endereço de função (info@, sales@...): baixa resposta e alto risco de denúncia"
        elif (l.get("pais") or "US").upper() not in ("US", "USA", "EUA", "UNITED STATES"):
            motivo = "fora dos EUA: outra lei (GDPR/CASL/LGPD), usar o fluxo do mercado certo"
        vistos.add(em)
        (fora if motivo else ok).append({**l, "email": em, **({"motivo": motivo} if motivo else {})})
    teto = teto_dia(caixas, dia)
    hoje, depois = ok[:teto], ok[teto:]
    return {"status": "ok" if hoje else "reprovado", "teto_hoje": teto,
            "regra_teto": f"heurística ARKOS: 2 semanas de warmup, depois 15-20/caixa/dia (teto {TETO_POR_CAIXA}), "
                          f"{CAIXAS_POR_DOMINIO[0]}-{CAIXAS_POR_DOMINIO[1]} caixas por domínio",
            "hoje": hoje, "proximos_dias": len(depois), "fora": fora,
            "contagem": {"lidos": len(leads), "hoje": len(hoje), "depois": len(depois), "fora": len(fora)},
            "estado": "rascunho: só o arkos-guarda-envio libera o envio"}


def _arg(argv, nome, padrao=None):
    return argv[argv.index(nome) + 1] if nome in argv else padrao


def _main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("checar", "lote", "bounce"):
        print(__doc__)
        return 2
    if argv[0] == "bounce":
        g = lambda n: float(_arg(argv, n)) if n in argv else None
        r = bounce(g("--hard"), g("--plataforma"), g("--spam"))
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 1 if r["status"] == "pausar" else 0
    if len(argv) < 2:
        print(__doc__)
        return 2
    if argv[0] == "checar":
        r = checar(json.loads(Path(argv[1]).read_text(encoding="utf-8")))
    else:
        sup = Path(_arg(argv, "--supressao")).read_text(encoding="utf-8") if "--supressao" in argv else ""
        r = lote(Path(argv[1]).read_text(encoding="utf-8"), sup, int(_arg(argv, "--caixas", 1)), int(_arg(argv, "--dia", 1)))
        if r["status"] == "ok" and "--out" in argv:
            p = Path(_arg(argv, "--out"))
            p.parent.mkdir(parents=True, exist_ok=True)
            campos = list(dict.fromkeys(k for x in r["hoje"] for k in x))
            with p.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=campos)
                w.writeheader()
                w.writerows(r["hoje"])
        if "--relatorio" in argv:
            p = Path(_arg(argv, "--relatorio"))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({k: v for k, v in r.items() if k != "hoje"}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return {"ok": 0, "reprovado": 1}.get(r["status"], 2)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
