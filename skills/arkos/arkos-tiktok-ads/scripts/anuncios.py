"""anuncios.py - leitura de export de anúncios de vídeo curto (TikTok Ads, Kwai for Business).

Lê o CSV exportado do gerenciador, acha as colunas pelo nome (pt-BR ou inglês), calcula as métricas
e dá uma decisão por anúncio: escalar, manter, pausar, trocar criativo ou aguardar (dado insuficiente).
Todos os limiares são HEURÍSTICAS da ARKOS, rotuladas como tal e ajustáveis por --limiar chave=valor.
Nada aqui fala com API nem escreve em conta: só lê o arquivo.

Uso:
  python anuncios.py ler export.csv --cpa-alvo 40 [--roas-alvo 2] [--plataforma tiktok|kwai]
                     [--dias 7] [--anterior export_anterior.csv] [--retargeting]
                     [--map map.json] [--limiar hook_min=0.3] [--out leitura.json] [--md leitura.md]
  python anuncios.py pronto leitura.json
  --dias: dias que o grupo está no ar (libera escalar com 10+ conv e pausar por CPA alto).
  --anterior: export da leitura anterior, para medir fadiga (queda de CTR/2s). --retargeting: liga o sinal de frequência.
Saída 0 = ok; 1 = pronto reprovado; 2 = entrada incompleta (colunas faltando, arquivo vazio).
"""
from __future__ import annotations

import csv
import io
import json
import re
import statistics
import sys
import unicodedata
from pathlib import Path

# nome canônico -> apelidos (normalizados: minúsculo, sem acento, só letras/números)
ALIASES = {
    "anuncio": ["ad name", "nome do anuncio", "anuncio", "ad", "creative name", "nome do criativo", "criativo"],
    "gasto": ["cost", "custo", "spend", "valor gasto", "gasto", "amount spent", "consumo"],
    "impressoes": ["impressions", "impressoes", "exibicoes"],
    "cliques": ["clicks destination", "clicks", "cliques destino", "cliques", "cliques no link"],
    "conversoes": ["conversions", "conversoes", "resultados", "results", "purchases", "compras",
                   "complete payment", "pagamento concluido", "conversoes otimizadas"],
    "receita": ["total complete payment", "valor total de pagamento concluido", "receita", "revenue",
                "purchase value", "valor de compra", "conversion value", "valor de conversao"],
    "views_2s": ["2 second video views", "video views at 2s", "visualizacoes de video de 2 segundos",
                 "visualizacoes de 2s", "reproducoes de 2s", "2s views", "visualizacoes 2s"],
    "views_6s": ["6 second video views", "video views at 6s", "visualizacoes de video de 6 segundos",
                 "visualizacoes de 6s", "reproducoes de 6s", "6s views", "visualizacoes 6s"],
    "views_100": ["video views at 100", "visualizacoes de video a 100", "reproducoes completas",
                  "visualizacoes completas", "completed views", "video completions"],
    "frequencia": ["frequency", "frequencia"],
    "alcance": ["reach", "alcance"],
}
OBRIGATORIAS = ("anuncio", "gasto", "impressoes", "cliques", "conversoes")

