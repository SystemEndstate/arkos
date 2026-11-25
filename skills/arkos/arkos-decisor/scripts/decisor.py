#!/usr/bin/env python3
"""arkos-decisor: decisao fechada barata com limiar (Sistema 1 da ARKOS).

Sala limpa: nao copia codigo/endpoint/formato de ferramenta pessoal de terceiros.
Metodo publico: pedir probabilidades a um provedor OpenAI-compativel e aplicar um
limiar; sem chave ou com falha, devolver o controle ao Claude. Somente stdlib.
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error

CONFIG_PATH = os.path.expanduser("~/.arkos/decisor.json")

# --- redacao de segredos / dado pessoal antes de qualquer envio -------------
_PADROES = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{10,}"), "[CHAVE]"),
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}\-?\d{2}\b"), "[CPF]"),
    (re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}\-?\d{2}\b"), "[CNPJ]"),
    (re.compile(r"\b[A-Za-z0-9]{32,}\b"), "[TOKEN]"),
]


def redigir(texto):
    t = texto or ""
    for rx, rep in _PADROES:
        t = rx.sub(rep, t)
    return t


def carregar_config():
    cfg = {
        "provider": os.environ.get("ARKOS_DECISOR_PROVIDER"),
        "base_url": os.environ.get("ARKOS_DECISOR_BASE_URL"),
        "model": os.environ.get("ARKOS_DECISOR_MODEL"),
        "key": os.environ.get("ARKOS_DECISOR_KEY"),
    }
    if not cfg["key"] and os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                disco = json.load(f)
            for k in cfg:
                cfg[k] = cfg[k] or disco.get(k)
        except (OSError, ValueError):
            pass
    return cfg


def _normalizar(scores, opcoes):
    s = {o: max(0.0, float(scores.get(o, 0.0))) for o in opcoes}
    total = sum(s.values())
    if total <= 0:
        return {o: 1.0 / len(opcoes) for o in opcoes}
    return {o: v / total for o, v in s.items()}


def aplicar_limiar(scores, opcoes, limiar):
    """Regra do limiar. Devolve o dict de saida (sem fazer rede)."""
    if not opcoes or len(opcoes) < 2:
        return {"fonte": "regra", "decidir_com_claude": True,
                "motivo": "opcoes_insuficientes"}
    probs = _normalizar(scores, opcoes)
    ordenado = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    melhor, p1 = ordenado[0]
    p2 = ordenado[1][1]
    acima = [o for o, p in ordenado if p > limiar]
    if p1 > limiar and (p1 - p2) >= 0.05:
        return {"fonte": "provedor", "escolha": melhor, "prob": round(p1, 4),
                "acima_limiar": acima, "probs": {o: round(p, 4) for o, p in probs.items()}}
    return {"fonte": "provedor", "decidir_com_claude": True,
            "top": [ordenado[0][0], ordenado[1][0]], "motivo": "abaixo_do_limiar",
            "probs": {o: round(p, 4) for o, p in probs.items()}}


def _chamar_provedor(cfg, pergunta, opcoes, texto, timeout=12):
    """POST OpenAI-compativel. Devolve dict de scores ou levanta excecao."""
    prompt = (
        "Voce classifica uma decisao fechada. Responda SO um JSON com uma "
        "probabilidade (0 a 1) por opcao, somando ~1.\n"
        f"Pergunta: {pergunta}\nOpcoes: {opcoes}\nCaso: {redigir(texto)}\n"
        'Formato: {"probs": {"<opcao>": <0..1>, ...}}'
    )
    body = json.dumps({
        "model": cfg["model"] or "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": "Bearer " + cfg["key"],
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (url do config do prestador)
        data = json.loads(resp.read().decode("utf-8"))
    conteudo = data["choices"][0]["message"]["content"]
    return json.loads(conteudo).get("probs", {})


def decidir(pergunta, opcoes, texto, limiar=0.6, scores=None, cfg=None):
    if not opcoes or len(opcoes) < 2:
        return {"fonte": "regra", "decidir_com_claude": True,
                "motivo": "opcoes_insuficientes"}
    if scores is not None:
        return aplicar_limiar(scores, opcoes, limiar)
    cfg = cfg or carregar_config()
    if not (cfg.get("key") and cfg.get("base_url")):
        return {"fonte": "fallback", "decidir_com_claude": True, "motivo": "sem chave"}
    for tentativa in range(2):
        try:
            got = _chamar_provedor(cfg, pergunta, opcoes, texto)
            return aplicar_limiar(got, opcoes, limiar)
        except (urllib.error.URLError, ValueError, KeyError, TimeoutError):
            if tentativa == 1:
                return {"fonte": "fallback", "decidir_com_claude": True,
                        "motivo": "provedor"}
    return {"fonte": "fallback", "decidir_com_claude": True, "motivo": "provedor"}


def _parse_scores(s):
    if not s:
        return None
    out = {}
    for par in s.split(","):
        k, _, v = par.partition(":")
        out[k.strip()] = float(v)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="decisor")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decide")
    d.add_argument("--pergunta", required=True)
    d.add_argument("--opcoes", required=True, help="a,b,c")
    d.add_argument("--texto", default="")
    d.add_argument("--limiar", type=float, default=0.6)
    d.add_argument("--scores", help="hook de teste/local: a:0.7,b:0.3")
    dl = sub.add_parser("decide-lote")
    dl.add_argument("--arquivo", required=True, help="JSON: [{pergunta,opcoes,texto}]")
    dl.add_argument("--limiar", type=float, default=0.6)
    args = ap.parse_args(argv)

    if args.cmd == "decide":
        opc = [o.strip() for o in args.opcoes.split(",") if o.strip()]
        res = decidir(args.pergunta, opc, args.texto, args.limiar,
                      scores=_parse_scores(args.scores))
        print(json.dumps(res, ensure_ascii=False))
        return 0
    if args.cmd == "decide-lote":
        with open(args.arquivo, encoding="utf-8") as f:
            itens = json.load(f)
        saida, para_claude = [], 0
        for it in itens:
            r = decidir(it["pergunta"], it.get("opcoes", []), it.get("texto", ""),
                        args.limiar, scores=it.get("scores"))
            saida.append(r)
            if r.get("decidir_com_claude"):
                para_claude += 1
        print(json.dumps({"itens": saida,
                          "resumo": {"total": len(itens),
                                     "decididos": len(itens) - para_claude,
                                     "para_claude": para_claude}}, ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
