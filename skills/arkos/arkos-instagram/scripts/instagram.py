#!/usr/bin/env python3
"""arkos-instagram: monta pedidos da Meta Graph API para publicar Reels.

Sala limpa: fala direto com a Graph API (metodo publico), com o token do cliente.
NAO publica: so monta o pedido travado (quem envia e o arkos-guarda-envio).
Somente stdlib.
"""
import argparse
import json
import os
import re
import sys

API = "https://graph.facebook.com/v21.0"
MAX_CAPTION = 2200
MAX_HASHTAGS = 30


def carregar_credenciais():
    return {
        "ig_user_id": os.environ.get("ARKOS_IG_USER_ID"),
        "access_token": os.environ.get("ARKOS_IG_TOKEN"),
    }


def validar(media_url, caption):
    erros = []
    if not re.match(r"^https?://", media_url or ""):
        erros.append("media_url precisa ser URL publica http(s)")
    if caption and len(caption) > MAX_CAPTION:
        erros.append(f"legenda {len(caption)} > {MAX_CAPTION}")
    if caption and caption.count("#") > MAX_HASHTAGS:
        erros.append(f"hashtags {caption.count('#')} > {MAX_HASHTAGS}")
    return erros


def preparar(media_url, caption, creds, agendar_em=None):
    erros = validar(media_url, caption)
    if not (creds.get("ig_user_id") and creds.get("access_token")):
        erros.append("sem token do cliente")
    if erros:
        return {"ok": False, "erros": erros, "acao": "recusar", "requisicoes": []}
    ig = creds["ig_user_id"]
    reqs = [
        {"metodo": "POST", "url": f"{API}/{ig}/media",
         "campos": {"media_type": "REELS", "video_url": media_url,
                    "caption": caption, "access_token": "[TOKEN]"}},
        {"metodo": "POST", "url": f"{API}/{ig}/media_publish",
         "campos": {"creation_id": "<do passo 1>", "access_token": "[TOKEN]"}},
    ]
    return {
        "ok": True,
        "conta": ig,
        "tipo": "REELS",
        "aviso": f"Vai publicar REELS na conta IG {ig}. Confirme a conta. "
                 "Cota de publicacao da API: 50/24h. Token e do cliente.",
        "agendado": agendar_em,
        "requisicoes": reqs,
        "trava": "arkos-guarda-envio",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(prog="instagram")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preparar")
    p.add_argument("--media-url", required=True)
    p.add_argument("--caption", default="")
    p.add_argument("--agendar-em", default=None)
    args = ap.parse_args(argv)
    if args.cmd == "preparar":
        res = preparar(args.media_url, args.caption, carregar_credenciais(), args.agendar_em)
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res["ok"] else 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
