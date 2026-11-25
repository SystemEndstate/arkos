"""arkos-garimpo-instagram: acha empresas de um nicho numa cidade pelo Instagram e mede sinais de oportunidade
(posta muito com pouco engajamento, sem link de venda, site ruim ou sem site, sem anúncio ativo na Biblioteca de
Anúncios da Meta, comentários sem resposta). Dá nota 0-100, diagnóstico e o que oferecer. Só dado público, sem login,
sem contato: nada é curtido, seguido, comentado ou enviado.

Uso:
  python garimpo_ig.py buscar --tools <pasta _tools da ARKOS> --nicho "clínica odontológica" --cidade "Campinas"
                              [--n 10] [--perfis a,b] [--comentarios] [--sem-adlib] [--confirmar-custo]
                              --saida workspace/<cliente>/<projeto>/garimpo-instagram/
  python garimpo_ig.py avaliar --entrada perfis.json --saida <pasta>   (só pontua perfis já coletados)

Sem --confirmar-custo o script só mostra a estimativa de custo e para (código 3): Apify cobra por perfil/comentário
(plano grátis: US$ 5/mês por chave) e a Biblioteca de Anúncios gasta 1 render da Oxylabs por empresa.
Fontes (chaves só pelo chaves.py): pesq.py google (Google site:instagram.com), pesq.py apify
(apify~instagram-profile-scraper e, com --comentarios, apify~instagram-comment-scraper), pesq.py adlib.
Saída: 0 ok · 2 recusa · 3 exceção tratada.
"""
import argparse, json, os, re, subprocess, sys, time, unicodedata, urllib.request  # noqa: E401
from datetime import datetime, timezone
from pathlib import Path

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
# preço de tabela usado só na ESTIMATIVA (conferir no Apify antes de rodar grande)
CUSTO = {"perfil": 0.0026, "comentario": 0.0023, "adlib": "1 render Oxylabs"}
# limiares padrão: A CONFIRMAR com o dono (nada de número de mercado inventado: são cortes operacionais)
LIM = {"posts_30d_muito": 8, "engaj_baixo": 0.005, "seguidores_max": 100_000, "seguidores_min": 300, "dias_inativo": 90,
       "site_lento_s": 4.0, "penalidade_parada": 20, "amostra_min": 20}
RESERVADOS = {"p", "reel", "reels", "explore", "stories", "tv", "accounts", "about", "legal", "directory", "developer", "web"}
AGREGADOR = re.compile(r"(linktr\.ee|linkin\.bio|beacons\.ai|bio\.link|lnk\.bio|taplink|campsite\.bio|linkbio|msha\.ke)", re.I)
WHATS = re.compile(r"(wa\.me|api\.whatsapp\.com|whatsapp\.com/)", re.I)


