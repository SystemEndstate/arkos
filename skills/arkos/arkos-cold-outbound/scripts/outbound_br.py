"""arkos-cold-outbound: cold outbound B2B no Brasil (e geral fora dos EUA), dentro da LGPD. Nunca envia:
entrega o lote como rascunho ao arkos-guarda-envio. EUA é da arkos-outbound-eua (CAN-SPAM).

  lote leads.csv --lia lia.json [--supressao s.csv] --caixas N --dia D --casa C --cliente X --projeto Y
  conferir sequencia.json
  montar sequencia.json lote.csv --casa C --cliente X --projeto Y      -> rascunhos.csv para o arkos-guarda-envio
  dns dominio.com.br                                                   -> SPF e DMARC do domínio de envio

Reusa da irmã arkos-outbound-eua/scripts/canspam.py: leitor de CSV, validação de e-mail, endereços de função
e a rampa de aquecimento (teto por caixa por dia). A regra legal aqui é a LGPD, não o CAN-SPAM.
"""
import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arkos_casa as C  # noqa: E402

_IRMA = Path(__file__).resolve().parents[2] / "arkos-outbound-eua" / "scripts"
sys.path.insert(0, str(_IRMA))
try:
    import canspam  # noqa: E402
except ImportError:
    canspam = None

ROLE_BR = {"contato", "vendas", "comercial", "atendimento", "financeiro", "suporte", "sac", "faleconosco",
           "rh", "marketing", "orcamento", "cobranca", "nfe", "compras", "recepcao"}
PESSOAL = {"gmail.com", "hotmail.com", "outlook.com", "live.com", "yahoo.com", "yahoo.com.br", "bol.com.br",
           "uol.com.br", "terra.com.br", "icloud.com", "ig.com.br"}
EUA = {"US", "USA", "EUA", "UNITED STATES", "ESTADOS UNIDOS"}
UE = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU",
      "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE", "UE", "EU"}
LIA = ["finalidade", "necessidade", "expectativa_do_titular", "salvaguardas"]
ASSUNTO_FALSO = re.compile(r"^\s*(re|fwd?|enc|res)\s*:|\b(boleto|nota fiscal|seu pedido|pagamento pendente)\b", re.I)
SAIDA = re.compile(r"responda\s+[\"'“]?sair|n[ãa]o quer(o)? (mais )?receber|descadastr|remover (voc[êe]|seu contato)|parar de receber", re.I)
ORIGEM = re.compile(r"\{\{\s*fonte\s*\}\}|seu contato (est[áa]|veio|apareceu)|encontrei (voc[êe]|seu|a empresa)|vi (no|na|que)", re.I)
CAMPO = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
LINK = re.compile(r"https?://|www\.", re.I)


def _precisa_irma():
    if canspam is None:
        C.saida("bloqueada", excecao="fora_do_ar", motivo="arkos-outbound-eua não encontrada (pasta irmã com canspam.py)",
                como_resolver="instalar a skill arkos-outbound-eua ao lado desta em ~/.claude/skills")
        sys.exit(C.FORA_DO_AR)


def _ler(caminho):
    if not caminho or not os.path.isfile(caminho):
        return ""
    return open(caminho, encoding="utf-8-sig").read()


# Bases que descaracterizam a publicação pelo titular (lista comprada ou enriquecimento de terceiros).
BASE_FORA = ("comprad", "lista paga", "enriquec", "apollo", "lusha", "scrap", "raspad", "clearbit", "snov")


def _pessoal_publicado(l: dict) -> bool:
    """E-mail de domínio pessoal só vale se o próprio titular o publicou como contato do negócio:
    URL em 'publicado_titular' + 'data_publicacao', e a fonte não ser base comprada/enriquecida."""
    url = (l.get("publicado_titular") or "").strip()
    data = (l.get("data_publicacao") or "").strip()
    fonte = (l.get("fonte") or "").lower()
    if not (url and data) or not LINK.search(url):
        return False
    return not any(x in fonte for x in BASE_FORA)


