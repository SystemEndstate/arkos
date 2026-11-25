"""notas.py — sistema de notas da ARKOS (skill arkos-notas).

Pontua um objeto contra uma régua (JSON) e devolve nota, veredito e o que sobe a nota.

Regras (engine/FLUXOS-POR-PLANO-E-NOTAS.md, parte 2):
- nota 0–100 por critério, cada uma com evidência;
- nota final = média ponderada dos critérios (pesos renormalizados sobre os ativos);
- corte FIXO (decisão do usuário): aprovar >= 75 · ajustar 50–74 · descartar < 50;
- critério sem evidência NÃO pontua: conta 0;
- se mais de 40% do peso ativo ficar sem evidência, o veredito é 'insuficiente'
  (nota não confiável) — nem aprovar, nem ajustar, nem descartar;
- plano: régua de acesso 'vip' não existe para membro; critério 'vip' sai do cálculo
  do membro e os pesos se renormalizam sobre os ativos;
- Jev (Sistema 1) pode pontuar cada critério (--jev); se falhar, cai para a nota
  fornecida pelo Claude, sem travar;
- cada pontuação vira uma linha em aprendizado.jsonl (nota x resultado real depois).

Uso:
  python notas.py pontuar --regua oferta --plano membro --entrada aval.json \
      [--jev] [--reguas-dir DIR] [--aprendizado CAMINHO] [--out r.json]
  python notas.py pronto r.json

  python notas.py resultado --aprendizado CAMINHO --id ID
      [--gasto N] [--pedidos N] [--lucro-d30 N] [--lucro-d60 N]
      [--decisao TEXTO] [--override-dono TEXTO]

  aval.json:
    {"objeto": "garantia-30-dias",
     "perfil": "loja",                      # opcional: perfil de pesos da régua
     "nao_aplica": ["oferta_ecommerce"],    # opcional
     "bandeiras": ["ia_efeito_categoria_vetada"],  # opcional: vetos duros da régua
     "contexto": {"vertical": "...", "canal": "...", "aov": 0, "cm2": 0},  # opcional, vai ao aprendizado
     "criterios": {"garantia": {"nota": 80, "evidencia": "texto da garantia ..."}, ...}}

Perfis (régua): "perfis": {"loja": {"pesos": {id: peso}, "veto": {id: limiar}}} troca pesos
e vetos só quando a entrada pede o perfil; sem perfil, vale o peso/veto do critério.
Veto: critério com "veto": true reprova com nota efetiva < "veto_abaixo" (padrão 25).
Vetos duros: "vetos_duros": [{"id": ..., "descricao": ...}]; bandeira presente na entrada = descartar.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

APROVAR = 75.0          # >= 75 aprovar
AJUSTAR = 50.0          # 50–74 ajustar; < 50 descartar
LIMITE_SEM_EVIDENCIA = 0.40   # mais de 40% do peso ativo sem evidência = insuficiente
VETO_PADRAO = 25.0      # critério-portão com nota efetiva abaixo disto reprova


class Bloqueada(Exception):
    """Régua de acesso vip pedida para um plano membro."""


def carregar_regua(regua: str, reguas_dir: str | None = None) -> dict:
    """Aceita um caminho de arquivo ou um id (resolvido em reguas_dir ou na pasta reguas/ da skill)."""
    p = Path(regua)
    if p.suffix == ".json" and p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    base = Path(reguas_dir) if reguas_dir else Path(__file__).resolve().parents[1] / "reguas"
    cand = base / f"{regua}.json"
    if not cand.exists():
        raise FileNotFoundError(f"régua não encontrada: {regua} (procurei em {cand})")
    return json.loads(cand.read_text(encoding="utf-8"))


def criterios_do_plano(regua: dict, plano: str) -> list[dict]:
    """Critérios ativos para o plano. Levanta Bloqueada se a régua inteira for vip e o plano membro."""
    if str(regua.get("acesso", "todos")).lower() == "vip" and plano == "membro":
        raise Bloqueada(f"régua '{regua.get('regua')}' é do plano VIP")
    ativos = []
    for c in regua.get("criterios", []):
        if str(c.get("acesso", "todos")).lower() == "vip" and plano == "membro":
            continue
        ativos.append(c)
    if not ativos:
        raise ValueError("régua sem critérios ativos para o plano")
    return ativos


def _jev_pontuar(criterio: dict, evidencia: str):
    """Pontua um critério via Jev (Sistema 1). Devolve 0–100 ou None se o Jev falhar."""
    try:
        jevdir = os.path.expanduser(os.path.join("~", ".claude", "jev"))
        if jevdir not in sys.path:
            sys.path.insert(0, jevdir)
        import jev  # noqa: PLC0415

        pergunta = criterio.get("pergunta") or criterio.get("nome") or criterio.get("id")
        ctx = jev.redact(f"{pergunta}\nEvidência apresentada: {evidencia}")
        r = jev.decide(ctx, {
            "nota": {"type": "score", "instructions": pergunta,
                     "criteria": ["0-24 ruim", "25-49 fraco", "50-74 ok", "75-89 bom", "90-100 excelente"]},
        })
        score = float(r["answers"]["nota"]["score"])  # escala 0..4
        return round(score / 4 * 100)
    except Exception:  # noqa: BLE001 — Jev é best-effort; qualquer falha cai para a nota do Claude
        return None


def aplicar_perfil(regua: dict, ativos: list[dict], perfil: str | None) -> list[dict]:
    """Devolve cópias dos critérios com peso/veto do perfil pedido. Sem perfil, devolve como está."""
    if not perfil:
        return ativos
    perfis = regua.get("perfis", {}) or {}
    if perfil not in perfis:
        raise ValueError(f"perfil desconhecido para a régua '{regua.get('regua')}': {perfil} "
                         f"(existem: {', '.join(sorted(perfis)) or 'nenhum'})")
    cfg = perfis[perfil] or {}
    pesos = cfg.get("pesos", {}) or {}
    vetos = cfg.get("veto", {}) or {}
    out = []
    for c in ativos:
        c2 = dict(c)
        if c["id"] in pesos:
            c2["peso"] = float(pesos[c["id"]])
        if c["id"] in vetos:
            lim = vetos[c["id"]]
            if lim is None or lim is False:
                c2["veto"] = False
            else:
                c2["veto"] = True
                c2["veto_abaixo"] = float(lim)
        out.append(c2)
    return out


def pontuar(regua: dict, aval: dict, plano: str = "membro", jev: bool = False) -> dict:
    perfil = aval.get("perfil") or None
    ativos = aplicar_perfil(regua, criterios_do_plano(regua, plano), perfil)
    entradas = aval.get("criterios", {})
    nao_aplica = set(aval.get("nao_aplica", []))
    # peso de referência = só os critérios que se aplicam (inaplicável sai da conta e renormaliza)
    total_peso = sum(float(c["peso"]) for c in ativos if c["id"] not in nao_aplica) or 1.0

    linhas = []
    jev_usado = jev_falhou = False
    for c in ativos:
        cid = c["id"]
        e = entradas.get(cid, {}) or {}
        evid = str(e.get("evidencia", "") or "").strip()
        nota = e.get("nota")
        origem = "claude"
        if cid in nao_aplica:
            # critério não aplicável (ex.: autenticidade UGC numa peça que não é UGC): fora do cálculo
            nota_efetiva, origem = None, "nao_aplica"
        else:
            if jev and evid and nota is None:
                nota = _jev_pontuar(c, evid)
                if nota is None:
                    jev_falhou = True
                else:
                    jev_usado = True
                    origem = "jev"
            if not evid:
                nota_efetiva = 0.0           # critério sem evidência não pontua: conta 0
                origem = "sem_evidencia"
            elif nota is None:
                nota_efetiva = None          # com evidência mas ainda sem nota: pendente, fica fora do cálculo
                origem = "pendente"
            else:
                nota = float(nota)
                if not 0 <= nota <= 100:
                    raise ValueError(f"{cid}: nota deve ficar entre 0 e 100")
                nota_efetiva = nota
        linhas.append({
            "criterio": cid, "nome": c.get("nome", cid), "peso": float(c["peso"]),
            "acesso": c.get("acesso", "todos"), "veto": bool(c.get("veto", False)),
            "veto_abaixo": float(c.get("veto_abaixo", VETO_PADRAO)),
            "nota": nota_efetiva, "origem": origem,
            "evidencia": evid, "evidencia_exigida": c.get("evidencia_exigida", []),
            "faixas": c.get("faixas", []),
        })

    peso_sem_evid = sum(l["peso"] for l in linhas if l["origem"] == "sem_evidencia")
    peso_pendente = sum(l["peso"] for l in linhas if l["origem"] == "pendente")
    insuficiente = peso_sem_evid / total_peso > LIMITE_SEM_EVIDENCIA

    com_nota = [l for l in linhas if l["nota"] is not None]
    denom = sum(l["peso"] for l in com_nota) or 1.0
    bruto = sum(l["nota"] * l["peso"] for l in com_nota) / denom
    nota_final = round(bruto + 1e-9, 1)

    # veto: critério-portão (política, lei, teste observável) com nota efetiva < 25 reprova,
    # qualquer que seja a nota final. Portão não provado (sem evidência = 0) também reprova.
    vetos = [l["criterio"] for l in linhas
             if l["veto"] and l["nota"] is not None and l["nota"] < l["veto_abaixo"]]

    # vetos duros: bandeira declarada na entrada (ex.: IA demonstrando efeito em categoria vetada)
    duros = {v["id"]: v for v in regua.get("vetos_duros", []) or []}
    pedidas = list(aval.get("bandeiras", []) or [])
    desconhecidas = [b for b in pedidas if b not in duros]
    if desconhecidas:
        raise ValueError(f"bandeira desconhecida para a régua '{regua.get('regua')}': {', '.join(desconhecidas)}")
    bandeiras = sorted(set(pedidas))

    if vetos or bandeiras:
        veredito = "descartar"
    elif insuficiente:
        veredito = "insuficiente"
    elif nota_final >= APROVAR:
        veredito = "aprovar"
    elif nota_final >= AJUSTAR:
        veredito = "ajustar"
    else:
        veredito = "descartar"

    # o que sobe a nota: 3 correções por impacto = peso * (100 - nota)
    melhoraveis = [l for l in linhas if l["nota"] is not None and l["nota"] < 100]
    melhoraveis.sort(key=lambda l: l["peso"] * (100 - l["nota"]), reverse=True)
    o_que_sobe = [{
        "criterio": l["criterio"], "nome": l["nome"], "nota_atual": l["nota"],
        "impacto": round(l["peso"] * (100 - l["nota"]), 2),
        "como": ("apresentar evidência" if l["origem"] == "sem_evidencia"
                 else "subir a faixa com prova mais forte"),
        "evidencia_exigida": l["evidencia_exigida"],
    } for l in melhoraveis[:3]]

    return {
        "status": "ok",
        "regua": regua.get("regua"),
        "objeto": aval.get("objeto"),
        "plano": plano,
        "perfil": perfil,
        "nota": nota_final,
        "veredito": veredito,
        "corte": {"aprovar": APROVAR, "ajustar": AJUSTAR},
        "insuficiente": insuficiente,
        "vetos": vetos,
        "bandeiras": [{"id": b, "descricao": duros[b].get("descricao", "")} for b in bandeiras],
        "nao_aplica": sorted(nao_aplica),
        "peso_sem_evidencia": round(peso_sem_evid / total_peso, 2),
        "peso_pendente": round(peso_pendente / total_peso, 2),
        "parcial": peso_pendente > 0,
        "jev": {"usado": jev_usado, "falhou": jev_falhou},
        "criterios": linhas,
        "o_que_sobe_a_nota": o_que_sobe,
        "contexto": aval.get("contexto") or {},
    }


CAMPOS_RESULTADO = ("gasto", "pedidos", "lucro_d30", "lucro_d60", "decisao", "override_dono")


def registrar(resultado: dict, caminho: str) -> str:
    """Acrescenta a pontuação em aprendizado.jsonl e devolve o id da linha.

    Grava a nota de cada critério (para medir Spearman critério x lucro D60 com 30+ casos),
    perfil, nao_aplica, vetos, bandeiras e o contexto (vertical, canal, AOV, CM2...).
    O resultado real entra depois pelo comando `resultado` (linha tipo 'resultado' com o mesmo id).
    """
    rid = f"{resultado.get('regua')}-{time.time_ns()}"
    linha = {
        "id": rid,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tipo": "nota",
        "regua": resultado.get("regua"),
        "objeto": resultado.get("objeto"),
        "plano": resultado.get("plano"),
        "perfil": resultado.get("perfil"),
        "nota": resultado.get("nota"),
        "veredito": resultado.get("veredito"),
        "vetos": resultado.get("vetos", []),
        "bandeiras": [b["id"] for b in resultado.get("bandeiras", [])],
        "nao_aplica": resultado.get("nao_aplica", []),
        "notas_criterios": {l["criterio"]: l["nota"] for l in resultado.get("criterios", [])},
        "contexto": resultado.get("contexto", {}),
        "resultado_real": None,  # preenchido depois por linha tipo "resultado" (CAMPOS_RESULTADO)
    }
    p = Path(caminho)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    return rid


def registrar_resultado(caminho: str, rid: str, **valores) -> dict:
    """Acrescenta o resultado real (gasto, pedidos, lucro D30/D60, decisão, override do dono) ao id.

    Append-only: não reescreve a linha da nota; grava uma linha 'resultado' que aponta para ela.
    """
    p = Path(caminho)
    if not p.exists():
        raise FileNotFoundError(f"aprendizado não encontrado: {caminho}")
    ids = set()
    for raw in p.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            o = json.loads(raw)
        except ValueError:
            continue
        if o.get("tipo") == "nota" and o.get("id"):
            ids.add(o["id"])
    if rid not in ids:
        raise KeyError(f"id de nota não encontrado no aprendizado: {rid}")
    linha = {"id": rid, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "tipo": "resultado"}
    for k in CAMPOS_RESULTADO:
        if valores.get(k) is not None:
            linha[k] = valores[k]
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    return linha


def pronto(resultado: dict) -> list[str]:
    """Problemas que travam o gate. Lista vazia = verde. Nota baixa NÃO trava (é decisão do fluxo)."""
    p = []
    if resultado.get("status") != "ok":
        p.append(f"status {resultado.get('status')}: pontuação não concluída")
        return p
    if resultado.get("veredito") == "insuficiente":
        p.append(f"veredito insuficiente: {resultado.get('peso_sem_evidencia')} do peso sem evidência (> {LIMITE_SEM_EVIDENCIA})")
    pend = [l["criterio"] for l in resultado.get("criterios", []) if l.get("origem") == "pendente"]
    if pend:
        p.append("critério com evidência mas sem nota (pendente): " + ", ".join(pend))
    return p


def _opt(argv, nome, default=None):
    return argv[argv.index(nome) + 1] if nome in argv else default


def _main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "pronto":
        resultado = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        probs = pronto(resultado)
        print(json.dumps({"pronto": not probs, "problemas": probs}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "resultado":
        caminho, rid = _opt(argv, "--aprendizado"), _opt(argv, "--id")
        if not caminho or not rid:
            print(__doc__)
            return 2
        num = {}
        for k in ("gasto", "pedidos", "lucro_d30", "lucro_d60"):
            v = _opt(argv, "--" + k.replace("_", "-"))
            if v is not None:
                num[k] = float(v)
        linha = registrar_resultado(caminho, rid, decisao=_opt(argv, "--decisao"),
                                    override_dono=_opt(argv, "--override-dono"), **num)
        print(json.dumps(linha, ensure_ascii=False, indent=2))
        return 0
    if cmd != "pontuar":
        print(f"comando desconhecido: {cmd}")
        return 2
    regua_arg = _opt(argv, "--regua")
    entrada = _opt(argv, "--entrada")
    if not regua_arg or not entrada:
        print(__doc__)
        return 2
    plano = (_opt(argv, "--plano", "membro") or "membro").lower()
    regua = carregar_regua(regua_arg, _opt(argv, "--reguas-dir"))
    aval = json.loads(Path(entrada).read_text(encoding="utf-8"))
    try:
        r = pontuar(regua, aval, plano=plano, jev="--jev" in argv)
    except Bloqueada as ex:
        r = {"status": "bloqueada", "motivo": str(ex), "plano": plano}
    aprend = _opt(argv, "--aprendizado")
    if aprend and r.get("status") == "ok":
        r["aprendizado_id"] = registrar(r, aprend)
    saida = _opt(argv, "--out")
    if saida:
        Path(saida).parent.mkdir(parents=True, exist_ok=True)
        Path(saida).write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
