"""arkos-monitor: confere se os sites e APIs entregues estão no ar (status HTTP, tempo, texto esperado, validade do HTTPS).
Só lê (GET/HEAD). Não reinicia nada nem mexe em servidor: alerta e aponta o playbook (deploy-infra) e o rollback.

Uso:
  python monitor.py checar --alvos alvos.json [--saida workspace/<cliente>/<projeto>/monitor/] [--estado estado.json]

alvos.json = [{"nome": "landing", "url": "https://...", "esperar_status": 200, "contem": "Agende",
               "max_ms": 3000, "tls_min_dias": 14}]
--estado guarda as falhas seguidas por alvo: alerta só na 2ª falha seguida (evita alarme por soluço de rede).
Saída: 0 tudo verde · 3 algum alvo amarelo/vermelho (exceção fora_do_ar tratada).
"""
import argparse, json, socket, ssl, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def tls_dias(host, porta=443, timeout=8):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, porta), timeout=timeout) as s, ctx.wrap_socket(s, server_hostname=host) as t:
        fim = datetime.fromtimestamp(ssl.cert_time_to_seconds(t.getpeercert()["notAfter"]), timezone.utc)
    return (fim - datetime.now(timezone.utc)).days


def checar_um(a, timeout=10):
    r = {"nome": a.get("nome") or a["url"], "url": a["url"], "cor": "verde", "problemas": []}
    u = urlparse(a["url"])
    if u.scheme not in ("http", "https"):
        return {**r, "cor": "vermelho", "problemas": ["url precisa ser http(s)"]}
    req = urllib.request.Request(a["url"], headers={"User-Agent": "arkos-monitor/1.0"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status, corpo = resp.status, resp.read(200_000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        status, corpo = e.code, ""
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        return {**r, "cor": "vermelho", "problemas": [f"fora do ar: {getattr(e, 'reason', e)}"], "ms": None}
    ms = round((time.monotonic() - t0) * 1000)
    r.update(status=status, ms=ms)
    if status != a.get("esperar_status", 200):
        r["cor"] = "vermelho"; r["problemas"].append(f"status {status} (esperado {a.get('esperar_status', 200)})")
    if a.get("contem") and a["contem"] not in corpo:
        r["cor"] = "vermelho"; r["problemas"].append(f"texto esperado ausente: {a['contem']!r} (página errada ou quebrada)")
    if ms > a.get("max_ms", 3000) and r["cor"] == "verde":
        r["cor"] = "amarelo"; r["problemas"].append(f"lento: {ms} ms (limite {a.get('max_ms', 3000)})")
    if u.scheme == "https":
        try:
            d = tls_dias(u.hostname, u.port or 443)
            r["tls_dias"] = d
            if d < a.get("tls_min_dias", 14):
                r["cor"] = "vermelho" if d < 3 else ("amarelo" if r["cor"] == "verde" else r["cor"])
                r["problemas"].append(f"certificado vence em {d} dias")
        except (OSError, ssl.SSLError, KeyError) as e:
            r["cor"] = "vermelho"; r["problemas"].append(f"HTTPS com problema: {e}")
    elif not a.get("permitir_http"):
        r["cor"] = "amarelo" if r["cor"] == "verde" else r["cor"]; r["problemas"].append("sem HTTPS")
    return r


def checar(alvos, estado=None):
    estado = dict(estado or {})
    res = []
    for a in alvos:
        r = checar_um(a)
        n = estado.get(r["nome"], 0) + 1 if r["cor"] == "vermelho" else 0
        estado[r["nome"]] = n
        r["falhas_seguidas"] = n
        r["alertar"] = n >= 2 or (r["cor"] == "amarelo" and any("certificado" in p for p in r["problemas"]))
        if r["cor"] == "vermelho":
            r["proximo"] = "abrir deploy-infra (etapa monitor/rollback): voltar a última versão que funcionava; nada é reiniciado sozinho"
        res.append(r)
    return res, estado


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["checar"]); ap.add_argument("--alvos", required=True); ap.add_argument("--saida"); ap.add_argument("--estado")
    a = ap.parse_args(argv)
    alvos = json.loads(Path(a.alvos).read_text(encoding="utf-8-sig"))
    est = json.loads(Path(a.estado).read_text(encoding="utf-8")) if a.estado and Path(a.estado).exists() else {}
    res, est = checar(alvos, est)
    if a.estado:
        Path(a.estado).write_text(json.dumps(est), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if a.saida:
        d = Path(a.saida); d.mkdir(parents=True, exist_ok=True)
        (d / f"monitor-{datetime.now():%Y%m%d-%H%M}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(r["cor"] == "verde" for r in res) else 3


if __name__ == "__main__":
    sys.exit(main())