def lote(a):
    _precisa_irma()
    falta = []
    if not os.path.isfile(a.leads):
        falta.append(f"CSV de leads não existe: {a.leads}")
    lia = C.carregar_spec(a.lia) if a.lia and os.path.isfile(a.lia) else {}
    falta += [f"lia.{k} (avaliação de legítimo interesse)" for k in LIA if not str(lia.get(k, "")).strip()]
    if falta:
        C.saida("aguardando", excecao="entrada_incompleta", falta=falta)
        sys.exit(C.ENTRADA_INCOMPLETA)
    leads = canspam._csv(_ler(a.leads))
    if not leads or "email" not in leads[0]:
        C.saida("aguardando", excecao="entrada_incompleta", falta=["coluna email no CSV"])
        sys.exit(C.ENTRADA_INCOMPLETA)
    sup_txt = _ler(a.supressao) or _ler(os.path.join(a.casa or "", "arkos.engine", "supressao.csv"))
    sup = {r.get("email", "").lower() for r in canspam._csv(sup_txt)} if sup_txt.strip() else set()
    sup_dom = {s[1:] for s in sup if s.startswith("@")}
    ok, fora, eua, vistos = [], [], [], set()
    for l in leads:
        em = l["email"].lower()
        usuario, _, dom = em.partition("@")
        pais = (l.get("pais") or "BR").upper()
        motivo = None
        if not canspam.EMAIL_RE.match(em):
            motivo = "e-mail inválido"
        elif em in vistos:
            motivo = "duplicado"
        elif em in sup or dom in sup_dom:
            motivo = "na lista de supressão (pediu para sair; LGPD art. 18)"
        elif not l.get("fonte"):
            motivo = "sem fonte do lead: a LGPD pede informar a origem do dado"
        elif usuario in canspam.ROLE or usuario in ROLE_BR:
            motivo = "endereço de função (contato@, vendas@...): baixa resposta e alto risco de denúncia"
        elif dom in PESSOAL and not _pessoal_publicado(l):
            motivo = ("e-mail pessoal: é pessoa física, o legítimo interesse B2B não cobre. Só entra se o próprio "
                      "titular publicou esse e-mail como contato do negócio (URL em 'publicado_titular' + 'data_publicacao') "
                      "e a base não for comprada nem de enriquecimento")
        elif pais in EUA:
            motivo = "EUA: vai para a arkos-outbound-eua (CAN-SPAM)"
        elif pais in UE:
            motivo = "União Europeia: GDPR com base legal por país; fora desta skill"
        vistos.add(em)
        if motivo and pais in EUA and motivo.startswith("EUA"):
            eua.append({**l, "email": em})
        (fora if motivo else ok).append({**l, "email": em, **({"motivo": motivo} if motivo else {})})
    teto = canspam.teto_dia(a.caixas, a.dia)
    hoje, depois = ok[:teto], ok[teto:]
    pasta = C.pasta_casa(a.casa, a.cliente, a.projeto, "outbound")
    alvo = C.caminho_novo(pasta, "lote", "csv")
    base = alvo[:-4]
    _gravar(alvo, hoje)
    _gravar(base + "-fora.csv", fora)
    if eua:
        _gravar(base + "-para-outbound-eua.csv", eua)
    with open(base + "-lia.json", "w", encoding="utf-8") as f:
        json.dump(lia, f, ensure_ascii=False, indent=1)
    C.saida("ok" if hoje else "reprovado", arquivo=alvo, teto_hoje=teto, regra_teto="rampa da arkos-outbound-eua (heurística ARKOS)",
            contagem={"lidos": len(leads), "hoje": len(hoje), "depois": len(depois), "fora": len(fora), "eua": len(eua)},
            fora=[{"email": f["email"], "motivo": f["motivo"]} for f in fora],
            estado="rascunho: só o arkos-guarda-envio libera o envio")


def _gravar(caminho, linhas):
    campos = []
    for l in linhas:
        campos += [k for k in l if k not in campos]
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos or ["email"])
        w.writeheader()
        w.writerows(linhas)