# Heurísticas da ARKOS (não são regra da plataforma). Ajuste por cliente com --limiar.
# escalar_passo_min/max: degrau de orçamento por vez. A página de lance recomenda 20-30%; boas práticas de
# orçamento (ago/2026) dizem que depois do aprendizado dá para subir até 50% sem reentrar no aprendizado,
# esperando >= 2 dias entre mudanças. A ARKOS usa 20-30% (50% só em data sazonal, com saída registrada).
# escala_orc_x_cpa: a campanha de escala precisa de orçamento >= 10x o CPA para sair do aprendizado (doc
# oficial); sem CPA histórico, mínimo oficial de US$ 200/dia. O teste a 1-2x CPA é só leitura de sinal.
# escalar_conv_min 25 = doc oficial jun/2026 (a oscilação cai depois de ~25 resultados ou 7 dias); 10+
# conversões só valem para escalar se o grupo tem >= dias_min_escala dias no ar (--dias).
# pausar por CPA alto (pausar_cpa_x) só com pausar_cpa_dias_min+ dias ou pausar_cpa_conv_min+ resultados;
# antes disso o aprendizado ainda oscila (~7 dias) e a decisão é 'aguardar'. A regra de 0 conversão
# (pausar_sem_conv_x_cpa) continua sem prazo.
# fadiga = CTR ou taxa de 2 s caindo >= fadiga_queda contra o export anterior (--anterior). A frequência é
# sinal secundário só em retargeting (freq_max 2,0, --retargeting), experimental até o aprendizado confirmar.
# hook: com 10+ anúncios no export, usa-se o relativo (abaixo de hook_rel × a mediana da conta) no lugar de hook_min.
LIMIARES = {
    "tiktok": {"impr_min": 1000, "gasto_min_x_cpa": 1.0, "pausar_sem_conv_x_cpa": 2.0, "pausar_cpa_x": 1.5,
               "pausar_cpa_dias_min": 7, "pausar_cpa_conv_min": 25,
               "escalar_cpa_x": 0.8, "escalar_conv_min": 25, "escalar_conv_min_dias": 10, "dias_min_escala": 7,
               "hook_min": 0.20, "hook_rel": 0.75, "hold_min": 0.40, "fadiga_queda": 0.30, "freq_max": 2.0,
               "escalar_passo_min": 0.20, "escalar_passo_max": 0.30, "escala_orc_x_cpa": 10},
    # Kwai não passou pela auditoria do gesso (só o TikTok). Mantém os limiares antigos: sem a janela de
    # maturidade na pausa (dias/conv mínimos = 0, o gate vira no-op) e escala a partir de 10 conversões.
    "kwai": {"impr_min": 2000, "gasto_min_x_cpa": 1.0, "pausar_sem_conv_x_cpa": 2.0, "pausar_cpa_x": 1.5,
             "pausar_cpa_dias_min": 0, "pausar_cpa_conv_min": 0,
             "escalar_cpa_x": 0.8, "escalar_conv_min": 10, "escalar_conv_min_dias": 10, "dias_min_escala": 7,
             "hook_min": 0.20, "hook_rel": 0.75, "hold_min": 0.35, "fadiga_queda": 0.30, "freq_max": 3.5,
             "escalar_passo_min": 0.20, "escalar_passo_max": 0.30, "escala_orc_x_cpa": 10},
}
DECISOES = ("escalar", "manter", "pausar", "trocar-criativo", "aguardar")


def norm(txt: str) -> str:
    t = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def num(v) -> float:
    """'R$ 1.234,56' -> 1234.56 ; '1,234.56' -> 1234.56 ; '12%' -> 0.12 ; '-' -> 0."""
    if v is None:
        return 0.0
    s = str(v).strip()
    pct = s.endswith("%")
    s = re.sub(r"[^\d,.\-]", "", s)
    if s in ("", "-", ".", ","):
        return 0.0
    if "," in s and "." in s:  # o último separador é o decimal
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if re.search(r",\d{1,2}$", s) and s.count(",") == 1 else s.replace(",", "")
    elif s.count(".") > 1 or (re.search(r"^-?[1-9]\d{0,2}\.\d{3}$", s)):
        s = s.replace(".", "")  # 1.234 = milhar no export BR
    try:
        x = float(s)
    except ValueError:
        return 0.0
    return x / 100 if pct else x


def mapear_colunas(cabecalho: list[str], extra: dict | None = None) -> tuple[dict, list[str]]:
    nomes = {norm(c): c for c in cabecalho}
    achou = {}
    for canon, apelidos in ALIASES.items():
        if extra and canon in extra and extra[canon] in cabecalho:
            achou[canon] = extra[canon]
            continue
        for a in apelidos:
            if a in nomes:
                achou[canon] = nomes[a]
                break
        else:
            for n, original in nomes.items():  # começa com o apelido (ex.: "custo (brl)")
                if any(n.startswith(a + " ") for a in apelidos):
                    achou[canon] = original
                    break
    faltando = [c for c in OBRIGATORIAS if c not in achou]
    return achou, faltando


def ler_csv(texto: str) -> list[dict]:
    texto = texto.lstrip("﻿")
    amostra = texto[:4096]
    delim = ";" if amostra.count(";") > amostra.count(",") else ","
    return list(csv.DictReader(io.StringIO(texto), delimiter=delim))


def metricas(l: dict) -> dict:
    g, i, c, cv = l["gasto"], l["impressoes"], l["cliques"], l["conversoes"]
    m = {
        "ctr": c / i if i else 0.0,
        "cpm": g / i * 1000 if i else 0.0,
        "cpc": g / c if c else None,
        "cpa": g / cv if cv else None,
        "roas": l["receita"] / g if g and l.get("receita") else None,
        "hook": l["views_2s"] / i if i and l.get("views_2s") else None,
        "hold": l["views_6s"] / l["views_2s"] if l.get("views_2s") and l.get("views_6s") else None,
        "conclusao": l["views_100"] / i if i and l.get("views_100") else None,
        "frequencia": l.get("frequencia") or (i / l["alcance"] if l.get("alcance") else None),
    }
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()}