def rodar(tools, *args, timeout=400):
    cmd = [sys.executable, str(Path(tools) / "chaves.py"), "run", "--", sys.executable, str(Path(tools) / "pesq.py"), *args]
    r = subprocess.run(cmd, cwd=tools, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"}, creationflags=NO_WINDOW)
    return r.stdout


def json_final(out):
    """pesq.py imprime o JSON na última linha não vazia (avisos do chaves.py vêm antes)."""
    for linha in reversed((out or "").splitlines()):
        linha = linha.strip()
        if linha.startswith(("[", "{")):
            try: return json.loads(linha)
            except json.JSONDecodeError: return None
    return None


def handles_do_google(out):
    hs = []
    for linha in (out or "").splitlines():
        url = linha.split(" | ")[0].strip()
        m = re.match(r"https?://(?:www\.)?instagram\.com/([A-Za-z0-9._]{2,30})/?(?:\?|$)", url)
        cand = [m.group(1)] if m else []
        cand += re.findall(r"\(@([A-Za-z0-9._]{2,30})\)", linha)
        for h in cand:
            h = h.lower().rstrip(".")
            if h not in RESERVADOS and h not in hs:
                hs.append(h)
    return hs


def nome_busca(nome, usuario):
    """Nome para a Biblioteca de Anúncios: tira letra estilizada (𝑶𝒓𝒂𝒍 -> Oral), emoji e o que vem depois de | - •."""
    n = unicodedata.normalize("NFKC", nome or "")
    n = re.split(r"[|\-–•·]", n)[0]
    n = re.sub(r"[^\w\s&'.]", " ", n, flags=re.UNICODE)
    n = " ".join([w for w in n.split() if len(w) > 1][:3]).strip()
    return n if len(n) >= 3 else usuario


def medir_comentarios(cs, u):
    """Comentários de clientes e quantos a marca respondeu. Sem dado de resposta no retorno do ator, 'medido' fica False
    e o sinal não entra na nota (nada de supor que não houve resposta)."""
    dono = [c for c in cs if (c.get("ownerUsername") or "").lower() == u]
    clientes = [c for c in cs if (c.get("ownerUsername") or "").lower() != u]
    aninhado = any(c.get("repliesCount") is not None or c.get("replies") for c in cs)
    resp_aninh = {c.get("id") for c in clientes for r in (c.get("replies") or []) if (r.get("ownerUsername") or "").lower() == u}
    marcados = {(m.lower()) for c in dono for m in re.findall(r"@([A-Za-z0-9._]+)", c.get("text") or "")}
    respondidos = [c for c in clientes if c.get("id") in resp_aninh or (c.get("ownerUsername") or "").lower() in marcados]
    return {"total": len(clientes), "respondidos": len(respondidos), "medido": aninhado or bool(dono)}


def consultas(nicho, cidade, sinonimos=""):
    """Buscas no Google site:instagram.com até juntar a amostra mínima: o nicho e cada sinônimo, com variações comuns de bio."""
    termos = [nicho] + [x.strip() for x in (sinonimos or "").split(",") if x.strip()]
    out = []
    for t in termos:
        out += [f'"{t}" "{cidade}"', f"{t} {cidade}", f"{t} em {cidade}", f"{t} {cidade} agende", f"{t} {cidade} whatsapp",
                f"{t} {cidade} agendamento", f"{t} {cidade} perfil oficial"]
    return list(dict.fromkeys(out))


def checar_site(url, timeout=12):
    """GET público no site do link da bio: status, https, tempo, viewport (mobile), título. Sem login, sem formulário."""
    r = {"url": url, "ok": False}
    t0 = time.time()
    try:
        q = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (arkos-garimpo; checagem pública)"})
        with urllib.request.urlopen(q, timeout=timeout) as resp:
            h = resp.read(400_000).decode("utf-8", "replace"); r["status"] = resp.status; r["final"] = resp.geturl()
    except Exception as e:
        r["erro"] = str(getattr(e, "code", "") or type(e).__name__); return r
    r["segundos"] = round(time.time() - t0, 1)
    r["https"] = r["final"].startswith("https://")
    r["mobile"] = bool(re.search(r'<meta[^>]+name=["\']viewport', h, re.I))
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", h); r["titulo"] = (m.group(1).strip()[:80] if m else "")
    r["ok"] = r["status"] == 200 and r["https"] and r["mobile"] and r["segundos"] <= LIM["site_lento_s"]
    return r


def sinais(p, agora, site=None, adlib=None, coment=None):
    posts = [x for x in (p.get("latestPosts") or []) if x.get("timestamp")]
    datas = sorted((datetime.fromisoformat(x["timestamp"].replace("Z", "+00:00")) for x in posts), reverse=True)
    seg = p.get("followersCount") or 0
    s = {"seguidores": seg, "posts_total": p.get("postsCount"), "categoria": p.get("businessCategoryName"),
         "posts_30d": sum(1 for d in datas if (agora - d).days <= 30),
         "dias_ultimo_post": (agora - datas[0]).days if datas else None}
    eng = [((x.get("likesCount") or 0) + (x.get("commentsCount") or 0)) / seg for x in posts if seg and (x.get("likesCount") or 0) >= 0]
    s["engajamento"] = round(sum(eng) / len(eng), 4) if eng else None
    link = (p.get("externalUrl") or "").strip()
    s["link"] = link or None
    s["link_tipo"] = ("nenhum" if not link else "whatsapp" if WHATS.search(link) else "agregador" if AGREGADOR.search(link) else "site")
    s["site"] = site
    s["anuncios_ativos"] = adlib.get("ativos") if isinstance(adlib, dict) else None
    s["comentarios"] = coment
    return s


def pontuar(s):
    """Nota de oportunidade 0-100 (pesos fixos e auditáveis; quanto maior, mais coisa a ARKOS consegue resolver)."""
    achados, oferta, pts = [], [], 0
    ativo = s["dias_ultimo_post"] is not None and s["dias_ultimo_post"] <= LIM["dias_inativo"]
    if s["link_tipo"] == "nenhum":
        pts += 25; achados.append("sem link nenhum na bio"); oferta.append("site ou landing com agenda/WhatsApp (arkos-site)")
    elif s["link_tipo"] == "site" and s["site"] is not None and not s["site"].get("ok"):
        site = s["site"]
        prob = [x for x, ruim in (("fora do ar", "erro" in site), ("sem https", site.get("https") is False),
                                   ("não é mobile", site.get("mobile") is False), (f"lento ({site.get('segundos')} s)", (site.get("segundos") or 0) > LIM["site_lento_s"])) if ruim]
        pts += 25; achados.append("site com problema: " + ", ".join(prob)); oferta.append("refazer o site (arkos-site)")
    elif s["link_tipo"] in ("whatsapp", "agregador"):
        pts += 15; achados.append(f"bio só com {s['link_tipo']}, sem página de venda"); oferta.append("landing de oferta com captura (arkos-site)")
    if s["anuncios_ativos"] == 0:
        pts += 20; achados.append("nenhum anúncio ativo na Biblioteca de Anúncios (busca pelo nome; confirmar)"); oferta.append("tráfego pago Meta com teste de criativos")
    if s["posts_30d"] >= LIM["posts_30d_muito"] and s["engajamento"] is not None and s["engajamento"] < LIM["engaj_baixo"]:
        pts += 20; achados.append(f"posta muito ({s['posts_30d']} em 30 dias) com engajamento de {s['engajamento']:.2%}"); oferta.append("estratégia de conteúdo e criativos (ganchos)")
    elif s["engajamento"] is not None and s["engajamento"] < LIM["engaj_baixo"]:
        pts += 10; achados.append(f"engajamento baixo ({s['engajamento']:.2%})"); oferta.append("estratégia de conteúdo")
    c = s.get("comentarios")
    if c and not c.get("medido", True):
        achados.append(f"{c['total']} comentários recentes; respostas da marca não medidas (o ator não trouxe as respostas)")
    elif c and c.get("total", 0) >= 3 and c.get("respondidos", 0) / c["total"] < 0.3:
        pts += 10; achados.append(f"{c['total'] - c['respondidos']} de {c['total']} comentários recentes sem resposta da marca"); oferta.append("atendimento e resposta automática")
    if ativo:
        pts += 10
    else:  # conta parada PERDE nota: quem não posta há 90 dias dificilmente compra agora
        pts -= LIM["penalidade_parada"]
        achados.append(f"conta parada (sem post em {LIM['dias_inativo']} dias): perde {LIM['penalidade_parada']} pontos")
    return max(0, min(pts, 100)), achados, oferta


def avaliar(perfis, agora=None, sites=None, adlibs=None, coments=None, min_seguidores=None):
    min_seg = LIM["seguidores_min"] if min_seguidores is None else min_seguidores
    agora = agora or datetime.now(timezone.utc)
    lista, descartes = [], []
    for p in perfis:
        u = (p.get("username") or "").lower()
        if p.get("error") or not u:
            descartes.append({"perfil": u or "?", "motivo": f"perfil não abriu ({p.get('error') or 'sem dados'})"}); continue
        if p.get("private"):
            descartes.append({"perfil": u, "motivo": "conta privada"}); continue
        s = sinais(p, agora, (sites or {}).get(u), (adlibs or {}).get(u), (coments or {}).get(u))
        if s["seguidores"] > LIM["seguidores_max"]:
            descartes.append({"perfil": u, "motivo": f"marca grande ({s['seguidores']} seguidores): fora do porte"}); continue
        if s["seguidores"] < min_seg:
            descartes.append({"perfil": u, "motivo": f"conta minúscula ({s['seguidores']} seguidores, mínimo {min_seg})"}); continue
        nota, achados, oferta = pontuar(s)
        lista.append({"perfil": u, "nome": p.get("fullName"), "url": f"https://www.instagram.com/{u}/", "nota": nota,
                      "diagnostico": achados or ["nenhum sinal forte de oportunidade"], "oferecer": oferta, "sinais": s})
    lista.sort(key=lambda x: -x["nota"])
    return lista, descartes


def md(lista, descartes, nicho, cidade, amostra=None):
    aviso = (f"**Amostra de {amostra} perfis, abaixo do mínimo de {LIM['amostra_min']}:** acrescente sinônimos do nicho (`--sinonimos`) ou bairros."
             if amostra is not None and amostra < LIM["amostra_min"] else "")
    L = ["# Garimpo no Instagram (proposta)", "", f"Nicho: **{nicho}** · cidade: **{cidade}** · amostra {amostra if amostra is not None else '-'} perfis · "
         f"{len(lista)} avaliados · {len(descartes)} descartados", ""] + ([aviso, ""] if aviso else []) + ["",
         "Só dado público, sem login. **Ninguém foi contatado.** Os limiares são padrão e estão a confirmar com o dono.", "",
         "| Nota | Perfil | Seguidores | Posts 30 d | Engaj. | Link | Anúncios ativos | O que oferecer |", "|---|---|---|---|---|---|---|---|"]
    for x in lista:
        s = x["sinais"]
        eng = "-" if s["engajamento"] is None else f"{s['engajamento']:.2%}"
        ads = "-" if s["anuncios_ativos"] is None else "0" if s["anuncios_ativos"] == 0 else f"{s['anuncios_ativos']} (termo amplo: podem ser de outros)"
        L.append(f"| {x['nota']} | [@{x['perfil']}]({x['url']}) | {s['seguidores']} | {s['posts_30d']} | {eng} | "
                 f"{s['link_tipo']} | {ads} | {'; '.join(x['oferecer']) or '-'} |")
    L += ["", "## Diagnóstico por perfil", ""]
    for x in lista:
        L += [f"### {x['nota']} · @{x['perfil']} · {x['nome'] or ''}", ""] + [f"- {a}" for a in x["diagnostico"]] + [""]
    L += ["## Descartados", "", "| Perfil | Motivo |", "|---|---|"] + [f"| {d['perfil']} | {d['motivo']} |" for d in descartes]
    return "\n".join(L) + "\n"


def main(argv=None):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError: pass
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["buscar", "avaliar"]); ap.add_argument("--tools"); ap.add_argument("--entrada")
    ap.add_argument("--nicho", default=""); ap.add_argument("--cidade", default=""); ap.add_argument("--n", type=int, default=LIM["amostra_min"])
    ap.add_argument("--sinonimos", default=""); ap.add_argument("--min-seguidores", type=int, default=LIM["seguidores_min"])
    ap.add_argument("--perfis", default=""); ap.add_argument("--comentarios", action="store_true"); ap.add_argument("--sem-adlib", action="store_true")
    ap.add_argument("--confirmar-custo", action="store_true"); ap.add_argument("--saida", required=True)
    a = ap.parse_args(argv)
    if "arkos.engine" in Path(a.saida).parts:
        print("recusado: entrega não fica dentro de arkos.engine", file=sys.stderr); return 2
    saida = Path(a.saida); saida.mkdir(parents=True, exist_ok=True)
    if a.cmd == "avaliar":
        d = json.loads(Path(a.entrada).read_text(encoding="utf-8"))
        if isinstance(d, dict):
            lista, desc = avaliar(d.get("perfis", []), sites=d.get("sites"), adlibs=d.get("adlib"), coments=d.get("comentarios"), min_seguidores=a.min_seguidores)
        else:
            lista, desc = avaliar(d, min_seguidores=a.min_seguidores)
        amostra = len(d.get("perfis", [])) if isinstance(d, dict) else len(d)
    else:
        if not (a.nicho and a.cidade) and not a.perfis:
            print(json.dumps({"excecao": "entrada_incompleta", "pergunta": "qual nicho e qual cidade (ou --perfis a,b)?"}, ensure_ascii=False)); return 3
        if not a.tools or not (Path(a.tools) / "chaves.py").exists():
            print(json.dumps({"excecao": "fora_do_ar", "falta": "pasta _tools com chaves.py e pesq.py (--tools)"}, ensure_ascii=False)); return 3
        n = min(max(a.n, LIM["amostra_min"]), 40) if not a.perfis else max(1, min(a.n, 40))
        est = {"perfis": n, "apify_perfis_usd": round(n * CUSTO["perfil"], 3),
               "apify_comentarios_usd": round(n * 3 * 15 * CUSTO["comentario"], 3) if a.comentarios else 0,
               "oxylabs": 0 if a.sem_adlib else f"{n} renders (Biblioteca de Anúncios)", "google": f"até {len(consultas(a.nicho, a.cidade, a.sinonimos))} buscas Oxylabs (para até no 1º que somar {n} perfis)"}
        if not a.confirmar_custo:
            print(json.dumps({"excecao": "aguardando_confirmacao", "custo_estimado": est,
                              "aviso": "Apify grátis = US$ 5/mês por chave; rode de novo com --confirmar-custo depois do OK do usuário"}, ensure_ascii=False)); return 3
        hs = [h.strip().lstrip("@").lower() for h in a.perfis.split(",") if h.strip()]
        if not hs:
            for q in consultas(a.nicho, a.cidade, a.sinonimos):
                hs += [h for h in handles_do_google(rodar(a.tools, "google", "garimpo-ig", q, "instagram.com")) if h not in hs]
                if len(hs) >= n: break
        hs = hs[:n]
        if not hs:
            print(json.dumps({"excecao": "resultado_ruim", "aviso": "nenhum perfil achado; troque o nicho ou a cidade"}, ensure_ascii=False)); return 3
        perfis = json_final(rodar(a.tools, "apify", "garimpo-ig", "apify~instagram-profile-scraper", json.dumps({"usernames": hs, "resultsLimit": 12}))) or []
        achados = {(p.get("username") or "").lower() for p in perfis}
        perfis += [{"username": h, "error": "não retornou do Apify"} for h in hs if h not in achados]
        sites, adlibs, coments = {}, {}, {}
        for p in perfis:
            u = (p.get("username") or "").lower()
            if p.get("error"): continue
            link = p.get("externalUrl") or ""
            if link and not WHATS.search(link) and not AGREGADOR.search(link):
                sites[u] = checar_site(link)
            if not a.sem_adlib:
                nome = nome_busca(p.get("fullName"), u)
                adlibs[u] = {**(json_final(rodar(a.tools, "adlib", "garimpo-ig", nome)) or {}), "termo": nome}
            if a.comentarios:
                urls = [x["url"] for x in (p.get("latestPosts") or []) if (x.get("commentsCount") or 0) > 0 and x.get("url")][:3]
                if urls:
                    cs = json_final(rodar(a.tools, "apify", "garimpo-ig", "apify~instagram-comment-scraper", json.dumps({"directUrls": urls, "resultsLimit": 15, "includeNestedComments": True}))) or []
                    coments[u] = medir_comentarios(cs, u)
        (saida / "perfis.json").write_text(json.dumps({"perfis": perfis, "sites": sites, "adlib": adlibs, "comentarios": coments}, ensure_ascii=False, indent=1), encoding="utf-8")
        lista, desc = avaliar(perfis, sites=sites, adlibs=adlibs, coments=coments, min_seguidores=a.min_seguidores)
        amostra = len(hs)
    (saida / "garimpo.json").write_text(json.dumps({"lista": lista, "descartes": desc}, ensure_ascii=False, indent=1), encoding="utf-8")
    (saida / "garimpo.md").write_text(md(lista, desc, a.nicho or "-", a.cidade or "-", amostra), encoding="utf-8")
    print(json.dumps({"status": "ok", "avaliados": len(lista), "descartados": len(desc), "pasta": str(saida)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
