"""arkos-escala: decide o que pausar, manter e escalar a partir de um export de métricas (CSV ou JSON). Só PROPÕE.
A mudança na conta passa pela arkos-guarda-escrita (prévia + aprovação).

Uso:
  python escala.py decidir --dados metricas.csv --meta-cpa 50 [--meta-roas 3] [--min-conv 10] [--min-gasto-fator 2]
                           [--teto-aumento 0.20] [--dias-aprendizado 7] [--folga-min 0.10] [--periodo-dias 7]
                           [--intervalo-dias 3] [--atribuicao-confiavel --registro-dono <id/caminho da decisão>]
                           [--saida workspace/<cliente>/<projeto>/escala/]
  python escala.py decidir --dados metricas.csv --modo loja --break-even 2.5 [--meta-roas R] [--cpa-break-even C]
                           [--teto-aumento 0.20] [--periodo-dias 7] [--saida ...]

Modo loja (decisão por ROAS x break-even, pontos 1-4 da auditoria de e-commerce):
  - ROAS-meta = --meta-roas, ou o break-even x 1,25 quando não informado;
  - folga = 1 − meta ÷ ROAS 7d; folga >= 10% libera escala em até METADE da folga;
  - teto do passo 20%, ou até 50% quando a folga >= 40% (regra "sem reaprendizado" da Meta);
  - passo > 5% espera 72 h desde o último ajuste; leitura em 7 dias (14 no PMax, com --periodo-dias 14);
  - pausa no CONJUNTO: ROAS 7d < 0,8x o equilíbrio pausa; entre 0,8x e 1,0x reduz o budget à metade e relê em 7 dias;
    a decisão de pausa só vale com gasto >= 2x o CPA de equilíbrio (--cpa-break-even) ou 10+ conversões.

Colunas aceitas (nomes comuns da Meta/Google): nome|ad_set|campanha, gasto|spend|cost, conversoes|results|conversions,
receita|value|conv_value, dias_ativo|age_days, aprendizado|learning (sim/não), budget_diario|daily_budget,
dias_desde_ajuste|days_since_budget_change (dias desde a última mudança de budget; opcional).
O export deve ser dos ÚLTIMOS 7 DIAS (--periodo-dias), no nível em que o budget mora (campanha em CBO).

Regra (fixa, transparente, auditável):
  1. em aprendizado ou com menos de --dias-aprendizado dias: MANTER (não mexer na fase de aprendizado);
  2. gasto < min_gasto_fator x meta_cpa e conversões < min_conv: MANTER_COLETAR (dado insuficiente, sem decisão);
  3. CPA > 1,5 x meta (ou ROAS < 0,5 x meta) com gasto >= min_gasto_fator x meta: PAUSAR;
  4. folga = (meta − CPA 7d) / meta. Folga >= --folga-min (10%), ROAS na meta (se houver) e conversões >= min_conv:
     ESCALAR em até METADE DA FOLGA, limitado por --teto-aumento. Se a verba nova não trouxer nenhuma conversão,
     o CPA ainda fica abaixo da meta (base: trafego/meta/escala-por-folga-headroom).
     Ajuste de budget há menos de --intervalo-dias (padrão 3): MANTER (respeitar o intervalo).
     Intervalo abaixo de 3 dias (escala diária) só com --atribuicao-confiavel e --registro-dono, e só nas linhas
     com 30+ conversões por dia; as demais seguem o intervalo de 3 dias (base: trafego/meta/escala-meta);
  5. o resto: MANTER.
Saída: 0 ok · 2 recusa · 3 exceção tratada.
"""
import argparse, csv, json, sys
from pathlib import Path