def decidir(l: dict, m: dict, cpa_alvo: float, roas_alvo: float | None, lim: dict,
            dias: float | None = None, mediana_hook: float | None = None,
            anterior: dict | None = None, retargeting: bool = False) -> tuple[str, list[str]]:
    motivos, sinais = [], []
    # gancho: com 10+ anúncios (mediana_hook definido) usa o relativo; senão o absoluto
    if m["hook"] is not None:
        if mediana_hook:
            if m["hook"] < lim["hook_rel"] * mediana_hook:
                sinais.append(f"gancho fraco: {m['hook']:.0%} veem 2 s, abaixo de {lim['hook_rel']:.0%} da "
                              f"mediana da conta ({mediana_hook:.0%})")
        elif m["hook"] < lim["hook_min"]:
            sinais.append(f"gancho fraco: {m['hook']:.0%} veem 2 s (heurística mín. {lim['hook_min']:.0%})")
    if m["hold"] is not None and m["hold"] < lim["hold_min"]:
        sinais.append(f"retém pouco: {m['hold']:.0%} dos 2 s chegam a 6 s (heurística mín. {lim['hold_min']:.0%})")
    # fadiga primária: queda vs export anterior (--anterior)
    if anterior:
        quedas = []
        pc, ph = anterior.get("ctr"), anterior.get("hook")
        if pc and m["ctr"] and m["ctr"] < pc * (1 - lim["fadiga_queda"]):
            quedas.append(f"CTR caiu {1 - m['ctr'] / pc:.0%}")
        if ph and m["hook"] and m["hook"] < ph * (1 - lim["fadiga_queda"]):
            quedas.append(f"taxa de 2 s caiu {1 - m['hook'] / ph:.0%}")
        if quedas:
            sinais.append("fadiga: " + ", ".join(quedas) + f" vs export anterior (≥ {lim['fadiga_queda']:.0%})")
    # fadiga secundária: frequência só em retargeting (experimental)
    if retargeting and m["frequencia"] and m["frequencia"] > lim["freq_max"]:
        sinais.append(f"fadiga (retargeting, experimental): frequência {m['frequencia']:.1f} > {lim['freq_max']}")
    if l["impressoes"] < lim["impr_min"] and l["gasto"] < lim["gasto_min_x_cpa"] * cpa_alvo:
        return "aguardar", [f"dado insuficiente: {int(l['impressoes'])} impressões e gasto {l['gasto']:.2f} "
                            f"< {lim['gasto_min_x_cpa']}× CPA alvo"] + sinais
    if l["conversoes"] == 0:
        if l["gasto"] >= lim["pausar_sem_conv_x_cpa"] * cpa_alvo:
            return "pausar", [f"0 conversão com gasto {l['gasto']:.2f} ≥ {lim['pausar_sem_conv_x_cpa']}× CPA alvo"] + sinais
        return ("trocar-criativo" if sinais else "aguardar"), ["sem conversão ainda, abaixo do teto de gasto"] + sinais
    cpa = m["cpa"]
    roas_ok = roas_alvo is None or m["roas"] is None or m["roas"] >= roas_alvo
    maduro = (dias is not None and dias >= lim["pausar_cpa_dias_min"]) or l["conversoes"] >= lim["pausar_cpa_conv_min"]
    if cpa > lim["pausar_cpa_x"] * cpa_alvo and l["gasto"] >= lim["pausar_sem_conv_x_cpa"] * cpa_alvo:
        if maduro:
            return "pausar", [f"CPA {cpa:.2f} > {lim['pausar_cpa_x']}× alvo ({cpa_alvo}) com "
                              f"{int(l['conversoes'])} conversões" + (f" e {int(dias)} dias" if dias is not None else "")] + sinais
        return "aguardar", [f"CPA {cpa:.2f} alto, mas ainda na janela de aprendizado: precisa de "
                            f"{lim['pausar_cpa_dias_min']}+ dias ou {lim['pausar_cpa_conv_min']}+ resultados antes de pausar"] + sinais
    conv_ok = (l["conversoes"] >= lim["escalar_conv_min"]
               or (l["conversoes"] >= lim["escalar_conv_min_dias"] and dias is not None and dias >= lim["dias_min_escala"]))
    if cpa <= lim["escalar_cpa_x"] * cpa_alvo and conv_ok and roas_ok:
        if any(s.startswith("fadiga") for s in sinais):
            return "trocar-criativo", [f"CPA {cpa:.2f} bom, mas com fadiga: novo criativo no mesmo ângulo antes de escalar"] + sinais
        return "escalar", [f"CPA {cpa:.2f} ≤ {lim['escalar_cpa_x']}× alvo com {int(l['conversoes'])} conversões; "
                           f"subir {lim['escalar_passo_min']:.0%}–{lim['escalar_passo_max']:.0%} do orçamento a cada 48–72 h "
                           f"na campanha de escala (orçamento ≥ {lim['escala_orc_x_cpa']}× CPA; o teste a 1–2× CPA é "
                           "leitura de sinal, não sai do aprendizado)"] + sinais
    if sinais:
        return "trocar-criativo", [f"CPA {cpa:.2f} perto do alvo; sinais de criativo"] + sinais
    motivos.append(f"CPA {cpa:.2f} perto do alvo ({cpa_alvo}); conversões {int(l['conversoes'])}")
    return "manter", motivos


