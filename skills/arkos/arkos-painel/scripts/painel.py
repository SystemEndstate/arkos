"""arkos-painel: lê as execuções da casa da ARKOS e monta carteira, prazos, fila do dono, indicadores e auditoria.

Uso:
  python painel.py carteira     [--casa C] [--do-cliente X] [--saida DIR]
  python painel.py prazos       [--casa C] [--sla-horas 40] [--sla-json f.json] [--agora ISO]
  python painel.py fila-revisao [--casa C]
  python painel.py indicadores  [--casa C] [--sla-horas 40]
  python painel.py auditoria    [--casa C] [--prestador P] [--agora ISO]

Só lê. Saída em JSON no stdout; com --saida grava painel.json e painel.md na pasta (ex.: workspace/_operacao/painel-2026-11/).
Códigos de saída: 0 ok · 2 recusa (regra dura) · 3 exceção tratada (ex.: casa sem execuções).
"""
import argparse, json, os, sys
from datetime import datetime
from pathlib import Path

FEITO = ("conclu", "feito", "ok", "done", "pulada")


def casa_de(arg=None):
    if arg:
        return Path(arg)
    if os.environ.get("ARKOS_CASA"):
        return Path(os.environ["ARKOS_CASA"])
    home = Path(os.environ.get("ARKOS_HOME") or Path.home() / ".arkos")
    cfg = home / "config.json"
    if cfg.exists():
        c = json.loads(cfg.read_text(encoding="utf-8-sig")).get("casa")
        if c:
            return Path(c)
    sys.exit("casa da ARKOS não definida: rode arkos setup")


