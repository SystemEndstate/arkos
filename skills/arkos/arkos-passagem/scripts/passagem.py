"""arkos-passagem: monta o dossiê de passagem de um cliente para outro prestador a partir da casa da ARKOS.

Uso:
  python passagem.py dossie    --casa C --cliente X --de ana --para bruno [--data 2026-11-22] [--nao-fazer "a;b"]
  python passagem.py confirmar --casa C --cliente X --arquivo passagem-<data>.md --quem bruno

Lê: workspace/<cliente>/_cliente/ (perfil, acessos.json, metas.yaml, notas) e arkos.engine/execucoes/* do cliente
(estado, saida.json: decisoes, pendencias, proxima_acao). Escreve só workspace/<cliente>/_cliente/passagem-<data>.md.
Nunca copia segredo: linhas com cara de senha/token são mascaradas.
Saída: 0 ok · 2 recusa · 3 exceção tratada (ex.: cliente sem execução nem perfil).
"""
import argparse, json, re, sys
from datetime import date, datetime
from pathlib import Path

SEGREDO = re.compile(r"(senha|password|token|secret|api[_-]?key|EAA[A-Za-z0-9]{20,}|sk_(live|test)_\w+|ghp_\w{20,})\s*[:=]?\s*\S*", re.I)


def ler(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def limpar(t):
    return SEGREDO.sub("[segredo omitido]", str(t))


def execs_do_cliente(casa, cliente):
    base = Path(casa) / "arkos.engine" / "execucoes"
    out = []
    for d in sorted(base.iterdir()) if base.is_dir() else []:
        ent, saida, est, aviso = (ler(d / n) for n in ("entradas.json", "saida.json", "estado.json", "aviso.json"))
        c = (saida or {}).get("cliente") or (ent or {}).get("cliente")
        if c != cliente:
            continue
        ets = (est or {}).get("etapas") or []
        if isinstance(ets, dict):
            ets = [{"id": k, "status": v} for k, v in ets.items()]
        ets = [{**e, "id": e.get("id") or e.get("nome")} for e in ets if isinstance(e, dict)]
        portoes = [e["id"] for e in ets if str(e.get("status")) in ("aguardando", "portao")]
        status = (saida or {}).get("status") or ("aguardando" if portoes else "em_andamento")
        out.append({"id": d.name, "playbook": (aviso or {}).get("playbook") or (saida or {}).get("playbook"), "status": status,
                    "portoes": portoes, "decisoes": (saida or {}).get("decisoes") or [], "pendencias": (saida or {}).get("pendencias") or [],
                    "proxima": (saida or {}).get("proxima_acao"), "artefatos": (saida or {}).get("artefatos") or []})
    return out


def dossie(casa, cliente, de, para, data=None, nao_fazer=None):
    pasta = Path(casa) / "workspace" / cliente / "_cliente"
    exs = execs_do_cliente(casa, cliente)
    if not exs and not pasta.is_dir():
        return 3, {"excecao": "entrada_incompleta", "aviso": f"nada encontrado do cliente {cliente} nesta casa"}
    if de == para:
        return 2, {"recusado": "passagem para a mesma pessoa"}
    data = data or date.today().isoformat()
    perfil = ler(pasta / "perfil.json") or {}
    acessos = (ler(pasta / "acessos.json") or {}).get("acessos", [])
    metas = (pasta / "metas.yaml").read_text(encoding="utf-8") if (pasta / "metas.yaml").exists() else None
    abertas = [x for x in exs if not str(x["status"]).startswith(("feito", "cancelado"))]
    L = [f"# Passagem · {cliente} · {data}", "", f"De **{de}** para **{para}**. Leitura confirmada por: _(pendente)_", "",
         "## 1. Quem é o cliente", ""]
    if perfil:
        for k in ("nome", "nicho", "mercado", "oferta", "ticket", "tom", "contato"):
            if perfil.get(k):
                L.append(f"- **{k}:** {limpar(perfil[k])}")
    else:
        L.append("- perfil.json não existe: rodar arkos-perfil antes da reunião.")
    L += ["", "## 2. Metas e SLA", "", f"```yaml\n{limpar(metas)}\n```" if metas else "- metas.yaml não existe (combinar na reunião).", "",
          "## 3. Execuções abertas (o que está no meio)", ""]
    if abertas:
        L += ["| Execução | Playbook | Status | Portão esperando | Próxima ação |", "|---|---|---|---|---|"]
        for x in abertas:
            L.append(f"| {x['id']} | {x['playbook']} | {x['status']} | {', '.join(x['portoes']) or '-'} | {limpar(x['proxima'] or '-')} |")
    else:
        L.append("- nenhuma.")
    L += ["", "## 4. Decisões já tomadas (e por quê)", ""]
    decs = [(x["id"], d) for x in exs for d in x["decisoes"]]
    L += [f"- {limpar(d.get('decisao'))} — _{limpar(d.get('porque') or 'sem porquê registrado')}_ ({eid})" for eid, d in decs] or ["- nenhuma registrada."]
    L += ["", "## 5. Pendências", ""]
    pend = [(x["id"], p) for x in exs for p in x["pendencias"]]
    L += [f"- [ ] {limpar(p if isinstance(p, str) else json.dumps(p, ensure_ascii=False))} ({eid})" for eid, p in pend] or ["- nenhuma."]
    L += ["", "## 6. Acessos a transferir (arkos-acessos transferir)", ""]
    dele = [a for a in acessos if a.get("quem") == de and a.get("status") == "ativo"]
    L += [f"- {a['servico']} ({a.get('nivel')}) — dar a {para} antes de revogar de {de}" for a in dele] or ["- nenhum registrado em acessos.json (conferir na reunião)."]
    L += ["", "## 7. O que NÃO fazer com este cliente", ""]
    L += [f"- {limpar(n.strip())}" for n in (nao_fazer or "").split(";") if n.strip()] or ["- _(o prestador que sai preenche antes da reunião)_"]
    L += ["", "## 8. Entregas anteriores", ""]
    arts = [(x["id"], a) for x in exs for a in x["artefatos"]]
    L += [f"- {a.get('tipo')}: `{a.get('caminho')}` ({eid})" if isinstance(a, dict) else f"- `{a}` ({eid})" for eid, a in arts] or ["- nenhuma."]
    pasta.mkdir(parents=True, exist_ok=True)
    f = pasta / f"passagem-{data}.md"
    f.write_text("\n".join(L) + "\n", encoding="utf-8")
    bloqueios = [x["id"] for x in abertas if x["portoes"]]
    return 0, {"arquivo": str(f), "abertas": len(abertas), "portoes_esperando": bloqueios, "acessos_a_transferir": len(dele),
               "nao_fazer_vazio": not (nao_fazer or "").strip()}


def confirmar(casa, cliente, arquivo, quem):
    f = Path(casa) / "workspace" / cliente / "_cliente" / Path(arquivo).name
    if not f.exists():
        return 3, {"excecao": "entrada_incompleta", "aviso": "dossiê não existe"}
    t = f.read_text(encoding="utf-8")
    if "_(pendente)_" not in t:
        return 0, {"ja_confirmado": True}
    f.write_text(t.replace("_(pendente)_", f"{quem} em {datetime.now():%Y-%m-%d %H:%M}", 1), encoding="utf-8")
    return 0, {"confirmado": quem}


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dossie", "confirmar"])
    for o in ("--casa", "--cliente", "--de", "--para", "--data", "--nao-fazer", "--arquivo", "--quem"):
        ap.add_argument(o)
    a = ap.parse_args(argv)
    code, r = dossie(a.casa, a.cliente, a.de, a.para, a.data, a.nao_fazer) if a.cmd == "dossie" else confirmar(a.casa, a.cliente, a.arquivo, a.quem)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
