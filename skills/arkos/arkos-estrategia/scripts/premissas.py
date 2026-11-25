"""premissas.py - lê, valida e atualiza o registro de premissas da suíte arkos-estrategia.

Só biblioteca padrão. Lê o subconjunto de YAML que a suíte usa (lista de mapas com
escalares, listas inline e listas em bloco) ou JSON. Escreve sempre o mesmo YAML.

Uso:
  python premissas.py validar premissas.yaml
  python premissas.py ajustar premissas.yaml julgamentos.json [--hoje AAAA-MM-DD] [--antes copia.yaml]
  python premissas.py proximo-id premissas.yaml

julgamentos.json: [{"id": "P-007", "direcao": "sobe|mantem|baixa|refuta",
                    "evidencia": "texto", "status": "testando|validada"?}]
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from pathlib import Path

CATEGORIAS = {"cliente", "problema", "canal", "preco", "custo", "operacao", "mercado", "regulatorio"}
IMPACTOS = {"alto", "medio", "baixo"}
STATUS = {"aberta", "testando", "validada", "refutada"}
OBRIGATORIOS = ("id", "afirmacao", "categoria", "origem", "confianca", "impacto", "status")
ORDEM = ("id", "afirmacao", "categoria", "origem", "confianca", "impacto", "evidencia",
         "teste", "prazo_teste", "custo_teste", "status", "substituida_por", "atualizado_em")

# regra de confiança (especificação interna)
PASSO = {"sobe": 0.15, "mantem": 0.0, "baixa": -0.20}
MIN_CONF, MAX_CONF, CONF_REFUTADA = 0.05, 0.95, 0.05


# ---------- YAML (subconjunto) ----------

def _escalar(txt: str):
    s = txt.strip()
    if s == "" or s in ("~", "null"):
        return None
    if s[0] in "\"'":
        q = s[0]
        fim = s.rfind(q)
        corpo = s[1:fim]
        return corpo.replace('\\"', '"') if q == '"' else corpo.replace("''", "'")
    s = _sem_comentario(s)
    if s.startswith("[") and s.endswith("]"):
        miolo = s[1:-1].strip()
        return [] if not miolo else [_escalar(p) for p in _dividir(miolo)]
    if s in ("true", "false"):
        return s == "true"
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d*", s):
        return float(s)
    return s


def _sem_comentario(s: str) -> str:
    dentro = None
    for i, c in enumerate(s):
        if c in "\"'":
            dentro = None if dentro == c else (c if dentro is None else dentro)
        elif c == "#" and dentro is None and (i == 0 or s[i - 1] == " "):
            return s[:i].rstrip()
    return s


def _dividir(miolo: str) -> list[str]:
    partes, atual, dentro = [], "", None
    for c in miolo:
        if c in "\"'":
            dentro = None if dentro == c else (c if dentro is None else dentro)
        if c == "," and dentro is None:
            partes.append(atual)
            atual = ""
        else:
            atual += c
    partes.append(atual)
    return [p.strip() for p in partes]


def ler_yaml(texto: str) -> list[dict]:
    itens: list[dict] = []
    atual: dict | None = None
    chave_lista: str | None = None
    for bruta in texto.splitlines():
        if not bruta.strip() or bruta.lstrip().startswith("#"):
            continue
        recuo = len(bruta) - len(bruta.lstrip())
        linha = bruta.strip()
        if recuo == 0 and linha.startswith("- "):
            atual = {}
            itens.append(atual)
            linha = linha[2:]
            chave_lista = None
        elif atual is None:
            raise ValueError(f"linha fora de item: {bruta!r}")
        if chave_lista and linha.startswith("- ") and recuo > 2:
            atual[chave_lista].append(_escalar(linha[2:]))
            continue
        m = re.match(r"([A-Za-z_][\w]*):\s*(.*)$", linha)
        if not m:
            raise ValueError(f"linha inválida: {bruta!r}")
        chave, resto = m.group(1), m.group(2)
        if _sem_comentario(resto).strip() == "":
            atual[chave] = []
            chave_lista = chave
        else:
            atual[chave] = _escalar(resto)
            chave_lista = None
    return itens


def _fmt(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(round(v, 4)) if isinstance(v, float) else str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_fmt(x) for x in v) + "]"
    s = str(v)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) or re.fullmatch(r"[A-Za-z][\w\-]*", s):
        return s
    return '"' + s.replace('"', '\\"') + '"'


def escrever_yaml(itens: list[dict]) -> str:
    linhas = []
    for item in itens:
        chaves = [k for k in ORDEM if k in item] + [k for k in item if k not in ORDEM]
        for i, k in enumerate(chaves):
            linhas.append(("- " if i == 0 else "  ") + f"{k}: {_fmt(item[k])}")
    return "\n".join(linhas) + "\n"


def carregar(caminho: str | Path) -> list[dict]:
    p = Path(caminho)
    texto = p.read_text(encoding="utf-8")
    return json.loads(texto) if p.suffix == ".json" else ler_yaml(texto)


def salvar(caminho: str | Path, itens: list[dict]) -> None:
    p = Path(caminho)
    conteudo = json.dumps(itens, ensure_ascii=False, indent=2) if p.suffix == ".json" else escrever_yaml(itens)
    p.write_text(conteudo, encoding="utf-8")


# ---------- regras ----------

def validar(itens: list[dict]) -> list[str]:
    erros, vistos = [], set()
    for n, p in enumerate(itens):
        rot = p.get("id", f"#{n}")
        for k in OBRIGATORIOS:
            if p.get(k) in (None, ""):
                erros.append(f"{rot}: falta '{k}'")
        if p.get("id") in vistos:
            erros.append(f"{rot}: id repetido")
        vistos.add(p.get("id"))
        if p.get("id") and not re.fullmatch(r"P-\d{3,}", str(p["id"])):
            erros.append(f"{rot}: id fora do padrão P-000")
        if p.get("categoria") and p["categoria"] not in CATEGORIAS:
            erros.append(f"{rot}: categoria '{p['categoria']}' inválida")
        if p.get("impacto") and p["impacto"] not in IMPACTOS:
            erros.append(f"{rot}: impacto '{p['impacto']}' inválido")
        if p.get("status") and p["status"] not in STATUS:
            erros.append(f"{rot}: status '{p['status']}' inválido")
        c = p.get("confianca")
        if c is not None:
            if not isinstance(c, (int, float)) or not (0 < c < 1):
                erros.append(f"{rot}: confianca deve ficar entre 0 e 1, sem os extremos")
        if p.get("evidencia") is not None and not isinstance(p["evidencia"], list):
            erros.append(f"{rot}: evidencia deve ser lista")
    return erros


def nova_confianca(atual: float, direcao: str) -> float:
    if direcao == "refuta":
        return CONF_REFUTADA
    if direcao not in PASSO:
        raise ValueError(f"direção inválida: {direcao}")
    return round(min(MAX_CONF, max(MIN_CONF, atual + PASSO[direcao])), 2)


def ajustar(itens: list[dict], julgamentos: list[dict], hoje: str) -> list[dict]:
    """Aplica a regra de confiança. Devolve a lista de mudanças (antes/depois)."""
    por_id = {p["id"]: p for p in itens}
    mudancas = []
    for j in julgamentos:
        p = por_id.get(j["id"])
        if p is None:
            raise KeyError(f"premissa {j['id']} não existe")
        antes = {"confianca": p["confianca"], "status": p["status"]}
        p["confianca"] = nova_confianca(float(p["confianca"]), j["direcao"])
        if j["direcao"] == "refuta":
            p["status"] = "refutada"
        elif j.get("status"):
            if j["status"] == "refutada":
                raise ValueError(f"{j['id']}: para refutar use direcao 'refuta'")
            if j["status"] not in STATUS:
                raise ValueError(f"{j['id']}: status inválido")
            p["status"] = j["status"]
        if j.get("evidencia"):
            p.setdefault("evidencia", [])
            p["evidencia"].append(j["evidencia"])
        p["atualizado_em"] = hoje
        mudancas.append({"id": p["id"], "antes": antes,
                         "depois": {"confianca": p["confianca"], "status": p["status"]},
                         "direcao": j["direcao"]})
    return mudancas


def proximo_id(itens: list[dict]) -> str:
    nums = [int(str(p["id"])[2:]) for p in itens if re.fullmatch(r"P-\d+", str(p.get("id", "")))]
    return f"P-{(max(nums) + 1 if nums else 1):03d}"


def critica(p: dict) -> bool:
    return p.get("impacto") == "alto" and float(p.get("confianca", 0)) < 0.5 and p.get("status") != "validada"


# ---------- CLI ----------

def _main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd, arq = argv[0], argv[1]
    itens = carregar(arq)
    if cmd == "validar":
        erros = validar(itens)
        print(json.dumps({"ok": not erros, "erros": erros, "total": len(itens)}, ensure_ascii=False, indent=2))
        return 0 if not erros else 1
    if cmd == "proximo-id":
        print(proximo_id(itens))
        return 0
    if cmd == "ajustar":
        julg = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        hoje = _opt(argv, "--hoje") or _dt.date.today().isoformat()
        copia = _opt(argv, "--antes")
        erros = validar(itens)
        if erros:
            print(json.dumps({"ok": False, "erros": erros}, ensure_ascii=False, indent=2))
            return 1
        if copia:
            Path(copia).write_text(Path(arq).read_text(encoding="utf-8"), encoding="utf-8")
        mud = ajustar(itens, julg, hoje)
        salvar(arq, itens)
        print(json.dumps({"ok": True, "mudancas": mud}, ensure_ascii=False, indent=2))
        return 0
    print(__doc__)
    return 2


def _opt(argv: list[str], nome: str) -> str | None:
    return argv[argv.index(nome) + 1] if nome in argv else None


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
