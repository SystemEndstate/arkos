"""arkos-suporte: diagnóstico da instalação do prestador, busca no FAQ e chamado para o dono.

Uso:
  python suporte.py diagnostico [--casa C] [--home ~/.arkos] [--saida arquivo.json]
  python suporte.py faq         --pergunta "o rodapé não aparece" [--faq faq.json]
  python suporte.py chamado     --casa C --resumo "..." --diagnostico diag.json

Nunca lê .env, .secrets, tokens ou chaves: só verifica se o arquivo EXISTE. Logs entram só as últimas linhas, mascaradas.
Subprocessos (node, git, claude) rodam sem janela (CREATE_NO_WINDOW).
Chamado fica em <casa>/workspace/_operacao/suporte/chamado-<data>.md; enviar ao dono é com o prestador (nada sai sozinho).
Saída: 0 ok · 3 exceção tratada (diagnóstico com item vermelho, FAQ sem resposta).
"""
import argparse, json, os, re, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

NW = 0x08000000 if os.name == "nt" else 0
SEGREDO = re.compile(r"authorization\s*[:=].*|bearer\s+\S+|(senha|password|token|secret|api[_-]?key)\s*[:=]?\s*\S+|EAA[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{16,}|ghp_\w{20,}", re.I)
CASA_PASTAS = ("arkos.engine", "docs", "tools", "workspace")

FAQ_PADRAO = [
    {"chaves": ["rodape", "rodapé", "status", "barra"], "resposta": "Rodapé some quando o terminal é estreito ou o statusline não foi instalado. Rode `arkos setup` de novo e abra o terminal com pelo menos 100 colunas."},
    {"chaves": ["casa", "pasta", "workspace", "onde"], "resposta": "A casa fica em ~/.arkos/config.json (campo casa). Dentro dela: arkos.engine, docs, tools e workspace. Rode `arkos setup` para escolher outra."},
    {"chaves": ["401", "licenca", "licença", "login", "base"], "resposta": "401 da base = licença vencida, revogada ou de outro cliente. Rode `arkos login <licença nova>`; se persistir, abra chamado (o dono confere)."},
    {"chaves": ["node", "npm", "versao", "versão"], "resposta": "A ARKOS pede Node 20 ou mais novo. Instale pelo site oficial (LTS) e rode `arkos doctor`."},
    {"chaves": ["mcp", "ferramenta", "conectar", "oauth"], "resposta": "MCP desconectado: rode `claude mcp list`; se aparecer falha, refaça o login OAuth daquela ferramenta. Nunca cole token no chat."},
    {"chaves": ["lento", "travando", "demora", "cota"], "resposta": "Lentidão costuma ser cota do Claude ou contexto cheio. Rode /compact ou abra uma sessão nova; a execução retoma de arkos.engine/execucoes/<id>."},
]


def cmd(args):
    exe = shutil.which(args[0])
    if not exe:
        return None
    try:
        r = subprocess.run([exe, *args[1:]], capture_output=True, text=True, timeout=20, creationflags=NW)
        return (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr) else ""
    except (OSError, subprocess.TimeoutExpired):
        return None


def versao_node(v):
    m = re.match(r"v?(\d+)", v or "")
    return int(m.group(1)) if m else 0


