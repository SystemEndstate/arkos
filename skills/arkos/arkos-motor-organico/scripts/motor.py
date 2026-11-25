"""motor.py - calendário de conteúdo orgânico ligado aos fluxos da ARKOS e leitura do que funcionou.

Todo post nasce com etapa do funil (topo, meio, fundo) e um CTA que aponta para um FLUXO da ARKOS
(ex.: fundo -> agente-sdr; meio -> site-landing/isca; topo -> seguir/salvar). Post sem fluxo não entra.

Entrada do calendário (JSON):
  {"inicio": "2026-12-01", "semanas": 4, "posts_semana": 4, "dias": ["seg","qua","sex","sab"],
   "pilares": [{"nome": "bastidores", "peso": 2}, ...],
   "formatos": ["reels", "carrossel", "stories"], "plataformas": ["instagram", "tiktok"],
   "mix": {"topo": 0.6, "meio": 0.3, "fundo": 0.1},
   "fluxos": {"topo": {"cta": "salva e segue", "fluxo": "conteudo-organico"},
              "meio": {"cta": "comenta GUIA e recebe o checklist", "fluxo": "site-landing"},
              "fundo": {"cta": "chama no direct para orçamento", "fluxo": "agente-sdr"}}}

Uso:
  python motor.py calendario plano.json [--out calendario.csv] [--json calendario.json]
  python motor.py ler metricas.csv [--top 0.2] [--out leitura.json]
  python motor.py pronto calendario.json
Saída 0 = ok · 1 = pronto reprovado · 2 = entrada incompleta.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import re
import sys
import unicodedata
from pathlib import Path

ETAPAS = ("topo", "meio", "fundo")
DIAS = {"seg": 0, "ter": 1, "qua": 2, "qui": 3, "sex": 4, "sab": 5, "dom": 6}
MAX_FUNDO = 0.25  # heurística ARKOS: perfil que só vende para de crescer


def _cotas(total: int, pesos: dict) -> dict:
    """Maior resto: distribui `total` pelos pesos sem sobrar nem faltar."""
    soma = sum(pesos.values())
    brutos = {k: total * v / soma for k, v in pesos.items()}
    base = {k: int(v) for k, v in brutos.items()}
    for k in sorted(brutos, key=lambda k: brutos[k] - base[k], reverse=True)[: total - sum(base.values())]:
        base[k] += 1
    return base


def _intercalar(cotas: dict) -> list:
    """Espalha os itens (ex.: 6 topo, 3 meio, 1 fundo) para não juntar iguais em sequência."""
    total = sum(cotas.values())
    pos = []
    for k, n in cotas.items():
        pos += [((i + 0.5) / n, k) for i in range(n)] if n else []
    return [k for _, k in sorted(pos)][:total]


def calendario(p: dict) -> dict:
    falt = [k for k in ("inicio", "semanas", "posts_semana", "pilares", "formatos", "mix", "fluxos") if not p.get(k)]
    if falt:
        return {"status": "entrada_incompleta", "faltando": falt}
    sem_fluxo = [e for e in ETAPAS if p["mix"].get(e, 0) > 0 and not (p["fluxos"].get(e) or {}).get("fluxo")]
    if sem_fluxo:
        return {"status": "entrada_incompleta", "faltando": [f"fluxo do CTA da etapa {e}" for e in sem_fluxo],
                "regra": "post sem fluxo ligado não entra no calendário"}
    if p["mix"].get("fundo", 0) / sum(p["mix"].values()) > MAX_FUNDO:
        return {"status": "entrada_incompleta", "faltando": [f"mix de fundo acima de {MAX_FUNDO:.0%} (heurística)"]}
    dias = [DIAS[d] for d in p.get("dias", ["seg", "qua", "sex", "sab"])][: p["posts_semana"]]
    inicio = dt.date.fromisoformat(p["inicio"])
    segunda = inicio - dt.timedelta(days=inicio.weekday())
    datas = sorted(segunda + dt.timedelta(weeks=s, days=d) for s in range(p["semanas"]) for d in dias)
    datas = [d for d in datas if d >= inicio]
    n = len(datas)
    etapas = _intercalar(_cotas(n, {e: p["mix"].get(e, 0) for e in ETAPAS if p["mix"].get(e, 0) > 0}))
    pilares = _intercalar(_cotas(n, {x["nome"]: x.get("peso", 1) for x in p["pilares"]}))
    plats = p.get("plataformas") or ["instagram"]
    posts = []
    for i, d in enumerate(datas):
        e = etapas[i]
        posts.append({"n": i + 1, "data": d.isoformat(), "semana": (d - segunda).days // 7 + 1,
                      "plataforma": plats[i % len(plats)], "formato": p["formatos"][i % len(p["formatos"])],
                      "pilar": pilares[i], "etapa": e, "cta": p["fluxos"][e]["cta"], "fluxo": p["fluxos"][e]["fluxo"],
                      "gancho": "", "roteiro": "", "status": "rascunho"})
    return {"status": "ok", "posts": posts, "contagem": {
        "etapa": {e: sum(1 for x in posts if x["etapa"] == e) for e in ETAPAS},
        "pilar": {k: sum(1 for x in posts if x["pilar"] == k) for k in dict.fromkeys(pilares)}}}


def pronto(cal: dict) -> list[str]:
    if cal.get("status") != "ok":
        return [f"status {cal.get('status')}"]
    erros = []
    for x in cal["posts"]:
        if not x.get("fluxo") or not x.get("cta"):
            erros.append(f"post {x['n']}: sem CTA ligado a fluxo")
        if not x.get("gancho", "").strip():
            erros.append(f"post {x['n']}: sem gancho escrito")
        if x.get("formato") in ("reels", "tiktok", "shorts", "video") and not x.get("roteiro", "").strip():
            erros.append(f"post {x['n']}: vídeo sem roteiro")
    fundo = sum(1 for x in cal["posts"] if x["etapa"] == "fundo") / max(1, len(cal["posts"]))
    if fundo > MAX_FUNDO:
        erros.append(f"fundo em {fundo:.0%} (máx. {MAX_FUNDO:.0%})")
    seq = [x["pilar"] for x in cal["posts"]]
    if any(seq[i] == seq[i + 1] == seq[i + 2] for i in range(len(seq) - 2)):
        erros.append("3 posts seguidos do mesmo pilar")
    return erros


def _n(v) -> float:
    s = re.sub(r"[^\d,.\-]", "", str(v or ""))
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _k(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()).strip("_")


COLS = {"post": ["post", "id", "link", "titulo", "legenda"], "alcance": ["alcance", "reach", "contas_alcancadas"],
        "curtidas": ["curtidas", "likes"], "comentarios": ["comentarios", "comments"],
        "salvos": ["salvos", "salvamentos", "saves"], "compart": ["compartilhamentos", "shares", "envios"],
        "seguidores": ["seguidores_ganhos", "follows", "novos_seguidores", "seguidores"],
        "formato": ["formato", "tipo", "type"], "pilar": ["pilar"]}


def ler(texto: str, top: float = 0.2) -> dict:
    texto = texto.lstrip("﻿")
    delim = ";" if texto[:2048].count(";") > texto[:2048].count(",") else ","
    linhas = list(csv.DictReader(io.StringIO(texto), delimiter=delim))
    if not linhas:
        return {"status": "entrada_incompleta", "faltando": ["linhas"]}
    chaves = {_k(c): c for c in linhas[0]}
    col = {k: next((chaves[a] for a in al if a in chaves), None) for k, al in COLS.items()}
    falt = [k for k in ("post", "alcance") if not col[k]]
    if falt:
        return {"status": "entrada_incompleta", "faltando": falt, "colunas": list(linhas[0])}
    posts = []
    for r in linhas:
        g = lambda k: _n(r.get(col[k])) if col[k] else 0.0
        alc = g("alcance")
        if not alc:
            continue
        inter = g("curtidas") + g("comentarios") + g("salvos") + g("compart")
        posts.append({"post": r[col["post"]], "formato": r.get(col["formato"] or "", ""), "pilar": r.get(col["pilar"] or "", ""),
                      "alcance": alc, "engajamento": round(inter / alc, 4),
                      "salvos_compart": round((g("salvos") + g("compart")) / alc, 4),
                      "seguidores_por_mil": round(g("seguidores") / alc * 1000, 2)})
    if len(posts) < 5:
        return {"status": "entrada_incompleta", "faltando": [f"pelo menos 5 posts com alcance (veio {len(posts)})"]}
    # nota: salvos+compartilhamentos pesam mais que curtida (sinal de valor e de alcance novo)
    for x in posts:
        x["nota"] = round(0.5 * x["salvos_compart"] + 0.3 * x["engajamento"] + 0.2 * x["seguidores_por_mil"] / 1000, 5)
    posts.sort(key=lambda x: x["nota"], reverse=True)
    k = max(1, round(len(posts) * top))
    for i, x in enumerate(posts):
        x["classe"] = "vencedor" if i < k else ("fraco" if i >= len(posts) - k else "medio")
    venc = [x for x in posts if x["classe"] == "vencedor"]
    return {"status": "ok", "posts": posts, "vencedores": [x["post"] for x in venc],
            "proximos": [f"'{x['post']}': repetir o ângulo em outro formato e levar ao lote-criativos (Spark Ads/impulsionar)" for x in venc],
            "por_pilar": {p: round(sum(x["nota"] for x in posts if x["pilar"] == p) / sum(1 for x in posts if x["pilar"] == p), 5)
                          for p in {x["pilar"] for x in posts if x["pilar"]}}}


def _main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("calendario", "ler", "pronto"):
        print(__doc__)
        return 2
    arq = Path(argv[1]).read_text(encoding="utf-8-sig")
    if argv[0] == "pronto":
        erros = pronto(json.loads(arq))
        print(json.dumps({"pronto": not erros, "erros": erros}, ensure_ascii=False, indent=2))
        return 0 if not erros else 1
    r = calendario(json.loads(arq)) if argv[0] == "calendario" else ler(arq, float(argv[argv.index("--top") + 1]) if "--top" in argv else 0.2)
    for flag in ("--out", "--json"):
        if flag in argv:
            p = Path(argv[argv.index(flag) + 1])
            p.parent.mkdir(parents=True, exist_ok=True)
            if flag == "--out" and argv[0] == "calendario" and r["status"] == "ok":
                with p.open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=list(r["posts"][0]))
                    w.writeheader()
                    w.writerows(r["posts"])
            else:
                p.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r["status"] == "ok" else 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
