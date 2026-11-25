"""arkos-acessos: inventário de acessos por cliente (quem tem o quê, em qual nível), sem nunca guardar senha ou token.

Uso:
  python acessos.py checklist  --casa C --cliente X --servicos meta_bm,meta_ads,ga4,gtm,dominio,crm,whatsapp,n8n
  python acessos.py registrar  --casa C --cliente X --servico meta_ads --quem ana --nivel leitura [--conta ID] [--obs "..."]
  python acessos.py transferir --casa C --cliente X --de ana --para bruno      (gera PLANO; não executa)
  python acessos.py revogar    --casa C --prestador ana                         (gera PLANO para todos os clientes)
  python acessos.py concluir   --casa C --cliente X --plano arquivo.json --item N --aprovacao ID

Arquivo único por cliente: <casa>/workspace/<cliente>/_cliente/acessos.json (+ acessos.md legível).
Planos vão para <casa>/workspace/<cliente>/_cliente/planos-acesso/. Executar a mudança na plataforma é do humano
ou de uma ferramenta passando pela arkos-guarda-escrita; aqui só se marca o item feito com o id da aprovação.
Saída: 0 ok · 2 recusa (regra dura) · 3 exceção tratada.
"""
import argparse, json, re, sys
from datetime import datetime
from pathlib import Path

SERVICOS = {
    "meta_bm": "Meta Business Manager (parceiro da agência, nunca login pessoal)",
    "meta_ads": "Conta de anúncios Meta (papel: anunciante/analista)",
    "google_ads": "Google Ads (acesso por MCC)",
    "ga4": "Google Analytics 4 (leitor/analista)",
    "gtm": "Google Tag Manager (publicar só com aprovação)",
    "tiktok_ads": "TikTok Ads (Business Center)",
    "dominio": "Registrador e DNS do domínio",
    "hospedagem": "Hospedagem do site",
    "crm": "CRM do cliente",
    "whatsapp": "WhatsApp Business (só API oficial, opt-in)",
    "n8n": "n8n (workflows)",
    "easypanel": "Easypanel (projeto criado pelo usuário)",
    "github": "GitHub (repositório do cliente)",
}
NIVEIS = ("leitura", "edicao", "admin")
# segredo nunca entra: senha, token, chave, cookie, OTP, cartão
SEGREDO = re.compile(r"(senha|password|passwd|token|secret|segredo|api[_-]?key|chave|cookie|otp|2fa|cvv|"
                     r"EAA[A-Za-z0-9]{20,}|sk_(live|test)_|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{20,}|\b\d{13,19}\b)", re.I)


def caminho(casa, cliente):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", cliente or ""):
        raise SystemExit("cliente precisa ser slug (a-z, 0-9, -)")
    return Path(casa) / "workspace" / cliente / "_cliente"


def ler(casa, cliente):
    f = caminho(casa, cliente) / "acessos.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"cliente": cliente, "acessos": [], "historico": []}


