"""arkos-regressao: trava de regressão em toda mudança de código que já funciona.

  init     <repo> [--comando "..."]           roda os testes e grava a linha de base (o que passa hoje)
  raio     <repo> [arquivo ...]               quem depende dos arquivos mudados (sem arquivo: git diff)
  contrato <repo> --id X --descricao "..." --teste ID [--teste ID ...]   comportamento que não pode mudar
  check    <repo> [--aceitar]                 roda tudo e compara com a base; código 1 = regressão
  ler      <repo>                             mostra base, contratos e o último check

Estado em <repo>/.arkos-regressao/: config.json, base.json, contratos.json, historico.jsonl.
Formatos de teste lidos por teste: pytest (junit), node --test (junit) e go test -json.
Outro comando qualquer vale com --comando, mas aí só o código de saída conta (amarelo).
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arkos_casa as C  # noqa: E402

PASTA = ".arkos-regressao"
IGNORA = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", PASTA, ".pytest_cache"}


def _estado(repo, nome, padrao=None):
    p = os.path.join(repo, PASTA, nome)
    return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else padrao


def _salvar(repo, nome, obj):
    os.makedirs(os.path.join(repo, PASTA), exist_ok=True)
    with open(os.path.join(repo, PASTA, nome), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def _arquivos(repo):
    for raiz, dirs, fs in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in IGNORA]
        for f in fs:
            yield os.path.join(raiz, f)


def detectar(repo):
    fs = [os.path.relpath(f, repo).replace("\\", "/") for f in _arquivos(repo)]
    if any(re.search(r"(^|/)(test_[^/]*|[^/]*_test)\.py$", f) for f in fs) or os.path.isfile(os.path.join(repo, "pytest.ini")):
        return {"tipo": "pytest"}
    if os.path.isfile(os.path.join(repo, "go.mod")):
        return {"tipo": "go"}
    if any(re.search(r"\.test\.(m?js|cjs)$", f) for f in fs):
        return {"tipo": "node"}
    return None


def rodar_testes(repo, cfg):
    """Devolve ({id: 'pass'|'fail'}, codigo, saida_resumida). Sem detalhe por teste: {'(suite)': ...}."""
    with tempfile.TemporaryDirectory() as tmp:
        junit = os.path.join(tmp, "r.xml")
        t = cfg["tipo"]
        if t == "pytest":
            cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={junit}"]
        elif t == "node":
            cmd = ["node", "--test", "--test-reporter=junit", f"--test-reporter-destination={junit}"]
        elif t == "go":
            cmd = ["go", "test", "./...", "-json"]
        else:
            cmd = cfg["comando"] if isinstance(cfg["comando"], list) else ["cmd", "/c", cfg["comando"]] if os.name == "nt" else ["sh", "-c", cfg["comando"]]
        try:
            r = C.rodar_oculto(cmd, timeout=900, cwd=repo)
        except FileNotFoundError as e:
            C.saida("bloqueada", excecao="fora_do_ar", motivo=f"executor de teste não encontrado: {e}")
            sys.exit(C.FORA_DO_AR)
        if t == "pytest" and "No module named pytest" in r.stderr:
            C.saida("bloqueada", excecao="fora_do_ar", motivo="pytest não instalado neste Python",
                    como_resolver=f"{sys.executable} -m pip install pytest")
            sys.exit(C.FORA_DO_AR)
        res = {}
        if t in ("pytest", "node") and os.path.isfile(junit):
            for tc in ET.parse(junit).getroot().iter("testcase"):
                nome = f"{tc.get('classname') or tc.get('file') or ''}::{tc.get('name')}".strip(":")
                if tc.find("skipped") is not None:
                    continue
                falhou = tc.find("failure") is not None or tc.find("error") is not None
                res[nome] = "fail" if falhou else "pass"
        elif t == "go":
            for l in r.stdout.splitlines():
                try:
                    ev = json.loads(l)
                except ValueError:
                    continue
                if ev.get("Test") and ev.get("Action") in ("pass", "fail"):
                    res[f"{ev['Package']}::{ev['Test']}"] = ev["Action"]
        else:
            res["(suite)"] = "pass" if r.returncode == 0 else "fail"
        return res, r.returncode, (r.stdout + r.stderr)[-1500:]


def _repo_ok(repo):
    if not repo or not os.path.isdir(repo):
        C.saida("aguardando", excecao="entrada_incompleta", falta=[f"pasta do repositório não existe: {repo}"])
        sys.exit(C.ENTRADA_INCOMPLETA)


def init(a):
    _repo_ok(a.repo)
    cfg = {"tipo": "comando", "comando": a.comando} if a.comando else detectar(a.repo)
    if not cfg:
        C.saida("aguardando", excecao="entrada_incompleta",
                falta=["nenhum teste encontrado (pytest, node --test ou go test): escreva o primeiro teste do "
                       "comportamento que funciona hoje, ou passe --comando"])
        sys.exit(C.ENTRADA_INCOMPLETA)
    res, cod, out = rodar_testes(a.repo, cfg)
    if not res:
        C.saida("aguardando", excecao="entrada_incompleta", falta=["os testes rodaram mas nenhum resultado foi lido"], saida=out)
        sys.exit(C.ENTRADA_INCOMPLETA)
    passando = sorted(k for k, v in res.items() if v == "pass")
    falhando = sorted(k for k, v in res.items() if v == "fail")
    cfg["criado_em"] = dt.datetime.now().isoformat(timespec="seconds")
    _salvar(a.repo, "config.json", cfg)
    _salvar(a.repo, "base.json", {"data": cfg["criado_em"], "passando": passando})
    if _estado(a.repo, "contratos.json") is None:
        _salvar(a.repo, "contratos.json", [])
    C.saida("ok" if not falhando else "amarelo", tipo=cfg["tipo"], base=len(passando), ja_falhando=falhando,
            nota="teste que já falha hoje não entra na base: não é regressão, é dívida" if falhando else "")


def _deps_de(repo, alvo):
    rel = os.path.relpath(alvo, repo).replace("\\", "/")
    stem = os.path.splitext(os.path.basename(rel))[0]
    pacote = os.path.dirname(rel)
    padroes = [rf"^\s*(from|import)\s+[\w.]*\b{re.escape(stem)}\b",
               rf"(require\(|from\s+|import\s*\()\s*['\"][^'\"]*/{re.escape(stem)}(\.\w+)?['\"]"]
    if pacote and alvo.endswith(".go"):
        padroes.append(rf"\"[^\"]*/{re.escape(pacote)}\"")
    rx = re.compile("|".join(padroes), re.M)
    out = []
    for f in _arquivos(repo):
        if os.path.abspath(f) == os.path.abspath(alvo) or not f.endswith((".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go")):
            continue
        try:
            if rx.search(open(f, encoding="utf-8", errors="replace").read()):
                out.append(os.path.relpath(f, repo).replace("\\", "/"))
        except OSError:
            pass
    return out


def raio(a):
    _repo_ok(a.repo)
    arqs = a.arquivos
    if not arqs:
        r = C.rodar_oculto(["git", "diff", "--name-only", "HEAD"], cwd=a.repo)
        arqs = [l for l in r.stdout.splitlines() if l.strip()]
    if not arqs:
        C.saida("aguardando", excecao="entrada_incompleta", falta=["nenhum arquivo mudado (passe os arquivos ou tenha diff no git)"])
        sys.exit(C.ENTRADA_INCOMPLETA)
    mapa, testes = {}, set()
    for f in arqs:
        caminho = f if os.path.isabs(f) else os.path.join(a.repo, f)
        deps = _deps_de(a.repo, caminho)
        mapa[f] = deps
        testes |= {d for d in deps if re.search(r"(test_|_test\.|\.test\.)", d)}
    contratos = _estado(a.repo, "contratos.json", [])
    C.saida("ok", mudados=arqs, dependentes=mapa, testes_que_cobrem=sorted(testes),
            contratos=[c["id"] for c in contratos],
            sem_cobertura=[f for f, d in mapa.items() if not any(re.search(r"(test_|_test\.|\.test\.)", x) for x in d)])


def contrato(a):
    _repo_ok(a.repo)
    base = _estado(a.repo, "base.json")
    if base is None:
        C.saida("aguardando", excecao="entrada_incompleta", falta=["rode 'init' antes"])
        sys.exit(C.ENTRADA_INCOMPLETA)
    falta = [t for t in a.teste if t not in base["passando"]]
    if falta or not a.descricao:
        C.saida("aguardando", excecao="entrada_incompleta",
                falta=([f"teste fora da base (precisa existir e passar): {t}" for t in falta] + ([] if a.descricao else ["--descricao"])))
        sys.exit(C.ENTRADA_INCOMPLETA)
    cs = [c for c in _estado(a.repo, "contratos.json", []) if c["id"] != a.id]
    cs.append({"id": a.id, "descricao": a.descricao, "testes": a.teste, "criado_em": dt.date.today().isoformat()})
    _salvar(a.repo, "contratos.json", cs)
    C.saida("ok", contratos=len(cs), contrato=a.id)


def check(a):
    _repo_ok(a.repo)
    cfg, base = _estado(a.repo, "config.json"), _estado(a.repo, "base.json")
    if not cfg or not base:
        C.saida("aguardando", excecao="entrada_incompleta", falta=["rode 'init' antes do primeiro check"])
        sys.exit(C.ENTRADA_INCOMPLETA)
    res, cod, out = rodar_testes(a.repo, cfg)
    regressoes = sorted(t for t in base["passando"] if res.get(t) == "fail")
    sumidos = sorted(t for t in base["passando"] if t not in res)
    novos_falhando = sorted(t for t, v in res.items() if v == "fail" and t not in base["passando"])
    novos_passando = sorted(t for t, v in res.items() if v == "pass" and t not in base["passando"])
    quebrados = [c["id"] for c in _estado(a.repo, "contratos.json", []) if any(res.get(t) != "pass" for t in c["testes"])]
    probs = ([f"regressão: {t}" for t in regressoes] + [f"teste sumiu (apagado ou renomeado): {t}" for t in sumidos]
             + [f"teste novo falhando: {t}" for t in novos_falhando] + [f"contrato quebrado: {c}" for c in quebrados])
    estado = "verde" if not probs else "vermelho"
    if cfg["tipo"] == "comando" and estado == "verde":
        estado = "amarelo"
    reg = {"data": dt.datetime.now().isoformat(timespec="seconds"), "estado": estado, "regressoes": regressoes,
           "sumidos": sumidos, "novos_falhando": novos_falhando, "contratos_quebrados": quebrados, "total": len(res)}
    os.makedirs(os.path.join(a.repo, PASTA), exist_ok=True)
    with open(os.path.join(a.repo, PASTA, "historico.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")
    if estado != "vermelho" and a.aceitar and novos_passando:
        base["passando"] = sorted(set(base["passando"]) | set(novos_passando))
        base["data"] = reg["data"]
        _salvar(a.repo, "base.json", base)
    C.saida(estado, problemas=probs, novos_passando=novos_passando, base_atualizada=bool(a.aceitar and novos_passando and estado != "vermelho"),
            saida=out[-600:] if probs else "",
            nota="só o código de saída: sem resultado por teste" if cfg["tipo"] == "comando" else "")
    sys.exit(0 if estado != "vermelho" else 1)


def ler(a):
    _repo_ok(a.repo)
    hist = os.path.join(a.repo, PASTA, "historico.jsonl")
    ult = open(hist, encoding="utf-8").read().splitlines()[-1] if os.path.isfile(hist) else None
    C.saida("ok", config=_estado(a.repo, "config.json"), base=len((_estado(a.repo, "base.json") or {}).get("passando", [])),
            contratos=_estado(a.repo, "contratos.json", []), ultimo_check=json.loads(ult) if ult else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("repo")
    i.add_argument("--comando")
    r = sub.add_parser("raio")
    r.add_argument("repo")
    r.add_argument("arquivos", nargs="*")
    c = sub.add_parser("contrato")
    c.add_argument("repo")
    c.add_argument("--id", required=True)
    c.add_argument("--descricao")
    c.add_argument("--teste", action="append", default=[])
    k = sub.add_parser("check")
    k.add_argument("repo")
    k.add_argument("--aceitar", action="store_true")
    sub.add_parser("ler").add_argument("repo")
    a = ap.parse_args()
    {"init": init, "raio": raio, "contrato": contrato, "check": check, "ler": ler}[a.cmd](a)


if __name__ == "__main__":
    main()