def _mapa_anterior(texto: str, mapa: dict | None) -> dict:
    """{nome_normalizado: {'ctr':.., 'hook':..}} do export anterior, para medir fadiga."""
    prev = ler_csv(texto)
    if not prev:
        return {}
    cols, faltando = mapear_colunas(list(prev[0].keys()), mapa)
    if "anuncio" not in cols:
        return {}
    out = {}
    for r in prev:
        nome = (r.get(cols["anuncio"]) or "").strip()
        if not nome or norm(nome) in ("total", "totais", "total geral"):
            continue
        l = {k: num(r.get(col)) for k, col in cols.items() if k != "anuncio"}
        for k in ALIASES:
            l.setdefault(k, 0.0)
        pm = metricas(l)
        out[norm(nome)] = {"ctr": pm["ctr"], "hook": pm["hook"]}
    return out


def ler(texto: str, cpa_alvo: float, roas_alvo: float | None = None, plataforma: str = "tiktok",
        mapa: dict | None = None, ajustes: dict | None = None, dias: float | None = None,
        anterior_texto: str | None = None, retargeting: bool = False) -> dict:
    if cpa_alvo is None or cpa_alvo <= 0:
        return {"status": "entrada_incompleta", "faltando": ["cpa_alvo"], "linhas": []}
    lim = dict(LIMIARES[plataforma])
    lim.update(ajustes or {})
    linhas_csv = ler_csv(texto)
    if not linhas_csv:
        return {"status": "entrada_incompleta", "faltando": ["linhas (export vazio)"], "linhas": []}
    cols, faltando = mapear_colunas(list(linhas_csv[0].keys()), mapa)
    if faltando:
        return {"status": "entrada_incompleta", "faltando": faltando, "colunas_achadas": cols,
                "dica": "passe --map com {\"canonico\": \"Nome da coluna\"}", "linhas": []}
    anterior = _mapa_anterior(anterior_texto, mapa) if anterior_texto else {}
    # 1ª passagem: métricas por anúncio (para a mediana de gancho da conta)
    itens = []
    for r in linhas_csv:
        nome = (r.get(cols["anuncio"]) or "").strip()
        if not nome or norm(nome) in ("total", "totais", "total geral"):
            continue
        l = {k: num(r.get(col)) for k, col in cols.items() if k != "anuncio"}
        for k in ALIASES:
            l.setdefault(k, 0.0)
        itens.append((nome, l, metricas(l)))
    hooks = [m["hook"] for _, _, m in itens if m["hook"] is not None]
    mediana_hook = round(statistics.median(hooks), 4) if len(hooks) >= 10 else None
    # 2ª passagem: decisão
    saida = []
    for nome, l, m in itens:
        d, motivos = decidir(l, m, cpa_alvo, roas_alvo, lim, dias=dias, mediana_hook=mediana_hook,
                             anterior=anterior.get(norm(nome)), retargeting=retargeting)
        saida.append({"anuncio": nome, **{k: l[k] for k in ("gasto", "impressoes", "cliques", "conversoes", "receita")},
                      "metricas": m, "decisao": d, "motivos": motivos})
    tot = {k: sum(x[k] for x in saida) for k in ("gasto", "impressoes", "cliques", "conversoes", "receita")}
    tot["cpa"] = round(tot["gasto"] / tot["conversoes"], 2) if tot["conversoes"] else None
    tot["roas"] = round(tot["receita"] / tot["gasto"], 2) if tot["gasto"] and tot["receita"] else None
    return {"status": "ok", "plataforma": plataforma, "cpa_alvo": cpa_alvo, "roas_alvo": roas_alvo,
            "dias": dias, "retargeting": retargeting, "mediana_hook": mediana_hook,
            "limiares": lim, "limiares_sao": "heurísticas ARKOS, não regra da plataforma",
            "colunas": cols, "total": tot, "linhas": saida,
            "contagem": {d: sum(1 for x in saida if x["decisao"] == d) for d in DECISOES}}


