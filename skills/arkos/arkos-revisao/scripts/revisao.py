"""arkos-revisao: registra a decisão do dono (ou do cliente) sobre uma entrega: aprovar, aprovar com ressalva ou devolver.

Uso:
  python revisao.py decidir --casa C --execucao ID --quem dono --papel dono --decisao aprovar|ressalva|devolver
                            [--motivo "..."] [--voltar-para ETAPA] [--ressalvas "a;b"]
  python revisao.py ler     --casa C --execucao ID

Grava <casa>/arkos.engine/execucoes/<id>/revisao.json (histórico de rodadas; nada é apagado).
Regras: só revisa com gate verde; devolver exige motivo e etapa de volta; ressalva exige a lista;
quem executou não revisa a própria entrega; papel prestador não aprova.
Saída: 0 ok · 2 recusa · 3 exceção tratada.
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

DECISOES = ("aprovar", "ressalva", "devolver")
PODE_APROVAR = ("dono", "revisor", "cliente")


def ler(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def etapas(estado):
    e = (estado or {}).get("etapas") or []
    if isinstance(e, dict):
        return [{"id": k, "status": v} for k, v in e.items()]
    return [{**x, "id": x.get("id") or x.get("nome")} for x in e if isinstance(x, dict)]


def decidir(casa, eid, quem, papel, decisao, motivo=None, voltar=None, ressalvas=None, agora=None):
    d = Path(casa) / "arkos.engine" / "execucoes" / eid
    if not d.is_dir():
        return 3, {"excecao": "entrada_incompleta", "aviso": f"execução {eid} não existe"}
    if papel not in PODE_APROVAR:
        return 2, {"recusado": f"papel {papel} não revisa entrega (só {', '.join(PODE_APROVAR)})"}
    entradas = ler(d / "entradas.json") or {}
    if quem and quem == entradas.get("prestador"):
        return 2, {"recusado": "quem executou não revisa a própria entrega"}
    ets = etapas(ler(d / "estado.json"))
    gate = next((e for e in ets if str(e.get("id") or "").lower().startswith("gate")), None)
    gj = ler(d / "gate.json")  # veredito do arkos-gate gravado pelo terminal
    verde = (gj and str(gj.get("cor")).lower() == "verde") or (gate and str(gate.get("status", "")).startswith(("feito", "ok", "verde")))
    if not verde:
        return 2, {"recusado": "gate não está verde: a entrega volta para o prestador antes da revisão"}
    if decisao not in DECISOES:
        return 3, {"excecao": "entrada_incompleta", "pergunta": f"decisão em {DECISOES}"}
    if decisao == "devolver":
        ids = [e.get("id") for e in ets]
        if not motivo or not voltar:
            return 3, {"excecao": "entrada_incompleta", "pergunta": "devolver precisa de motivo e da etapa para onde volta"}
        if voltar not in ids:
            return 3, {"excecao": "entrada_incompleta", "pergunta": f"etapa {voltar} não existe; opções: {ids}"}
    lista = [r.strip() for r in (ressalvas or "").split(";") if r.strip()]
    if decisao == "ressalva" and not lista:
        return 3, {"excecao": "entrada_incompleta", "pergunta": "aprovar com ressalva precisa da lista de ressalvas"}
    f = d / "revisao.json"
    hist = ler(f) or {"rodadas": []}
    rodada = {"n": len(hist["rodadas"]) + 1, "quem": quem, "papel": papel, "decisao": decisao, "motivo": motivo,
              "voltar_para": voltar, "ressalvas": lista, "quando": agora or datetime.now().isoformat(timespec="seconds")}
    hist["rodadas"].append(rodada)
    hist.update(decisao=decisao, quem=quem, quando=rodada["quando"], motivo=motivo)
    f.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    if decisao == "devolver":  # exceção retrabalho: reabre da etapa pedida em diante, o resto fica como está
        reabrir, achou = [], False
        for e in ets:
            achou = achou or e.get("id") == voltar
            if achou:
                e["status"] = "pendente"; reabrir.append(e["id"])
        est = ler(d / "estado.json") or {}
        est["etapas"] = ets
        (d / "estado.json").write_text(json.dumps(est, ensure_ascii=False, indent=2), encoding="utf-8")
        rodada["reaberta"] = reabrir
        f.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0, rodada


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["decidir", "ler"])
    for o in ("--casa", "--execucao", "--quem", "--papel", "--decisao", "--motivo", "--voltar-para", "--ressalvas"):
        ap.add_argument(o)
    a = ap.parse_args(argv)
    if a.cmd == "ler":
        print(json.dumps(ler(Path(a.casa) / "arkos.engine" / "execucoes" / a.execucao / "revisao.json"), ensure_ascii=False, indent=2)); return 0
    code, r = decidir(a.casa, a.execucao, a.quem, a.papel, a.decisao, a.motivo, a.voltar_para, a.ressalvas)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