def _palavras(t):
    return len(re.findall(r"\w+", CAMPO.sub("x", t)))


def avaliar_sequencia(seq):
    probs = []
    toques = seq.get("toques", [])
    if not 3 <= len(toques) <= 5:
        probs.append(f"{len(toques)} toques (use de 3 a 5)")
    dias = [t.get("dia", 0) for t in toques]
    if dias != sorted(dias):
        probs.append(f"dias {dias}: fora de ordem")
    if len(dias) >= 2 and not 7 <= dias[1] - dias[0] <= 14:
        probs.append(f"2º toque no dia {dias[1]} (intervalo {dias[1] - dias[0]}): o 2º e-mail vem 7 a 14 dias depois do 1º")
    if dias and not 21 <= dias[-1] <= 35:
        probs.append(f"último toque no dia {dias[-1]}: a sequência dura de 3 a 5 semanas (termina entre o dia 21 e o 35)")
    rem = seq.get("remetente", {})
    for k in ("nome", "empresa"):
        if not rem.get(k):
            probs.append(f"remetente.{k} vazio: quem envia tem que se identificar")
    campos_ok = set(seq.get("campos", [])) | {"nome", "empresa", "fonte"}
    for n, t in enumerate(toques, 1):
        canal = t.get("canal", "email")
        corpo = t.get("corpo", "")
        if canal == "whatsapp" and not seq.get("opt_in_whatsapp"):
            probs.append(f"toque {n}: WhatsApp sem opt-in registrado (regra do arkos-guarda-envio: só com opt-in e janela de 24 h)")
        if canal == "email":
            assunto = t.get("assunto", "")
            if not assunto or len(assunto) > 50:
                probs.append(f"toque {n}: assunto vazio ou com mais de 50 caracteres")
            if ASSUNTO_FALSO.search(assunto):
                probs.append(f"toque {n}: assunto engana (Re:/Enc:/boleto/pedido)")
            if assunto.isupper() or "!!" in assunto:
                probs.append(f"toque {n}: assunto em caixa alta ou com !!")
        pal = _palavras(corpo)
        if n == 1:
            if pal > 90:
                probs.append(f"toque 1: {pal} palavras (acima de 90 reprova; 25 a 75 é o ótimo, 76 a 90 aceitável)")
            elif pal > 75:
                probs.append(f"toque 1: {pal} palavras aceitável, mas o ótimo é de 25 a 75 (aviso)")
            elif pal < 25:
                probs.append(f"toque 1: {pal} palavras (curto demais; o ótimo é de 25 a 75)")
        elif pal > 90:
            probs.append(f"toque {n}: {pal} palavras (follow-up no máximo 90)")
        if n == 1:
            if corpo.count("?") != 1:
                probs.append("toque 1: tem que ter exatamente uma pergunta")
            if LINK.search(corpo):
                probs.append("toque 1: sem link no primeiro e-mail")
            if not ORIGEM.search(corpo):
                probs.append("toque 1: dizer de onde veio o contato ({{fonte}}): transparência da LGPD")
        if not SAIDA.search(corpo):
            probs.append(f"toque {n}: falta a saída fácil (ex.: 'se não quiser mais receber, responda SAIR')")
        usados = set(CAMPO.findall(corpo + t.get("assunto", "")))
        desconhecidos = usados - campos_ok
        if desconhecidos:
            probs.append(f"toque {n}: campo(s) sem origem {sorted(desconhecidos)} (declare em 'campos' e traga no CSV)")
        if n == 1 and not (usados - {"nome"}):
            probs.append("toque 1: personalização real além do {{nome}} (ex.: {{gancho}} sobre a empresa)")
    return probs