def pronto(r: dict) -> list[str]:
    """Critério de pronto da leitura. Lista vazia = verde."""
    erros = []
    if r.get("status") != "ok":
        return [f"status {r.get('status')}: faltando {r.get('faltando')}"]
    if not r["linhas"]:
        erros.append("nenhum anúncio lido")
    for x in r["linhas"]:
        if x["decisao"] not in DECISOES:
            erros.append(f"{x['anuncio']}: decisão inválida")
        if not x["motivos"]:
            erros.append(f"{x['anuncio']}: decisão sem motivo")
        if x["decisao"] == "escalar" and any(m.startswith("dado insuficiente") for m in x["motivos"]):
            erros.append(f"{x['anuncio']}: escalar com dado insuficiente")
    if "heur" not in r.get("limiares_sao", ""):
        erros.append("limiares sem o rótulo de heurística")
    return erros


def para_md(r: dict) -> str:
    if r.get("status") != "ok":
        return f"# Leitura não feita\n\nFaltando: {', '.join(r.get('faltando', []))}\n"
    t = r["total"]
    out = [f"# Leitura de anúncios ({r['plataforma']})", "",
           f"Total: gasto {t['gasto']:.2f} · conversões {int(t['conversoes'])} · CPA {t['cpa']} · ROAS {t['roas']} "
           f"(alvo CPA {r['cpa_alvo']}).", "", f"Limiares: {r['limiares_sao']}.", "",
           "| Anúncio | Gasto | Conv. | CPA | CTR | Gancho 2s | Retenção 6s | Decisão | Por quê |",
           "|---|---|---|---|---|---|---|---|---|"]
    pc = lambda v: "—" if v is None else f"{v:.0%}"
    for x in sorted(r["linhas"], key=lambda x: DECISOES.index(x["decisao"])):
        m = x["metricas"]
        out.append(f"| {x['anuncio']} | {x['gasto']:.2f} | {int(x['conversoes'])} | "
                   f"{'—' if m['cpa'] is None else format(m['cpa'], '.2f')} | {m['ctr']:.2%} | "
                   f"{pc(m['hook'])} | {pc(m['hold'])} | **{x['decisao']}** | {'; '.join(x['motivos'])} |")
    return "\n".join(out) + "\n"


def _arg(argv, nome, padrao=None):
    return argv[argv.index(nome) + 1] if nome in argv else padrao


def _main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("ler", "pronto"):
        print(__doc__)
        return 2
    if argv[0] == "pronto":
        erros = pronto(json.loads(Path(argv[1]).read_text(encoding="utf-8")))
        print(json.dumps({"pronto": not erros, "erros": erros}, ensure_ascii=False, indent=2))
        return 0 if not erros else 1
    ajustes = {}
    for i, a in enumerate(argv):
        if a == "--limiar":
            k, v = argv[i + 1].split("=", 1)
            ajustes[k] = float(v)
    mapa = json.loads(Path(_arg(argv, "--map")).read_text(encoding="utf-8")) if "--map" in argv else None
    roas = _arg(argv, "--roas-alvo")
    dias = _arg(argv, "--dias")
    anterior_txt = Path(_arg(argv, "--anterior")).read_text(encoding="utf-8-sig") if "--anterior" in argv else None
    r = ler(Path(argv[1]).read_text(encoding="utf-8-sig"), float(_arg(argv, "--cpa-alvo", 0)),
            float(roas) if roas else None, _arg(argv, "--plataforma", "tiktok"), mapa, ajustes,
            dias=float(dias) if dias else None, anterior_texto=anterior_txt, retargeting="--retargeting" in argv)
    txt = json.dumps(r, ensure_ascii=False, indent=2)
    for flag, conteudo in (("--out", txt), ("--md", para_md(r))):
        if flag in argv:
            p = Path(_arg(argv, flag))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(conteudo, encoding="utf-8")
    print(txt)
    return 0 if r["status"] == "ok" else 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