def diagnostico(casa=None, home=None, versoes=None):
    home = Path(home or os.environ.get("ARKOS_HOME") or Path.home() / ".arkos")
    itens = []
    add = lambda nome, ok, det, cor=None: itens.append({"item": nome, "cor": cor or ("verde" if ok else "vermelho"), "detalhe": det})
    v = versoes if versoes is not None else {"node": cmd(["node", "--version"]), "git": cmd(["git", "--version"]), "claude": cmd(["claude", "--version"])}
    add("node", versao_node(v.get("node")) >= 20, v.get("node") or "não encontrado")
    add("git", bool(v.get("git")), v.get("git") or "não encontrado")
    add("claude", bool(v.get("claude")), v.get("claude") or "Claude Code não encontrado")
    cfg = home / "config.json"
    conf = {}
    if cfg.exists():
        try:
            conf = json.loads(cfg.read_text(encoding="utf-8-sig"))
            add("config", True, str(cfg))
        except json.JSONDecodeError:
            add("config", False, "config.json corrompido: rode arkos setup")
    else:
        add("config", False, "~/.arkos/config.json não existe: rode arkos setup")
    casa = Path(casa or conf.get("casa") or "")
    if str(casa) and casa.is_dir():
        faltam = [p for p in CASA_PASTAS if not (casa / p).is_dir()]
        add("casa", not faltam, f"{casa}" + (f" (faltam: {', '.join(faltam)})" if faltam else ""))
        perfil = casa / "arkos.engine" / "perfil.json"
        add("perfil", perfil.exists(), "perfil.json ok" if perfil.exists() else "sem perfil: rode o onboarding (arkos-perfil)", None if perfil.exists() else "amarelo")
        logs = sorted((casa / "arkos.engine" / "logs").glob("*.log"))[-1:] if (casa / "arkos.engine" / "logs").is_dir() else []
        cauda = []
        for f in logs:
            cauda = [SEGREDO.sub("[mascarado]", l) for l in f.read_text(encoding="utf-8", errors="ignore").splitlines()[-20:]]
        add("logs", True, f"{len(cauda)} linhas do último log", "verde" if not any("erro" in l.lower() for l in cauda) else "amarelo")
    else:
        add("casa", False, f"casa não encontrada ({casa or 'não configurada'})"); cauda = []
    lic = home / "licenca.txt"
    add("licenca", lic.exists(), "licença presente (conteúdo não lido aqui)" if lic.exists() else "sem licença: arkos login <licença>", None if lic.exists() else "amarelo")
    cor = "vermelho" if any(i["cor"] == "vermelho" for i in itens) else "amarelo" if any(i["cor"] == "amarelo" for i in itens) else "verde"
    return {"quando": datetime.now().isoformat(timespec="seconds"), "geral": cor, "itens": itens, "log": cauda,
            "so_ou": sys.platform, "python": sys.version.split()[0]}


def faq(pergunta, base=None):
    p = pergunta.lower()
    melhor = max(((sum(c in p for c in f["chaves"]), f) for f in (base or FAQ_PADRAO)), key=lambda x: x[0])
    return melhor[1]["resposta"] if melhor[0] else None


def chamado(casa, resumo, diag):
    pasta = Path(casa) / "workspace" / "_operacao" / "suporte"; pasta.mkdir(parents=True, exist_ok=True)
    f = pasta / f"chamado-{datetime.now():%Y%m%d-%H%M%S}.md"
    vermelhos = [i for i in diag["itens"] if i["cor"] != "verde"]
    L = [f"# Chamado de suporte · {datetime.now():%Y-%m-%d %H:%M}", "", f"**Resumo:** {SEGREDO.sub('[mascarado]', resumo)}", "",
         f"**Diagnóstico geral:** {diag['geral']}", "", "| Item | Cor | Detalhe |", "|---|---|---|"]
    L += [f"| {i['item']} | {i['cor']} | {SEGREDO.sub('[mascarado]', i['detalhe'])} |" for i in diag["itens"]]
    L += ["", "**Itens a olhar primeiro:** " + (", ".join(i["item"] for i in vermelhos) or "nenhum"), "",
          "**Últimas linhas do log (mascaradas):**", "", "```", *diag.get("log", [])[-20:], "```", "",
          "_Enviar ao dono é com o prestador: este arquivo não sai sozinho._"]
    f.write_text("\n".join(L) + "\n", encoding="utf-8")
    return f


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["diagnostico", "faq", "chamado"])
    for o in ("--casa", "--home", "--saida", "--pergunta", "--faq", "--resumo", "--diagnostico"):
        ap.add_argument(o)
    a = ap.parse_args(argv)
    if a.cmd == "diagnostico":
        d = diagnostico(a.casa, a.home)
        if a.saida:
            Path(a.saida).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(d, ensure_ascii=False, indent=2)); return 0 if d["geral"] != "vermelho" else 3
    if a.cmd == "faq":
        base = json.loads(Path(a.faq).read_text(encoding="utf-8")) if a.faq else None
        r = faq(a.pergunta or "", base)
        print(json.dumps({"resposta": r, "proximo": None if r else "abrir chamado com o diagnóstico"}, ensure_ascii=False)); return 0 if r else 3
    d = json.loads(Path(a.diagnostico).read_text(encoding="utf-8"))
    print(json.dumps({"chamado": str(chamado(a.casa, a.resumo or "", d))}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    sys.exit(main())