def conferir(a):
    if not os.path.isfile(a.sequencia):
        C.saida("aguardando", excecao="entrada_incompleta", falta=[f"arquivo não existe: {a.sequencia}"])
        sys.exit(C.ENTRADA_INCOMPLETA)
    seq = C.carregar_spec(a.sequencia)
    if str(seq.get("mercado", "BR")).upper() in EUA:
        C.saida("delegar", skill="arkos-outbound-eua", motivo="mercado EUA: CAN-SPAM, inglês e endereço postal")
        sys.exit(0)
    C.exigir(seq, ["remetente", "toques"], "sequência")
    probs = avaliar_sequencia(seq)
    C.saida("verde" if not probs else "vermelho", toques=len(seq["toques"]), problemas=probs)
    sys.exit(0 if not probs else 1)


def montar(a):
    seq = C.carregar_spec(a.sequencia)
    probs = avaliar_sequencia(seq)
    if probs:
        C.saida("vermelho", motivo="a sequência não passou no conferir", problemas=probs)
        sys.exit(1)
    leads = list(csv.DictReader(open(a.lote, encoding="utf-8-sig")))
    linhas, pend = [], []
    for l in leads:
        for n, t in enumerate(seq["toques"], 1):
            def troca(m):
                v = l.get(m.group(1), "")
                return v if v else m.group(0)
            assunto = CAMPO.sub(troca, t.get("assunto", ""))
            corpo = CAMPO.sub(troca, t.get("corpo", "")).replace("{{remetente}}", seq["remetente"]["nome"])
            sobra = CAMPO.findall(assunto + corpo)
            if sobra:
                pend.append({"email": l["email"], "toque": n, "faltando": sorted(set(sobra))})
                continue
            linhas.append({"email": l["email"], "toque": n, "dia": t.get("dia", 0), "canal": t.get("canal", "email"),
                           "assunto": assunto, "corpo": corpo, "estado": "rascunho"})
    pasta = C.pasta_casa(a.casa, a.cliente, a.projeto, "outbound")
    alvo = C.caminho_novo(pasta, "rascunhos", "csv")
    _gravar(alvo, linhas)
    C.saida("ok" if not pend else "amarelo", arquivo=alvo, rascunhos=len(linhas), pendentes=pend,
            proximo="arkos-guarda-envio: aprovar o lote; esta skill não envia")


def dns(a):
    def txt(nome):
        r = C.rodar_oculto(["nslookup", "-type=TXT", nome], timeout=20)
        return r.stdout
    try:
        spf = [l for l in txt(a.dominio).splitlines() if "v=spf1" in l]
        dmarc_raw = txt("_dmarc." + a.dominio)
    except Exception as e:  # noqa: BLE001
        C.saida("bloqueada", excecao="fora_do_ar", motivo=f"nslookup falhou: {e}")
        sys.exit(C.FORA_DO_AR)
    dmarc = [l for l in dmarc_raw.splitlines() if "v=DMARC1" in l]
    probs = ([] if spf else ["sem SPF (v=spf1)"]) + ([] if dmarc else ["sem DMARC em _dmarc." + a.dominio])
    C.saida("verde" if not probs else "vermelho", dominio=a.dominio, spf=[s.strip() for s in spf],
            dmarc=[d.strip() for d in dmarc], problemas=probs,
            nota="DKIM depende do seletor da ferramenta de envio; conferir no painel dela")
    sys.exit(0 if not probs else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    lo = sub.add_parser("lote")
    lo.add_argument("leads")
    lo.add_argument("--lia")
    lo.add_argument("--supressao")
    lo.add_argument("--caixas", type=int, default=1)
    lo.add_argument("--dia", type=int, default=1)
    co = sub.add_parser("conferir")
    co.add_argument("sequencia")
    mo = sub.add_parser("montar")
    mo.add_argument("sequencia")
    mo.add_argument("lote")
    for p in (lo, mo):
        p.add_argument("--casa")
        p.add_argument("--cliente")
        p.add_argument("--projeto")
    sub.add_parser("dns").add_argument("dominio")
    a = ap.parse_args()
    {"lote": lote, "conferir": conferir, "montar": montar, "dns": dns}[a.cmd](a)


if __name__ == "__main__":
    main()