def gravar(casa, cliente, d):
    pasta = caminho(casa, cliente); pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "acessos.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    L = [f"# Acessos · {cliente}", "", "Só o que existe e quem tem. **Nunca a senha.**", "", "| Serviço | Quem | Nível | Conta | Status | Desde |", "|---|---|---|---|---|---|"]
    for a in d["acessos"]:
        L.append(f"| {a['servico']} | {a.get('quem') or '-'} | {a.get('nivel') or '-'} | {a.get('conta') or '-'} | {a['status']} | {a.get('desde') or '-'} |")
    (pasta / "acessos.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def tem_segredo(*vals):
    return any(v and SEGREDO.search(str(v)) for v in vals)


def checklist(casa, cliente, servicos):
    d = ler(casa, cliente)
    desconhecidos = [s for s in servicos if s not in SERVICOS]
    if desconhecidos:
        print(json.dumps({"excecao": "entrada_incompleta", "pergunta": f"serviço desconhecido: {', '.join(desconhecidos)}. Opções: {', '.join(SERVICOS)}"}, ensure_ascii=False))
        return 3
    ja = {a["servico"] for a in d["acessos"]}
    for s in servicos:
        if s not in ja:
            d["acessos"].append({"servico": s, "descricao": SERVICOS[s], "quem": None, "nivel": None, "status": "pendente"})
    gravar(casa, cliente, d)
    print(json.dumps({"pendentes": [a["servico"] for a in d["acessos"] if a["status"] == "pendente"]}, ensure_ascii=False))
    return 0


def registrar(casa, cliente, servico, quem, nivel, conta=None, obs=None, agora=None):
    if tem_segredo(conta, obs, quem):
        print("recusado: parece senha/token/chave. Aqui só entra quem tem acesso e em qual nível; o segredo fica no cofre do cliente.", file=sys.stderr)
        return 2
    if servico not in SERVICOS or nivel not in NIVEIS:
        print(json.dumps({"excecao": "entrada_incompleta", "pergunta": f"serviço em {list(SERVICOS)} e nível em {NIVEIS}"}, ensure_ascii=False))
        return 3
    d = ler(casa, cliente)
    d["acessos"] = [a for a in d["acessos"] if not (a["servico"] == servico and a.get("quem") in (None, quem))]
    d["acessos"].append({"servico": servico, "descricao": SERVICOS[servico], "quem": quem, "nivel": nivel, "conta": conta,
                         "obs": obs, "status": "ativo", "desde": agora or datetime.now().isoformat(timespec="seconds")})
    d["historico"].append({"quando": agora or datetime.now().isoformat(timespec="seconds"), "acao": "registrar", "servico": servico, "quem": quem, "nivel": nivel})
    gravar(casa, cliente, d)
    return 0


def plano(casa, cliente, itens, motivo):
    pasta = caminho(casa, cliente) / "planos-acesso"; pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{datetime.now():%Y%m%d-%H%M%S}-{motivo}.json"
    p = {"cliente": cliente, "motivo": motivo, "acao": "escrita", "guarda": "arkos-guarda-escrita",
         "regra": "dar ao novo ANTES de revogar do antigo; cada item só fica feito com aprovacao_id", "itens": itens}
    (pasta / nome).write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    return pasta / nome, p


def transferir(casa, cliente, de, para):
    d = ler(casa, cliente)
    dele = [a for a in d["acessos"] if a.get("quem") == de and a["status"] == "ativo"]
    if not dele:
        print(json.dumps({"excecao": "entrada_incompleta", "aviso": f"{de} não tem acesso ativo em {cliente}"}, ensure_ascii=False))
        return 3
    itens = []
    for a in dele:  # ordem importa: dar primeiro, revogar depois (cliente nunca fica sem operador)
        itens.append({"n": len(itens) + 1, "tipo": "dar", "servico": a["servico"], "quem": para, "nivel": a["nivel"], "conta": a.get("conta"), "feito": False,
                      "rollback": f"remover {para} de {a['servico']}"})
    for a in dele:
        itens.append({"n": len(itens) + 1, "tipo": "revogar", "servico": a["servico"], "quem": de, "nivel": a["nivel"], "conta": a.get("conta"), "feito": False,
                      "depende_de": [i["n"] for i in itens if i["tipo"] == "dar" and i["servico"] == a["servico"]],
                      "rollback": f"devolver {a['nivel']} a {de} em {a['servico']}"})
    f, _ = plano(casa, cliente, itens, f"transferir-{de}-para-{para}")
    print(json.dumps({"plano": str(f), "itens": len(itens)}, ensure_ascii=False))
    return 0


def revogar(casa, prestador):
    ws = Path(casa) / "workspace"
    planos = []
    for c in sorted(p.name for p in ws.iterdir() if p.is_dir() and not p.name.startswith("_")) if ws.is_dir() else []:
        d = ler(casa, c)
        dele = [a for a in d["acessos"] if a.get("quem") == prestador and a["status"] == "ativo"]
        if not dele:
            continue
        itens = [{"n": i + 1, "tipo": "revogar", "servico": a["servico"], "quem": prestador, "nivel": a["nivel"], "conta": a.get("conta"),
                  "feito": False, "rollback": f"devolver {a['nivel']} a {prestador} em {a['servico']}"} for i, a in enumerate(dele)]
        itens.append({"n": len(itens) + 1, "tipo": "girar_segredos", "servico": "todos", "quem": prestador, "feito": False,
                      "obs": "girar tokens e chaves de API que ele viu (n8n, Easypanel, webhooks); o novo segredo vai direto ao cofre",
                      "rollback": "sem rollback: segredo antigo não volta"})
        f, _ = plano(casa, c, itens, f"revogar-{prestador}")
        planos.append(str(f))
    print(json.dumps({"planos": planos, "clientes": len(planos)}, ensure_ascii=False))
    return 0 if planos else 3


def concluir(casa, cliente, arq, n, aprovacao):
    if not aprovacao:
        print("recusado: item de acesso só fica feito com o id da aprovação da arkos-guarda-escrita", file=sys.stderr)
        return 2
    p = json.loads(Path(arq).read_text(encoding="utf-8"))
    item = next((i for i in p["itens"] if i["n"] == n), None)
    if not item:
        return 3
    pend = [i for i in p["itens"] if i["n"] in item.get("depende_de", []) and not i["feito"]]
    if pend:
        print(f"recusado: revogar antes de dar o acesso ao novo deixa o cliente sem operador (falta item {pend[0]['n']})", file=sys.stderr)
        return 2
    item.update(feito=True, aprovacao=aprovacao, quando=datetime.now().isoformat(timespec="seconds"))
    Path(arq).write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    d = ler(casa, cliente)
    if item["tipo"] == "dar":
        d["acessos"].append({"servico": item["servico"], "descricao": SERVICOS.get(item["servico"], ""), "quem": item["quem"], "nivel": item["nivel"],
                             "conta": item.get("conta"), "status": "ativo", "desde": item["quando"]})
    elif item["tipo"] == "revogar":
        for a in d["acessos"]:
            if a["servico"] == item["servico"] and a.get("quem") == item["quem"]:
                a["status"] = "revogado"
    d["historico"].append({"quando": item["quando"], "acao": item["tipo"], "servico": item["servico"], "quem": item["quem"], "aprovacao": aprovacao})
    gravar(casa, cliente, d)
    return 0


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["checklist", "registrar", "transferir", "revogar", "concluir"])
    for o in ("--casa", "--cliente", "--servicos", "--servico", "--quem", "--nivel", "--conta", "--obs", "--de", "--para", "--prestador", "--plano", "--aprovacao"):
        ap.add_argument(o)
    ap.add_argument("--item", type=int)
    a = ap.parse_args(argv)
    if not a.casa:
        raise SystemExit("--casa obrigatório")
    if a.cmd == "checklist":
        return checklist(a.casa, a.cliente, [s.strip() for s in (a.servicos or "").split(",") if s.strip()])
    if a.cmd == "registrar":
        return registrar(a.casa, a.cliente, a.servico, a.quem, a.nivel, a.conta, a.obs)
    if a.cmd == "transferir":
        return transferir(a.casa, a.cliente, a.de, a.para)
    if a.cmd == "revogar":
        return revogar(a.casa, a.prestador)
    return concluir(a.casa, a.cliente, a.plano, a.item, a.aprovacao)


if __name__ == "__main__":
    sys.exit(main())
