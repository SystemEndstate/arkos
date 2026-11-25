#!/usr/bin/env python3
"""arkos-vps: operar VPS do cliente (status/logs livres; deploy so com confirmacao
E aprovacao_id da guarda-escrita). Sala limpa: SSH (OpenSSH) ou API tRPC do
Easypanel, com credencial do cliente. Somente stdlib.

Seguranca: `servico` e validado (allowlist de caracteres) e passa por shlex.quote
antes de virar comando remoto; nada de string de shell montada com entrada crua.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
SERVICO_OK = re.compile(r"^[A-Za-z0-9_.-]+$")
# endpoint tRPC documentado do Easypanel (nao o /api/deploy, que nao existe)
EASYPANEL_DEPLOY_PROC = "services.app.deployService"


def servico_valido(servico):
    return bool(servico) and bool(SERVICO_OK.match(servico))


def ssh_cmd(host, user, chave, remoto):
    """argv (lista), nunca shell string. `remoto` ja deve vir com o alvo citado."""
    base = ["ssh"]
    if chave:
        base += ["-i", chave]
    base += ["-o", "StrictHostKeyChecking=accept-new", f"{user}@{host}", remoto]
    return base


def status(host, user, chave, servico):
    if servico and not servico_valido(servico):
        return {"acao": "status", "erro": "servico invalido", "muda_estado": False}
    remoto = f"systemctl is-active {shlex.quote(servico)}" if servico else "uptime"
    return {"acao": "status", "cmd": ssh_cmd(host, user, chave, remoto),
            "janela": "oculta" if os.name == "nt" else "n/a", "muda_estado": False}


def logs(host, user, chave, servico, n=100):
    if servico and not servico_valido(servico):
        return {"acao": "logs", "erro": "servico invalido", "muda_estado": False}
    n = int(n)
    if servico:
        remoto = f"journalctl -u {shlex.quote(servico)} -n {n} --no-pager"
    else:
        remoto = f"tail -n {n} /var/log/syslog"
    return {"acao": "logs", "cmd": ssh_cmd(host, user, chave, remoto), "muda_estado": False}


def easypanel_deploy(base_url, projeto, servico, api_key_presente):
    # tRPC: POST {base}/api/trpc/{proc}; corpo com project+service no json do input
    return {"metodo": "POST",
            "url": f"{base_url.rstrip('/')}/api/trpc/{EASYPANEL_DEPLOY_PROC}",
            "corpo": {"json": {"projectName": projeto, "serviceName": servico}},
            "header": {"Authorization": "Bearer [API_KEY]" if api_key_presente else None}}


def deploy(host, user, chave, servico, imagem, rollback, confirmar=False,
           aprovacao_id=None, projeto=None, easypanel=None):
    if not servico_valido(servico):
        return {"acao": "deploy", "confirmado": False, "muda_estado": True,
                "motivo": "servico invalido (so [A-Za-z0-9_.-])"}
    if not confirmar:
        return {"acao": "deploy", "confirmado": False, "muda_estado": True,
                "o_que_faria": {"servico": servico, "imagem": imagem,
                                "easypanel": bool(easypanel)},
                "rollback": rollback or "REGISTRAR o deploy/commit anterior antes",
                "motivo": "deploy exige --confirmar"}
    if not aprovacao_id:
        return {"acao": "deploy", "confirmado": False, "muda_estado": True,
                "motivo": "deploy exige aprovacao_id da arkos-guarda-escrita"}
    if not rollback:
        return {"acao": "deploy", "confirmado": False, "muda_estado": True,
                "motivo": "sem plano de rollback registrado"}
    if easypanel:
        destino = easypanel_deploy(easypanel, projeto or servico, servico, True)
    else:
        remoto = (f"cd /srv/{shlex.quote(servico)} && "
                  "docker compose up -d --pull always")
        destino = {"cmd": ssh_cmd(host, user, chave, remoto)}
    return {"acao": "deploy", "confirmado": True, "muda_estado": True,
            "trava": "arkos-guarda-escrita", "aprovacao_id": aprovacao_id,
            "rollback": rollback, "destino": destino}


def _run(cmd, timeout=60):
    kw = {"capture_output": True, "text": True, "timeout": timeout}
    if os.name == "nt":
        kw["creationflags"] = CREATE_NO_WINDOW
    return subprocess.run(cmd, **kw)


def executar_leitura(plano):
    """Roda de fato um plano de status/logs (so leitura)."""
    if "erro" in plano or "cmd" not in plano:
        return plano
    try:
        p = _run(plano["cmd"])
        plano["saida"] = p.stdout[-2000:]
        plano["returncode"] = p.returncode
    except (OSError, subprocess.SubprocessError) as e:
        plano["erro_exec"] = str(e)
    return plano


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vps")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nome in ("status", "logs"):
        c = sub.add_parser(nome)
        c.add_argument("--host", required=True)
        c.add_argument("--user", default="root")
        c.add_argument("--chave", default=None)
        c.add_argument("--servico", default=None)
        c.add_argument("--run", action="store_true", help="executa de fato (default: so monta)")
        if nome == "logs":
            c.add_argument("-n", type=int, default=100)
    d = sub.add_parser("deploy")
    d.add_argument("--host", default=None)
    d.add_argument("--user", default="root")
    d.add_argument("--chave", default=None)
    d.add_argument("--servico", required=True)
    d.add_argument("--projeto", default=None)
    d.add_argument("--imagem", default=None)
    d.add_argument("--rollback", default=None)
    d.add_argument("--aprovacao-id", default=None)
    d.add_argument("--easypanel", default=None)
    d.add_argument("--confirmar", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd in ("status", "logs"):
        plano = (status(args.host, args.user, args.chave, args.servico) if args.cmd == "status"
                 else logs(args.host, args.user, args.chave, args.servico, args.n))
        if getattr(args, "run", False):
            plano = executar_leitura(plano)
        print(json.dumps(plano, ensure_ascii=False))
        return 2 if "erro" in plano else 0
    if args.cmd == "deploy":
        res = deploy(args.host, args.user, args.chave, args.servico, args.imagem,
                     args.rollback, args.confirmar, args.aprovacao_id, args.projeto,
                     args.easypanel)
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res.get("confirmado") else 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