ALIAS = {"nome": ("nome", "ad_set", "adset", "ad set name", "campanha", "campaign", "campaign name", "ad_set_name"),
         "gasto": ("gasto", "spend", "cost", "amount spent", "valor usado"),
         "conv": ("conversoes", "conversões", "results", "conversions", "resultados"),
         "receita": ("receita", "value", "conv_value", "conversion value", "purchase value"),
         "dias": ("dias_ativo", "age_days", "dias"),
         "aprendizado": ("aprendizado", "learning", "learning phase", "fase de aprendizado"),
         "budget": ("budget_diario", "daily_budget", "orcamento", "budget"),
         "desde_ajuste": ("dias_desde_ajuste", "days_since_budget_change", "days_since_edit", "dias_desde_mudanca")}

INTERVALO_PADRAO = 3        # dias entre aumentos (travas.intervalo_dias)
CONV_DIA_DIARIO = 30        # escala diária só com 30+ conversões/dia na linha
# Modo loja (decisão por ROAS x break-even):
BE_PAUSA = 0.8              # ROAS 7d < 0,8x equilíbrio -> pausar
BE_REDUZIR = 1.0           # 0,8x a 1,0x equilíbrio -> reduzir à metade e reler em 7 dias
META_PRECAUCAO = 1.25      # ROAS-meta = break-even x 1,25 (precaução, não medido)
TETO_ALTO = 0.50           # teto dinâmico quando a folga >= 40% (regra "sem reaprendizado" da Meta)
FOLGA_TETO_ALTO = 0.40
PASSO_SEM_ESPERA = 0.05    # passo <= 5% não espera; passo > 5% espera 72 h