def ler(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def etapas_de(estado):
    et = (estado or {}).get("etapas") or []
    if isinstance(et, dict):
        return [{"id": k, "status": v} for k, v in et.items()]
    return [{**e, "id": e.get("id") or e.get("nome")} for e in et if isinstance(e, dict)]


def feito(st):
    return str(st or "").lower().startswith(FEITO)


def criado_em(eid):
    try:
        return datetime.strptime(eid[:15], "%Y%m%d-%H%M%S")
    except ValueError:
        return None


def execucoes(casa):
    base = Path(casa) / "arkos.engine" / "execucoes"
    out = []
    if not base.is_dir():
        return out
    for d in sorted(base.iterdir()):
        if not d.is_dir():
            continue
        aviso, entradas, estado, saida = (ler(d / n) for n in ("aviso.json", "entradas.json", "estado.json", "saida.json"))
        revisao = ler(d / "revisao.json")
        aprov = [x for x in (ler(f) for f in sorted((d / "aprovacoes").glob("*.json"))) if x] if (d / "aprovacoes").is_dir() else []
        escritas = []
        if (d / "escritas.jsonl").exists():
            for linha in (d / "escritas.jsonl").read_text(encoding="utf-8").splitlines():
                if linha.strip():
                    try:
                        escritas.append(json.loads(linha))
                    except json.JSONDecodeError:
                        escritas.append({"_invalida": linha[:80]})
        ets = etapas_de(estado)
        cliente = (saida or {}).get("cliente") or (entradas or {}).get("cliente") or "sem-cliente"
        projeto = (saida or {}).get("projeto") or (entradas or {}).get("projeto") or "sem-projeto"
        if saida and saida.get("status"):
            status = str(saida["status"])
        elif any(str(e.get("status", "")).startswith("bloqueada") for e in ets):
            status = "bloqueado"
        elif any(str(e.get("status", "")) in ("aguardando", "portao") for e in ets):
            status = "aguardando"
        elif ets and all(feito(e.get("status")) for e in ets):
            status = "feito"
        else:
            status = "em_andamento"
        gate = next((e for e in ets if str(e.get("id") or e.get("nome") or "").lower().startswith("gate")), None)
        gj = ler(d / "gate.json")  # veredito do arkos-gate, quando o terminal grava
        if gj:
            gate = {"id": "gate", "status": "feito" if str(gj.get("cor")).lower() == "verde" else str(gj.get("cor")), "tentativas": gj.get("tentativas", 1)}
        out.append({
            "id": d.name, "dir": str(d), "playbook": (aviso or {}).get("playbook") or (saida or {}).get("playbook"),
            "cliente": cliente, "projeto": projeto, "status": status, "criado": criado_em(d.name),
            "prestador": (entradas or {}).get("prestador") or (aviso or {}).get("prestador") or "?",
            "etapas": ets, "gate_verde": bool(gate and feito(gate.get("status"))),
            "gate_tentativas": int((gate or {}).get("tentativas", 1) or 1),
            "portao_cliente_h": sum(float(e.get("portao_cliente_h", 0) or 0) for e in ets),
            "fim": (saida or {}).get("concluido_em"), "saida": saida, "revisao": revisao, "aprovacoes": aprov, "escritas": escritas,
        })
    return out


def aberta(x):
    return not (x["status"].startswith("feito") or x["status"].startswith("cancelado"))


def carteira(exs, do_cliente=None):
    por = {}
    for x in exs:
        if do_cliente and x["cliente"] != do_cliente:
            continue
        c = por.setdefault(x["cliente"], {"abertas": [], "aguardando_portao": [], "bloqueadas": [], "feitas": 0})
        if not aberta(x):
            c["feitas"] += 1
            continue
        item = {"id": x["id"], "playbook": x["playbook"], "projeto": x["projeto"], "status": x["status"]}
        c["abertas"].append(item)
        if x["status"] == "aguardando":
            c["aguardando_portao"].append(item)
        if x["status"].startswith("bloque"):
            c["bloqueadas"].append(item)
    return por


def sla_de(x, sla_horas, sla_map):
    return float(sla_map.get(x["playbook"] or "", sla_horas))


def prazos(exs, agora, sla_horas=40, sla_map=None):
    sla_map = sla_map or {}
    res = []
    for x in exs:
        if not aberta(x) or not x["criado"]:
            continue
        horas = (agora - x["criado"]).total_seconds() / 3600 - x["portao_cliente_h"]  # portão do cliente não conta
        sla = sla_de(x, sla_horas, sla_map)
        pct = horas / sla if sla else 0
        nivel = "estourado" if pct >= 1 else "aviso" if pct >= 0.8 else "ok"
        res.append({"id": x["id"], "cliente": x["cliente"], "playbook": x["playbook"], "horas": round(horas, 1), "sla_h": sla,
                    "pct": round(pct, 2), "nivel": nivel, "avisar": "dono" if nivel == "estourado" else "prestador" if nivel == "aviso" else None})
    return sorted(res, key=lambda r: -r["pct"])


def fila_revisao(exs):
    return [{"id": x["id"], "cliente": x["cliente"], "playbook": x["playbook"]} for x in exs
            if x["gate_verde"] and not x["revisao"] and x["status"].startswith("feito")]


def indicadores(exs, sla_horas=40, sla_map=None):
    sla_map = sla_map or {}
    feitas = [x for x in exs if x["status"].startswith("feito")]
    no_prazo = 0
    for x in feitas:
        fim = None
        try:
            fim = datetime.fromisoformat(x["fim"]) if x["fim"] else None
        except ValueError:
            pass
        if fim and x["criado"] and (fim - x["criado"]).total_seconds() / 3600 - x["portao_cliente_h"] <= sla_de(x, sla_horas, sla_map):
            no_prazo += 1
    revisadas = [x for x in exs if x["revisao"]]
    devolvidas = [x for x in revisadas if x["revisao"].get("decisao") == "devolver"]
    com_gate = [x for x in exs if x["gate_verde"]]
    est = sum(float(((x["saida"] or {}).get("campos") or {}).get("custo_estimado", 0) or 0) for x in feitas)
    real = sum(float(((x["saida"] or {}).get("campos") or {}).get("custo_real", 0) or 0) for x in feitas)
    pc = lambda a, b: round(100 * a / b, 1) if b else None
    return {"execucoes": len(exs), "feitas": len(feitas), "no_prazo_pct": pc(no_prazo, len([x for x in feitas if x["fim"]])),
            "devolucao_pct": pc(len(devolvidas), len(revisadas)),
            "gate_verde_de_primeira_pct": pc(len([x for x in com_gate if x["gate_tentativas"] == 1]), len(com_gate)),
            "custo_estimado": est, "custo_real": real, "custo_real_sobre_estimado": round(real / est, 2) if est else None}


def auditoria(exs, agora, prestador=None):
    """Toda escrita/envio registrada precisa de aprovação válida: mesma id, hash igual e dentro da validade."""
    anomalias, conferidas = [], 0
    for x in exs:
        if prestador and x["prestador"] != prestador:
            continue
        aprov = {a.get("id"): a for a in x["aprovacoes"]}
        for w in x["escritas"]:
            conferidas += 1
            if "_invalida" in w:
                anomalias.append({"execucao": x["id"], "problema": "linha ilegível em escritas.jsonl"}); continue
            a = aprov.get(w.get("aprovacao"))
            if not a:
                anomalias.append({"execucao": x["id"], "alvo": w.get("alvo"), "problema": "escrita/envio sem aprovação"}); continue
            if a.get("hash") != w.get("hash"):
                anomalias.append({"execucao": x["id"], "alvo": w.get("alvo"), "problema": "hash da escrita difere do aprovado"})
            try:
                if w.get("quando") and a.get("expira_em") and datetime.fromisoformat(w["quando"]) > datetime.fromisoformat(a["expira_em"]):
                    anomalias.append({"execucao": x["id"], "alvo": w.get("alvo"), "problema": "aprovação vencida na hora da escrita"})
            except ValueError:
                anomalias.append({"execucao": x["id"], "problema": "data inválida na aprovação ou na escrita"})
    return {"conferidas": conferidas, "anomalias": anomalias, "verde": not anomalias}


def md(titulo, dados):
    return f"# {titulo}\n\n```json\n{json.dumps(dados, ensure_ascii=False, indent=2, default=str)}\n```\n"


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["carteira", "prazos", "fila-revisao", "indicadores", "auditoria"])
    ap.add_argument("--casa"); ap.add_argument("--do-cliente"); ap.add_argument("--prestador"); ap.add_argument("--saida")
    ap.add_argument("--sla-horas", type=float, default=40.0); ap.add_argument("--sla-json"); ap.add_argument("--agora")
    a = ap.parse_args(argv)
    casa = casa_de(a.casa)
    exs = execucoes(casa)
    if not exs:
        print(json.dumps({"aviso": f"nenhuma execução em {casa}/arkos.engine/execucoes", "excecao": "entrada_incompleta"}, ensure_ascii=False))
        return 3
    agora = datetime.fromisoformat(a.agora) if a.agora else datetime.now()
    sla_map = ler(a.sla_json) if a.sla_json else {}
    r = {"carteira": lambda: carteira(exs, a.do_cliente), "prazos": lambda: prazos(exs, agora, a.sla_horas, sla_map),
         "fila-revisao": lambda: fila_revisao(exs), "indicadores": lambda: indicadores(exs, a.sla_horas, sla_map),
         "auditoria": lambda: auditoria(exs, agora, a.prestador)}[a.cmd]()
    print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
    if a.saida:
        d = Path(a.saida)
        if "arkos.engine" in d.parts:
            print("recusado: entrega não fica dentro de arkos.engine (regra PASTA-CASA)", file=sys.stderr)
            return 2
        d.mkdir(parents=True, exist_ok=True)
        (d / "painel.json").write_text(json.dumps(r, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        (d / "painel.md").write_text(md(f"Painel ARKOS · {a.cmd}", r), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
