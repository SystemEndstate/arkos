"""arkos-atualizar: homologa e publica uma versão nova da ARKOS para os prestadores, com rollback para a anterior.

Uso:
  python atualizar.py homologar --release release.json --testes resultado-testes.json [--atual 0.5.0]
  python atualizar.py publicar  --release release.json --canal canal.json --aprovacao revisao.json [--confirmo]
  python atualizar.py rollback  --canal canal.json --motivo "..." [--confirmo]

release.json = {"versao": "0.6.0", "notas": "...", "novidades": ["..."], "arquivos": {"playbooks.json": "<sha256>", ...}}
resultado-testes.json = {"maquina": "teste-limpa", "total": 34, "passou": 34, "falhou": [], "aceitacao": {"arkos-x": "verde", ...}}
canal.json = {"atual": "0.5.0", "anteriores": ["0.4.0"], "historico": [...]}  (o que `arkos update` lê)
revisao.json = aprovação do dono (arkos-revisao), decisao "aprovar".

Publicar = trocar o ponteiro do canal (escrita): precisa da homologação verde, da aprovação do dono e de --confirmo.
O rollback volta o ponteiro para a versão anterior. Nada é apagado.
Saída: 0 ok · 2 recusa · 3 exceção tratada.
"""
import argparse, hashlib, json, re, sys
from datetime import datetime
from pathlib import Path

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def ver(v):
    m = SEMVER.match(v or "")
    return tuple(int(x) for x in m.groups()) if m else None


def ler(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def homologar(rel, testes, atual=None):
    prob = []
    v = ver(rel.get("versao"))
    if not v:
        prob.append(f"versão fora do formato X.Y.Z: {rel.get('versao')}")
    elif atual and ver(atual) and v <= ver(atual):
        prob.append(f"versão {rel['versao']} não é maior que a atual {atual}")
    if not (rel.get("notas") or "").strip() or not rel.get("novidades"):
        prob.append("faltam notas e novidades (o prestador precisa saber o que mudou)")
    if not rel.get("arquivos") or not all(re.fullmatch(r"[0-9a-f]{64}", h or "") for h in rel["arquivos"].values()):
        prob.append("arquivos sem sha256: sem isso o prestador não confere o que baixou")
    if testes.get("maquina") in (None, "", "dev", "minha"):
        prob.append("testes precisam rodar numa máquina de teste limpa, não na de desenvolvimento")
    if testes.get("falhou") or testes.get("passou") != testes.get("total") or not testes.get("total"):
        prob.append(f"testes: {testes.get('passou')}/{testes.get('total')} (falhou: {', '.join(testes.get('falhou') or []) or '?'})")
    nao_verde = [k for k, c in (testes.get("aceitacao") or {}).items() if c != "verde"]
    if nao_verde:
        prob.append(f"aceitação não verde: {', '.join(nao_verde)}")
    return not prob, prob


def publicar(rel, canal_arq, aprov, confirmo, testes=None, agora=None):
    if not aprov or aprov.get("decisao") != "aprovar" or aprov.get("papel", "dono") != "dono":
        return 2, {"recusado": "publicar precisa da aprovação do dono (arkos-revisao, decisão aprovar)"}
    canal = ler(canal_arq) if Path(canal_arq).exists() else {"atual": None, "anteriores": [], "historico": []}
    if testes is not None:
        ok, prob = homologar(rel, testes, canal.get("atual"))
        if not ok:
            return 2, {"recusado": "homologação não está verde", "problemas": prob}
    if not confirmo:
        return 2, {"previa": {"de": canal.get("atual"), "para": rel["versao"], "rollback": f"volta para {canal.get('atual')}"},
                   "recusado": "confirme com --confirmo depois de ler a prévia"}
    if canal.get("atual"):
        canal["anteriores"] = [canal["atual"], *[v for v in canal.get("anteriores", []) if v != canal["atual"]]][:10]
    canal["atual"] = rel["versao"]
    canal.setdefault("historico", []).append({"quando": agora or datetime.now().isoformat(timespec="seconds"), "acao": "publicar",
                                              "versao": rel["versao"], "aprovado_por": aprov.get("quem"),
                                              "hash_release": hashlib.sha256(json.dumps(rel, sort_keys=True).encode()).hexdigest()})
    Path(canal_arq).write_text(json.dumps(canal, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0, {"publicada": rel["versao"], "anterior": canal["anteriores"][0] if canal["anteriores"] else None}


def rollback(canal_arq, motivo, confirmo):
    canal = ler(canal_arq)
    if not canal.get("anteriores"):
        return 3, {"excecao": "rollback", "aviso": "não há versão anterior para voltar"}
    if not motivo:
        return 3, {"excecao": "entrada_incompleta", "pergunta": "motivo do rollback (vai para o histórico)"}
    if not confirmo:
        return 2, {"previa": {"de": canal["atual"], "para": canal["anteriores"][0]}, "recusado": "confirme com --confirmo"}
    de = canal["atual"]
    canal["atual"] = canal["anteriores"].pop(0)
    canal["historico"].append({"quando": datetime.now().isoformat(timespec="seconds"), "acao": "rollback", "de": de, "para": canal["atual"], "motivo": motivo})
    Path(canal_arq).write_text(json.dumps(canal, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0, {"atual": canal["atual"], "de": de}


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["homologar", "publicar", "rollback"])
    for o in ("--release", "--testes", "--atual", "--canal", "--aprovacao", "--motivo"):
        ap.add_argument(o)
    ap.add_argument("--confirmo", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "homologar":
        ok, prob = homologar(ler(a.release), ler(a.testes), a.atual)
        print(json.dumps({"verde": ok, "problemas": prob}, ensure_ascii=False, indent=2)); return 0 if ok else 3
    if a.cmd == "publicar":
        code, r = publicar(ler(a.release), a.canal, ler(a.aprovacao) if a.aprovacao else None, a.confirmo, ler(a.testes) if a.testes else None)
    else:
        code, r = rollback(a.canal, a.motivo, a.confirmo)
    print(json.dumps(r, ensure_ascii=False, indent=2)); return code


if __name__ == "__main__":
    sys.exit(main())