def num(v):
    if v in (None, ""):
        return None
    s = str(v).strip().replace("R$", "").replace("US$", "").replace("$", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def carregar(arq):
    p = Path(arq)
    if p.suffix.lower() == ".json":
        linhas = json.loads(p.read_text(encoding="utf-8-sig"))
    else:
        texto = p.read_text(encoding="utf-8-sig")
        sep = ";" if texto.count(";") > texto.count(",") else ","
        linhas = list(csv.DictReader(texto.splitlines(), delimiter=sep))
    out = []
    for l in linhas:
        low = {k.strip().lower(): v for k, v in l.items() if k}
        g = lambda campo: next((low[a] for a in ALIAS[campo] if a in low), None)
        out.append({"nome": g("nome") or "?", "gasto": num(g("gasto")), "conv": num(g("conv")), "receita": num(g("receita")),
                    "dias": num(g("dias")), "aprendizado": str(g("aprendizado") or "").strip().lower() in ("sim", "yes", "true", "1", "learning"),
                    "budget": num(g("budget")), "desde_ajuste": num(g("desde_ajuste"))})
    return out


def decidir(linhas, meta_cpa, meta_roas=None, min_conv=10, min_gasto_fator=2.0, teto=0.20, dias_aprend=7,
            folga_min=0.10, periodo=7, intervalo=INTERVALO_PADRAO, atribuicao_confiavel=False, registro_dono=None):
    if teto > 0.5:
        raise ValueError("teto de aumento acima de 50% por execução não é aceito; a guarda-escrita pede 2ª confirmação acima de 20%")
    if intervalo < 1:
        raise ValueError("intervalo_dias mínimo é 1")
    if intervalo < INTERVALO_PADRAO and not (atribuicao_confiavel and registro_dono):
        raise ValueError(f"escala com intervalo de {intervalo:g} dia(s) exige atribuição confiável (--atribuicao-confiavel) "
                         f"e registro de decisão do dono (--registro-dono); sem isso o intervalo é {INTERVALO_PADRAO} dias")
    res = []
    for l in linhas:
        if l["gasto"] is None or l["conv"] is None:
            res.append({**l, "acao": "MANTER_COLETAR", "porque": "linha sem gasto ou conversões: dado incompleto"}); continue
        cpa = l["gasto"] / l["conv"] if l["conv"] else None
        roas = l["receita"] / l["gasto"] if l["receita"] is not None and l["gasto"] else None
        base = {**l, "cpa": round(cpa, 2) if cpa else None, "roas": round(roas, 2) if roas is not None else None}
        if l["aprendizado"] or (l["dias"] is not None and l["dias"] < dias_aprend):
            res.append({**base, "acao": "MANTER", "porque": "em fase de aprendizado: mexer agora reinicia o aprendizado"}); continue
        gasto_min = min_gasto_fator * meta_cpa
        if l["gasto"] < gasto_min and l["conv"] < min_conv:
            res.append({**base, "acao": "MANTER_COLETAR", "porque": f"gasto {l['gasto']:.0f} < {gasto_min:.0f} e {l['conv']:.0f} conversões: pouco dado para decidir"}); continue
        ruim_cpa = (cpa is None and l["gasto"] >= gasto_min) or (cpa is not None and cpa > 1.5 * meta_cpa)
        ruim_roas = meta_roas is not None and roas is not None and roas < 0.5 * meta_roas
        if (ruim_cpa or ruim_roas) and l["gasto"] >= gasto_min:
            motivo = "sem conversão" if cpa is None else f"CPA {cpa:.2f} > 1,5 x meta {meta_cpa:.2f}"
            if ruim_roas:
                motivo += f"; ROAS {roas:.2f} < metade da meta {meta_roas:.2f}"
            res.append({**base, "acao": "PAUSAR", "porque": motivo, "guarda": "arkos-guarda-escrita", "rollback": "reativar o conjunto"}); continue
        bom_roas = meta_roas is None or (roas is not None and roas >= meta_roas)
        folga = (meta_cpa - cpa) / meta_cpa if cpa is not None else None
        if folga is not None and folga >= folga_min and bom_roas and l["conv"] >= min_conv:
            conv_dia = l["conv"] / periodo if periodo else 0
            diario_ok = intervalo < INTERVALO_PADRAO and conv_dia >= CONV_DIA_DIARIO
            intervalo_linha = intervalo if diario_ok or intervalo >= INTERVALO_PADRAO else INTERVALO_PADRAO
            if l["desde_ajuste"] is not None and l["desde_ajuste"] < intervalo_linha:
                res.append({**base, "acao": "MANTER", "folga": round(folga, 4),
                            "porque": f"último ajuste há {l['desde_ajuste']:.0f} dia(s); intervalo mínimo {intervalo_linha:g} dias"}); continue
            aumento = round(min(folga / 2, teto), 4)
            novo = round(l["budget"] * (1 + aumento), 2) if l["budget"] else None
            porque = (f"folga {folga:.0%} (CPA 7d {cpa:.2f} x meta {meta_cpa:.2f}) com {l['conv']:.0f} conversões: "
                      f"aumento de até metade da folga = {aumento:.1%}" + (" (limitado pelo teto)" if folga / 2 > teto else ""))
            if intervalo < INTERVALO_PADRAO and not diario_ok:
                porque += f"; {conv_dia:.0f} conv./dia < {CONV_DIA_DIARIO}: segue intervalo de {INTERVALO_PADRAO} dias"
            if l["desde_ajuste"] is None:
                porque += f"; confira se o último ajuste foi há {intervalo_linha:g}+ dias"
            item = {**base, "acao": "ESCALAR", "porque": porque, "folga": round(folga, 4), "budget_novo": novo,
                    "aumento_max": aumento, "intervalo_dias": intervalo_linha, "guarda": "arkos-guarda-escrita",
                    "rollback": f"voltar budget para {l['budget']}" if l["budget"] else "voltar budget anterior"}
            if diario_ok:
                item["registro_dono"] = registro_dono
            res.append(item); continue
        res.append({**base, "acao": "MANTER", "porque": "dentro da faixa da meta"})
    return res


def decidir_loja(linhas, break_even, meta_roas=None, min_conv=10, min_gasto_fator=2.0, cpa_break_even=None,
                 teto=0.20, dias_aprend=7, folga_min=0.10, periodo=7):
    """Modo loja: decide por ROAS contra o break-even (ROAS de equilíbrio). Pausa/reduz no conjunto,
    nunca no anúncio. ROAS-meta = break-even x 1,25 quando não informado. Escala por metade da folga."""
    if break_even is None or break_even <= 0:
        raise ValueError("modo loja exige --break-even (ROAS de equilíbrio) > 0")
    if teto > 0.5:
        raise ValueError("teto de aumento acima de 50% por execução não é aceito; a guarda-escrita pede 2ª confirmação acima de 20%")
    meta = meta_roas if meta_roas is not None else round(break_even * META_PRECAUCAO, 4)
    gasto_floor = min_gasto_fator * cpa_break_even if cpa_break_even else None  # gasto >= 2x CPA de equilíbrio
    res = []
    for l in linhas:
        if l["gasto"] is None:
            res.append({**l, "acao": "MANTER_COLETAR", "porque": "linha sem gasto: dado incompleto"}); continue
        roas = l["receita"] / l["gasto"] if l["receita"] is not None and l["gasto"] else None
        base = {**l, "roas": round(roas, 2) if roas is not None else None, "break_even": break_even, "meta_roas": meta}
        if l["aprendizado"] or (l["dias"] is not None and l["dias"] < dias_aprend):
            res.append({**base, "acao": "MANTER", "porque": "em fase de aprendizado: mexer agora reinicia o aprendizado"}); continue
        if roas is None:
            res.append({**base, "acao": "MANTER_COLETAR", "porque": "loja decide por ROAS: faltou receita no export"}); continue
        maduro = (gasto_floor is not None and l["gasto"] >= gasto_floor) or (l["conv"] is not None and l["conv"] >= min_conv)
        if not maduro:
            alvo = f"gasto >= {gasto_floor:.0f}" if gasto_floor is not None else f"{min_conv:g} conversões"
            res.append({**base, "acao": "MANTER_COLETAR", "porque": f"pouco dado para decidir ({alvo})"}); continue
        if roas < BE_PAUSA * break_even:
            res.append({**base, "acao": "PAUSAR", "porque": f"ROAS 7d {roas:.2f} < 0,8x o equilíbrio {break_even:.2f}",
                        "guarda": "arkos-guarda-escrita", "rollback": "reativar o conjunto"}); continue
        if roas < BE_REDUZIR * break_even:
            novo = round(l["budget"] * 0.5, 2) if l["budget"] else None
            res.append({**base, "acao": "REDUZIR", "budget_novo": novo,
                        "porque": f"ROAS 7d {roas:.2f} entre 0,8x e 1,0x o equilíbrio {break_even:.2f}: cortar o budget à metade e reler em 7 dias",
                        "guarda": "arkos-guarda-escrita", "rollback": f"voltar budget para {l['budget']}" if l["budget"] else "voltar budget anterior"}); continue
        folga = 1 - meta / roas
        if folga >= folga_min and (l["conv"] is None or l["conv"] >= min_conv):
            teto_din = TETO_ALTO if folga >= FOLGA_TETO_ALTO else teto
            aumento = round(min(folga / 2, teto_din), 4)
            if aumento > PASSO_SEM_ESPERA and l["desde_ajuste"] is not None and l["desde_ajuste"] < INTERVALO_PADRAO:
                res.append({**base, "acao": "MANTER", "folga": round(folga, 4),
                            "porque": f"passo {aumento:.1%} acima de 5%: esperar 72 h (último ajuste há {l['desde_ajuste']:.0f} dia(s))"}); continue
            novo = round(l["budget"] * (1 + aumento), 2) if l["budget"] else None
            porque = (f"ROAS 7d {roas:.2f} x meta {meta:.2f} (equilíbrio {break_even:.2f} x 1,25): folga {folga:.0%}; "
                      f"aumento de até metade da folga = {aumento:.1%}" +
                      (" (teto 50%: folga >= 40%)" if teto_din == TETO_ALTO else "") +
                      (" (limitado pelo teto)" if folga / 2 > teto_din else ""))
            if aumento > PASSO_SEM_ESPERA and l["desde_ajuste"] is None:
                porque += "; passo > 5%: confira 72 h desde o último ajuste"
            res.append({**base, "acao": "ESCALAR", "porque": porque, "folga": round(folga, 4), "budget_novo": novo,
                        "aumento_max": aumento, "guarda": "arkos-guarda-escrita",
                        "rollback": f"voltar budget para {l['budget']}" if l["budget"] else "voltar budget anterior"}); continue
        res.append({**base, "acao": "MANTER", "porque": f"ROAS {roas:.2f} acima do equilíbrio mas folga {folga:.0%} < {folga_min:.0%}"})
    return res


def md(res):
    L = ["# Decisão de escala (proposta)", "", "Nada foi alterado na conta. Cada PAUSAR/ESCALAR passa pela arkos-guarda-escrita.", "",
         "| Conjunto | Gasto | Conv. | CPA | ROAS | Ação | Por quê |", "|---|---|---|---|---|---|---|"]
    for r in res:
        L.append(f"| {r['nome']} | {r['gasto']} | {r['conv']} | {r.get('cpa')} | {r.get('roas')} | **{r['acao']}** | {r['porque']} |")
    return "\n".join(L) + "\n"


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["decidir"]); ap.add_argument("--dados", required=True); ap.add_argument("--saida")
    ap.add_argument("--modo", choices=["cpa", "loja"], default="cpa")
    ap.add_argument("--break-even", type=float); ap.add_argument("--cpa-break-even", type=float)
    ap.add_argument("--meta-cpa", type=float); ap.add_argument("--meta-roas", type=float); ap.add_argument("--min-conv", type=float, default=10)
    ap.add_argument("--min-gasto-fator", type=float, default=2.0); ap.add_argument("--teto-aumento", type=float, default=0.20)
    ap.add_argument("--dias-aprendizado", type=float, default=7); ap.add_argument("--folga-min", type=float, default=0.10)
    ap.add_argument("--periodo-dias", type=float, default=7); ap.add_argument("--intervalo-dias", type=float, default=INTERVALO_PADRAO)
    ap.add_argument("--atribuicao-confiavel", action="store_true"); ap.add_argument("--registro-dono")
    a = ap.parse_args(argv)
    if a.modo == "loja":
        if not a.break_even:
            print(json.dumps({"excecao": "entrada_incompleta", "pergunta": "qual o ROAS de equilíbrio (break-even) desta loja? (--break-even)"}, ensure_ascii=False)); return 3
    elif not a.meta_cpa:
        print(json.dumps({"excecao": "entrada_incompleta", "pergunta": "qual a meta de CPA (custo por resultado) desta conta?"}, ensure_ascii=False)); return 3
    linhas = carregar(a.dados)
    if not linhas:
        print(json.dumps({"excecao": "entrada_incompleta", "aviso": "export vazio"}, ensure_ascii=False)); return 3
    try:
        if a.modo == "loja":
            res = decidir_loja(linhas, a.break_even, a.meta_roas, a.min_conv, a.min_gasto_fator, a.cpa_break_even,
                               a.teto_aumento, a.dias_aprendizado, a.folga_min, a.periodo_dias)
        else:
            res = decidir(linhas, a.meta_cpa, a.meta_roas, a.min_conv, a.min_gasto_fator, a.teto_aumento, a.dias_aprendizado,
                          a.folga_min, a.periodo_dias, a.intervalo_dias, a.atribuicao_confiavel, a.registro_dono)
    except ValueError as e:
        print(f"recusado: {e}", file=sys.stderr); return 2
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if a.saida:
        if "arkos.engine" in Path(a.saida).parts:
            print("recusado: entrega não fica dentro de arkos.engine", file=sys.stderr); return 2
        d = Path(a.saida); d.mkdir(parents=True, exist_ok=True)
        (d / "decisao.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        (d / "decisao.md").write_text(md(res), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
