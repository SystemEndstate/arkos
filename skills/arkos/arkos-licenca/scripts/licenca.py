"""arkos-licenca: emite, verifica e revoga a licença do prestador (papel + clientes + validade), assinada com HMAC-SHA256.

Formato: ARK1.<payload base64url>.<assinatura base64url>
payload = {"lid", "prestador", "papel", "plano", "clientes", "emitida", "expira", "base"}
plano: "vip" (tudo) ou "membro" (sem e-commerce, TikTok Shop, UGC, VSL e advertorial). Sem campo = membro.
O plano vai dentro do payload assinado: trocar "membro" por "vip" invalida a assinatura.

O segredo de assinatura NUNCA fica em arquivo do repositório nem no pacote: vem de ARKOS_LICENCA_SEGREDO
(só na máquina do dono / no servidor da arkos-base). O prestador só guarda a licença (~/.arkos/licenca.txt).

Uso:
  python licenca.py emitir    --prestador ana --papel prestador --plano membro --clientes clinica-a,loja-b --dias 90 [--dono-confirma]
  python licenca.py verificar --licenca ARK1...  [--revogadas revogadas.json] [--cliente X]
  python licenca.py revogar   --lid L --revogadas revogadas.json --motivo "..." [--dono-confirma]
Saída: 0 ok · 2 recusa · 3 exceção tratada · verificar inválida = 401 no JSON e código 4.
"""
import argparse, base64, hashlib, hmac, json, os, re, secrets, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PAPEIS = ("prestador", "revisor", "dono")
PLANOS = ("vip", "membro")


def plano_de(p):
    """Plano efetivo do payload já verificado: só "vip" explícito é vip; ausente ou qualquer outro valor = membro."""
    return "vip" if (p or {}).get("plano") == "vip" else "membro"


def b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def segredo():
    s = os.environ.get("ARKOS_LICENCA_SEGREDO", "")
    if len(s) < 32:
        raise SystemExit("ARKOS_LICENCA_SEGREDO ausente ou curto (mínimo 32 caracteres). Só o dono tem.")
    return s.encode()


def agora():
    return datetime.now(timezone.utc).replace(microsecond=0)


def emitir(prestador, papel, clientes, dias, dono_confirma, base="https://base.arkos.local", plano="membro"):
    if not dono_confirma:
        return None, "recusado: só o dono emite licença (passe --dono-confirma depois de revisar papel e clientes)"
    if papel not in PAPEIS:
        return None, f"papel inválido: {papel} (opções: {', '.join(PAPEIS)})"
    if papel != "dono" and not clientes:
        return None, "licença de prestador/revisor precisa de pelo menos 1 cliente"
    if plano not in PLANOS:
        return None, f"plano inválido: {plano} (opções: {', '.join(PLANOS)})"
    if not 1 <= dias <= 365:
        return None, "validade entre 1 e 365 dias"
    if not all(re.fullmatch(r"[a-z0-9][a-z0-9-]*", c) for c in clientes):
        return None, "cliente precisa ser slug"
    t = agora()
    p = {"lid": secrets.token_hex(8), "prestador": prestador, "papel": papel, "plano": plano, "clientes": sorted(set(clientes)),
         "emitida": t.isoformat(), "expira": (t + timedelta(days=dias)).isoformat(), "base": base}
    corpo = b64(json.dumps(p, separators=(",", ":"), sort_keys=True).encode())
    sig = b64(hmac.new(segredo(), corpo.encode(), hashlib.sha256).digest())
    return f"ARK1.{corpo}.{sig}", p


def verificar(lic, revogadas=None, cliente=None, quando=None):
    """Devolve (ok, motivo, payload). Comparação de assinatura em tempo constante."""
    try:
        pre, corpo, sig = lic.strip().split(".")
        if pre != "ARK1":
            return False, "formato desconhecido", None
        esperado = b64(hmac.new(segredo(), corpo.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(esperado, sig):
            return False, "assinatura inválida (licença alterada ou de outra base)", None
        p = json.loads(unb64(corpo))
    except (ValueError, json.JSONDecodeError):
        return False, "licença malformada", None
    if (quando or agora()) >= datetime.fromisoformat(p["expira"]):
        return False, "licença vencida", p
    if p["lid"] in set(revogadas or []):
        return False, "licença revogada", p
    if cliente and p["papel"] != "dono" and cliente not in p["clientes"]:
        return False, f"cliente {cliente} fora da licença", p
    return True, "ok", p


def ler_revogadas(arq):
    f = Path(arq) if arq else None
    if not f or not f.exists():
        return {}
    return json.loads(f.read_text(encoding="utf-8"))


def revogar(lid, arq, motivo, dono_confirma):
    if not dono_confirma:
        return "recusado: só o dono revoga (passe --dono-confirma)"
    if not motivo:
        return "motivo obrigatório (vai para a auditoria)"
    r = ler_revogadas(arq)
    r[lid] = {"quando": agora().isoformat(), "motivo": motivo}
    Path(arq).parent.mkdir(parents=True, exist_ok=True)
    Path(arq).write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    return None


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["emitir", "verificar", "revogar"])
    for o in ("--prestador", "--papel", "--plano", "--clientes", "--licenca", "--revogadas", "--cliente", "--lid", "--motivo", "--base"):
        ap.add_argument(o)
    ap.add_argument("--dias", type=int, default=90); ap.add_argument("--dono-confirma", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "emitir":
        lic, p = emitir(a.prestador, a.papel, [c for c in (a.clientes or "").split(",") if c], a.dias, a.dono_confirma, a.base or "https://base.arkos.local", a.plano or "membro")
        if not lic:
            print(p, file=sys.stderr); return 2
        print(json.dumps({"licenca": lic, "payload": p}, ensure_ascii=False)); return 0
    if a.cmd == "verificar":
        ok, motivo, p = verificar(a.licenca or "", ler_revogadas(a.revogadas), a.cliente)
        print(json.dumps({"status": 200 if ok else 401, "motivo": motivo, "papel": (p or {}).get("papel"), "plano": plano_de(p) if ok else None}, ensure_ascii=False))
        return 0 if ok else 4
    erro = revogar(a.lid, a.revogadas, a.motivo, a.dono_confirma)
    if erro:
        print(erro, file=sys.stderr); return 2
    print(json.dumps({"revogada": a.lid}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    sys.exit(main())
