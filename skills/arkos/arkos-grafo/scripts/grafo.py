#!/usr/bin/env python3
"""arkos-grafo: casca sobre o CLI publico `graphify` (pacote graphifyy, MIT).

Nao reimplementa o grafo: monta e roda o comando do graphify com janela oculta
no Windows, detecta ausencia e orienta a instalacao. Somente stdlib.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
INSTRUCAO_INSTALL = "uv tool install graphifyy"


def _run(cmd, timeout=30):
    kw = {"capture_output": True, "text": True, "timeout": timeout}
    if os.name == "nt":
        kw["creationflags"] = CREATE_NO_WINDOW  # janela oculta (regra da casa)
    return subprocess.run(cmd, **kw)


def disponivel():
    return shutil.which("graphify") is not None


# acoes que gastam LLM (build semantico completo) -> exigem aviso de custo
ACOES_COM_CUSTO = {"extract"}


def build_cmd(acao, alvo=None, a=None, b=None):
    """Monta o comando graphify real (conferido com `graphify --help`). Nao executa.

    build completo = `graphify extract <path>` (AST + LLM, custa). `update` e AST
    puro (sem LLM). `graphify .` (usado antes) NAO existe no CLI.
    """
    if acao in ("extract", "graph", "build"):
        return ["graphify", "extract", alvo or "."]
    if acao == "update":
        return ["graphify", "update", alvo or "."]
    if acao == "query":
        return ["graphify", "query", alvo or ""]
    if acao == "explain":
        return ["graphify", "explain", alvo or ""]
    if acao == "affected":
        return ["graphify", "affected", alvo or ""]
    if acao == "path":
        return ["graphify", "path", a or "", b or ""]
    raise ValueError("acao desconhecida: " + str(acao))


def check():
    if not disponivel():
        return {"ok": False, "instrucao": INSTRUCAO_INSTALL,
                "motivo": "graphify nao encontrado no PATH"}
    try:
        p = _run(["graphify", "--version"])
        return {"ok": p.returncode == 0, "versao": (p.stdout or p.stderr).strip()}
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "instrucao": INSTRUCAO_INSTALL, "motivo": str(e)}


def executar(acao, alvo=None, a=None, b=None, dry_run=False):
    cmd = build_cmd(acao, alvo, a, b)
    custo = acao in ("extract", "graph", "build")
    aviso = ("`graphify extract` usa LLM e custa: confirme antes." if custo else None)
    if dry_run:
        out = {"cmd": cmd, "janela": "oculta" if os.name == "nt" else "n/a", "dry_run": True}
        if aviso:
            out["aviso_custo"] = aviso
        return out
    if custo:
        # build semantico nao roda sem OK (regra de custo do Jev/decisor)
        return {"cmd": cmd, "precisa_confirmar_custo": True, "aviso_custo": aviso}
    if not disponivel():
        return {"erro": "graphify ausente", "instrucao": INSTRUCAO_INSTALL}
    try:
        p = _run(cmd, timeout=600)
        return {"cmd": cmd, "returncode": p.returncode,
                "stdout": p.stdout, "stderr": p.stderr[-500:]}
    except subprocess.SubprocessError as e:
        return {"erro": str(e), "cmd": cmd}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="grafo")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    bc = sub.add_parser("build-cmd")
    bc.add_argument("acao", choices=["graph", "update", "query", "explain", "path"])
    bc.add_argument("--alvo", default=".")
    bc.add_argument("--a")
    bc.add_argument("--b")
    bc.add_argument("--dry-run", action="store_true", default=True)
    rn = sub.add_parser("run")
    rn.add_argument("acao", choices=["graph", "update", "query", "explain", "path"])
    rn.add_argument("--alvo", default=".")
    rn.add_argument("--a")
    rn.add_argument("--b")
    args = ap.parse_args(argv)

    if args.cmd == "check":
        print(json.dumps(check(), ensure_ascii=False))
        return 0
    if args.cmd == "build-cmd":
        print(json.dumps(executar(args.acao, args.alvo, args.a, args.b, dry_run=True),
                         ensure_ascii=False))
        return 0
    if args.cmd == "run":
        print(json.dumps(executar(args.acao, args.alvo, args.a, args.b), ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
