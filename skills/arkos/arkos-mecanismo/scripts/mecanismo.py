"""mecanismo.py - pontua candidatos a mecanismo único e confere promessas arriscadas.

O Claude escreve os candidatos e dá a nota de 1 a 5 em cada critério, com uma linha de justificativa.
A conta, o ranking, os vetos e a checagem de promessa são deste script (nunca do modelo).

Entrada (JSON): {"mercado": "BR|EUA|EU", "candidatos": [{"nome": "...", "como_funciona": "...",
  "causa": "por que o problema existe (o vilão)", "prova": "demo, dado, caso, estudo" ou "",
  "promessa": "...", "notas": {"dor": 4, "novidade": 3, "credibilidade": 4, "especificidade": 5, "provabilidade": 3},
  "justificativas": {"dor": "...", ...}}]}

Uso:
  python mecanismo.py pontuar candidatos.json [--out mecanismo-pontos.json] [--minimo 3.5]
  python mecanismo.py pronto mecanismo.md mecanismo-pontos.json
Saída 0 = ok · 1 = pronto reprovado ou nenhum candidato passou (resultado_ruim) · 2 = entrada incompleta.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

PESOS = {"dor": 0.25, "credibilidade": 0.25, "novidade": 0.20, "especificidade": 0.15, "provabilidade": 0.15}
MINIMO = 3.5  # nota ponderada mínima para virar "o mecanismo" (heurística ARKOS)

# Promessas que a ARKOS não publica (CDC art. 37 e CONAR no BR; FTC Act §5 nos EUA; UCPD na UE).
PROIBIDAS = [r"\bcura\b", r"\bcurar\b", r"garantid[oa]s?\b", r"\b100\s?% (?:garantid|eficaz|seguro)", r"sem esforco",
             r"\bmilagr", r"renda garantida", r"fique rico", r"enriqueca", r"nunca mais", r"\bdefinitiv[oa]\b",
             r"guaranteed", r"\bcure[sd]?\b", r"get rich", r"risk[- ]free", r"effortless", r"miracle"]
# Podem aparecer só com prova citada no campo "prova".
EXIGEM_PROVA = [r"comprovad", r"cientific", r"clinic", r"\d+\s?%", r"\d+x\b", r"em \d+ dias", r"\bnumero 1\b",
                r"\bo melhor\b", r"proven", r"clinically", r"scientifically", r"#1\b", r"in \d+ days"]
SECOES = ["## Mecanismo escolhido", "## Como funciona", "## Por que o problema existe", "## Prova",
          "## Nome", "## Candidatos", "## O que eu faria nesta semana", "## O que pode matar isto"]


def _norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def checar_promessa(texto: str, prova: str) -> dict:
    t = _norm(texto)
    proibidas = sorted({m.group(0) for p in PROIBIDAS for m in re.finditer(p, t)})
    sem_prova = [] if prova.strip() else sorted({m.group(0) for p in EXIGEM_PROVA for m in re.finditer(p, t)})
    return {"proibidas": proibidas, "exigem_prova": sem_prova}


def pontuar(dados: dict, minimo: float = MINIMO) -> dict:
    cands = dados.get("candidatos") or []
    if len(cands) < 3:
        return {"status": "entrada_incompleta", "faltando": [f"pelo menos 3 candidatos (veio {len(cands)})"]}
    falt, saida = [], []
    for c in cands:
        notas = c.get("notas") or {}
        ruins = [k for k in PESOS if not isinstance(notas.get(k), (int, float)) or not 1 <= notas[k] <= 5]
        sem_just = [k for k in PESOS if not (c.get("justificativas") or {}).get(k)]
        if ruins or sem_just or not c.get("nome") or not c.get("como_funciona"):
            falt.append({"candidato": c.get("nome", "?"), "notas_invalidas": ruins, "sem_justificativa": sem_just})
            continue
        nota = round(sum(notas[k] * p for k, p in PESOS.items()), 2)
        texto = " ".join(str(c.get(k, "")) for k in ("nome", "como_funciona", "promessa"))
        promessa = checar_promessa(texto, c.get("prova", ""))
        vetos = []
        if not c.get("prova", "").strip():
            vetos.append("sem prova: só pode virar mecanismo depois do teste de prova")
        if not c.get("causa", "").strip():
            vetos.append("sem causa (vilão): o mecanismo não explica por que o problema existe")
        if promessa["proibidas"]:
            vetos.append(f"promessa proibida: {', '.join(promessa['proibidas'])}")
        if promessa["exigem_prova"]:
            vetos.append(f"afirmação que exige prova: {', '.join(promessa['exigem_prova'])}")
        saida.append({"nome": c["nome"], "nota": nota, "notas": notas, "vetos": vetos, "promessa": promessa,
                      "elegivel": nota >= minimo and not vetos})
    if falt:
        return {"status": "entrada_incompleta", "faltando": falt}
    saida.sort(key=lambda x: (x["elegivel"], x["nota"]), reverse=True)
    escolhido = saida[0] if saida[0]["elegivel"] else None
    return {"status": "ok" if escolhido else "resultado_ruim", "minimo": minimo, "pesos": PESOS,
            "escolhido": escolhido and escolhido["nome"], "candidatos": saida,
            "proximo": None if escolhido else "voltar ao passo 3 (mais candidatos) ou rodar o teste de prova do melhor"}


def pronto(md: str, pontos: dict) -> list[str]:
    erros = [f"falta a seção '{s}'" for s in SECOES if s not in md]
    if pontos.get("status") != "ok":
        erros.append(f"pontuação com status {pontos.get('status')}")
    elif pontos["escolhido"] not in md:
        erros.append("o mecanismo do .md não é o escolhido pelo script")
    achado = checar_promessa(md.split("## Candidatos")[0], "x")["proibidas"]
    if achado:
        erros.append(f"promessa proibida no texto final: {', '.join(achado)}")
    return erros


def _main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("pontuar", "pronto"):
        print(__doc__)
        return 2
    if argv[0] == "pronto":
        erros = pronto(Path(argv[1]).read_text(encoding="utf-8"), json.loads(Path(argv[2]).read_text(encoding="utf-8")))
        print(json.dumps({"pronto": not erros, "erros": erros}, ensure_ascii=False, indent=2))
        return 0 if not erros else 1
    minimo = float(argv[argv.index("--minimo") + 1]) if "--minimo" in argv else MINIMO
    r = pontuar(json.loads(Path(argv[1]).read_text(encoding="utf-8")), minimo)
    txt = json.dumps(r, ensure_ascii=False, indent=2)
    if "--out" in argv:
        p = Path(argv[argv.index("--out") + 1])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    print(txt)
    return {"ok": 0, "resultado_ruim": 1}.get(r["status"], 2)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
