"""arkos-garimpo-x: acha no X posts de empresas e empresários PEDINDO um prestador (dev, editor de vídeo, designer,
tráfego, social media), confere cada post no dado público do próprio X, classifica, dá nota 0-100 (rubrica do
first-customer-finder) e escreve um rascunho de abordagem. NUNCA envia, curte, segue ou responde nada.

Uso:
  python garimpo_x.py buscar --tools <pasta _tools da ARKOS> --servicos dev,video [--idiomas pt,en] [--dias 30]
                             [--por-consulta 10] [--sem-x] --saida workspace/<cliente>/<projeto>/garimpo-x/
  python garimpo_x.py avaliar --entrada posts.json --saida <pasta>     (só classifica/pontua um JSON já coletado)

Fontes (chaves só pelo chaves.py da pasta _tools; nunca lidas aqui):
  - pesq.py google <mod> "<consulta>" x.com   (Oxylabs: Google site:x.com, últimos 12 meses)
  - x.py "<consulta>" --n N                     (Apify; no plano grátis os atores travam: o script segue sem)
  - conferência: cdn.syndication.twimg.com/tweet-result (dado público do embed do X: texto, data, autor; sem login)
Saída: 0 ok · 2 recusa · 3 exceção tratada (sem fonte, sem serviço).
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

SERVICOS = {
    "dev": {"rotulo": "desenvolvimento (site, app, sistema, automação)",
            "pt": ['"preciso de um programador"', '"procuro desenvolvedor"', '"alguém indica um dev"', '"preciso de alguém que programe"',
                   '"procuro programador freelancer"', '"minha empresa" precisa de um site', '"para minha loja" preciso de um programador',
                   '"meu negócio" "preciso de um site"', '"alguém indica" dev "minha empresa"'],
            "en": ['"looking for a developer"', '"need a developer" for my', '"hiring a freelance developer"', '"anyone know a good developer"', '"for my startup" "looking for a developer"',
                   '"my agency" "need a developer"', '"for my store" "need a developer"', '"my saas" "looking for a developer"'],
            "chaves": r"\b(dev|devs|desenvolvedor\w*|programador\w*|programe|developer|engineer|coder|full.?stack|front.?end|back.?end|"
                      r"site|website|app|aplicativo|sistema|saas|mvp|automa\w+|bubble|webflow|wordpress|shopify|n8n|api)\b"},
    "video": {"rotulo": "edição de vídeo",
              "pt": ['"preciso de um editor de vídeo"', '"procuro editor de vídeo"', '"alguém indica editor de vídeo"', '"procuro editor para"',
                   '"minha empresa" "editor de vídeo"', '"para minha marca" "editor de vídeo"'],
              "en": ['"looking for a video editor"', '"need a video editor"', '"hiring a video editor"',
                   '"for my business" "video editor"', '"my agency" "looking for a video editor"', '"our brand" "need a video editor"'],
              "chaves": r"\b(edi\w+ de v[ií]deo|editor\w*|edi[çc][ãa]o|video editor|editing|reels?|shorts|youtube|tiktok|cortes|motion)\b"},
    "design": {"rotulo": "design (marca, peças, UI)",
               "pt": ['"preciso de um designer"', '"procuro designer"', '"alguém indica designer"'],
               "en": ['"looking for a designer"', '"need a designer" for', '"hiring a designer"'],
               "chaves": r"\b(designer|design|logo|marca|identidade visual|branding|ui|ux|figma|criativos?)\b"},
    "trafego": {"rotulo": "tráfego pago",
                "pt": ['"preciso de um gestor de tráfego"', '"procuro gestor de tráfego"', '"alguém indica gestor de tráfego"'],
                "en": ['"looking for a media buyer"', '"need someone to run" ads', '"looking for a facebook ads" expert'],
                "chaves": r"\b(tr[áa]fego|gestor de tr[áa]fego|media buyer|ads|an[úu]ncios?|meta ads|google ads|facebook ads|ppc)\b"},
    "social": {"rotulo": "social media",
               "pt": ['"preciso de um social media"', '"procuro social media"', '"alguém indica social media"'],
               "en": ['"looking for a social media manager"', '"need a social media manager"'],
               "chaves": r"\b(social media|redes sociais|instagram|conte[úu]do|content|posts?)\b"},
}

PEDIDO = re.compile(r"\b(preciso|precisamos|procuro|procuramos|busco|buscamos|algu[ée]m (indica|conhece|sabe)|indica(m|ção)?|"
                    r"contratando|quero contratar|vou contratar|looking for|need (a|an|someone)|hiring|seeking|"
                    r"anyone (know|recommend)|recommend (a|an)|in need of)\b", re.I)
OFERTA = re.compile(r"\b(estou dispon[ií]ve\w*|dispon[ií]vel para|aceitando (projetos|clientes|commissions)|fa[çc]o (edi|sites?|artes)|"
                    r"me contrat|hire me|i'?m available|available for|open (to|for) (work|commissions)|dm me for|my services|"
                    r"meus servi[çc]os|portf[óo]lio no link|sou (editor|designer|dev|programador)|i'?m a (video editor|developer|designer))\b", re.I)
RECRUTADOR = re.compile(r"\b(recrutador\w*|recruiter|recruiting|talent (acquisition|partner)|headhunt\w*|vaga clt|clt|"
                        r"envie (seu )?curr[íi]culo|send (your )?(cv|resume)|job opening|apply (now|here)|nossa vaga|"
                        r"for (our|a) client|para (um|nosso) cliente|on behalf of)\b", re.I)
REVENDA = re.compile(r"\b(white.?label|for our clients|para nossos clientes|terceiriz\w+|ag[êe]ncia parceira|partner agency|outsourc\w+)\b", re.I)
SPAM = re.compile(r"\b(airdrop|crypto|cripto|nft|giveaway|sorteio|ganhe dinheiro|renda extra|link na bio|onlyfans|"
                  r"forex|bet|apostas?|pix gr[áa]tis)\b", re.I)
URGENCIA = re.compile(r"\b(urgente|urg[êe]ncia|hoje|amanh[ãa]|essa semana|esta semana|pra ontem|asap|urgent|today|tomorrow|"
                      r"this week|right away|immediately|imediato|quick turnaround)\b", re.I)
ORCAMENTO = re.compile(r"(R\$\s?\d|US?\$\s?\d|\$\d|€\s?\d|\b\d+\s?(k|mil|reais|dollars|usd)\b|\b(or[çc]amento|budget|pago|paid|pagamento|"
                       r"remunera\w+|valor|fixo mensal|per (hour|video|month)|por (v[íi]deo|m[êe]s|hora)|retainer)\b)", re.I)
PORTE = [("empresa", re.compile(r"\b(minha empresa|nossa empresa|meu neg[óo]cio|nosso neg[óo]cio|minha loja|nossa loja|"
                                r"my (company|startup|agency|store|business|shop|brand|saas|clinic|firm)|our (company|startup|agency|store|business|team|saas|brand)|"
                                r"nosso time|nossa equipe|startup|saas|ag[êe]ncia|agency|loja|store|e-?commerce|cl[íi]nica|escrit[óo]rio|ltda|"
                                r"founder|ceo|cto|co-?founder|fundador\w*|s[óo]cio|dono (de|da|do)|owner|empres[áa]ri\w+|empreendedor\w*|"
                                r"business owner|small business|pequena empresa|minha marca|restaurante|consult[óo]rio)\b", re.I)),
         ("criador", re.compile(r"\b(meu canal|my channel|canal (no|do) youtube|youtube channel|creator|criador de conte[úu]do|podcast|"
                                r"influenc\w+|streamer|reacts?|cortes|meus v[íi]deos|my videos)\b", re.I))]
# alcance (0-5) por quem pede: o alvo é empresa/empresário; criador tem lista e nota próprias; pessoa sem sinal fica atrás
ALCANCE = {"empresa": 5, "criador": 4, "pessoa/indefinido": 2}

NEGACAO = re.compile(r"\b(don'?t|doesn'?t|do not|does not|no|without|never|n[ãa]o|sem) (need|needs|needing|precisa\w*|precisar de)\b|"
                     r"\bwithout (a |any )?(developer|dev|coder|editor)|\bsem (precisar de )?(um )?(programador|dev|desenvolvedor)", re.I)
IMOVEL = re.compile(r"\b(acre|acres|redevelop\w*|neighbou?rhood|real estate|property|housing|parking lot|apartments?|homes?|"
                    r"terreno|loteamento|incorporadora|empreendimento imobili\w+|site near|land)\b", re.I)
EMPREGO = re.compile(r"\b(sal[áa]rio|salary|full.?time|tempo integral|join (our|the) team|benef[íi]cios|benefits|equity|"
                     r"apply|candidat\w+|lead (comms|the)|head of|formul[áa]rio)\b", re.I)


def frase_em(t, i):
    """A frase (entre . ! ? ou quebra de linha) que contém a posição i, com a pontuação final."""
    ini = max(t.rfind(c, 0, i) for c in ".!?\n") + 1
    fins = [j for j in (t.find(c, i) for c in ".!?\n") if j != -1]
    fim = min(fins) + 1 if fins else len(t)
    return t[ini:fim].strip()


def retorica(t, i):
    """'why are companies hiring editors?' / 'por que ninguém contrata dev?': pergunta sobre os outros, não pedido."""
    f = frase_em(t, i)
    k = f.find(t[i:i + 12])
    antes = f[:k] if k >= 0 else f
    return f.endswith("?") and bool(re.search(r"(?i)\b(why|how come|por ?que|será|quem disse|who says)\b", antes))


def pedido_do_servico(t, servicos):
    """Verbo de pedido com o serviço logo depois (até ~70 letras): 'preciso destrinchar...' solto não conta."""
    for m in PEDIDO.finditer(t):
        if retorica(t, m.start()):
            continue
        janela = t[m.start(): m.end() + 70]
        if any(re.search(SERVICOS[s]["chaves"], janela, re.I) for s in servicos):
            return True
    return False


TWEET = re.compile(r"https?://(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]{1,15})/status/(\d+)")
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def data_do_id(tid):
    """X usa snowflake: os 41 bits altos são ms desde 2010-11-04. Dá a data exata sem abrir o post."""
    try:
        ms = (int(tid) >> 22) + 1288834974657
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def conferir(tid, cache_dir=None):
    """Lê o post no dado público do embed do X. None = não deu para conferir (apagado, privado, fora do ar)."""
    f = Path(cache_dir) / f"tw-{tid}.json" if cache_dir else None
    if f and f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    try:
        q = urllib.request.Request(f"https://cdn.syndication.twimg.com/tweet-result?id={tid}&token=4&lang=pt",
                                   headers={"User-Agent": "Mozilla/5.0 (arkos-garimpo)"})
        d = json.load(urllib.request.urlopen(q, timeout=20))
    except Exception:
        return None
    if not isinstance(d, dict) or d.get("__typename") != "Tweet" or not d.get("text"):
        return None
    u = d.get("user") or {}
    r = {"texto": d["text"], "data": d.get("created_at"), "autor": u.get("screen_name"), "nome": u.get("name"),
         "likes": d.get("favorite_count"), "respostas": d.get("conversation_count"), "idioma": d.get("lang")}
    if f:
        f.parent.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    return r


def classificar(texto, servicos, agora, data):
    """Devolve dict com tipo, sinais, filtro (motivo de descarte ou None) e nota 0-100 + dimensões 0-5."""
    t = texto or ""
    tipo = [s for s in servicos if re.search(SERVICOS[s]["chaves"], t, re.I)]
    pede, oferta = pedido_do_servico(t, servicos), bool(OFERTA.search(t))
    filtro = None
    if SPAM.search(t): filtro = "spam"
    elif NEGACAO.search(t): filtro = "frase negativa (\"não precisa de dev\"), não é pedido"
    elif "developer" in t.lower() and IMOVEL.search(t): filtro = "developer de imóvel (incorporadora), fora do escopo"
    elif RECRUTADOR.search(t) or EMPREGO.search(t): filtro = "recrutador ou vaga de emprego"
    elif REVENDA.search(t): filtro = "agência revendendo"
    elif oferta and not re.search(r"^\W*(preciso|procuro|busco|looking for|need|hiring)", t, re.I): filtro = "é prestador se oferecendo, não pedido"
    elif not PEDIDO.search(t): filtro = "não é pedido explícito"
    elif not tipo: filtro = "serviço fora dos escolhidos"
    elif not pede: filtro = "pedido não é do serviço (verbo solto, longe do serviço)"
    urg, orc = bool(URGENCIA.search(t)), bool(ORCAMENTO.search(t))
    porte = next((nome for nome, rx in PORTE if rx.search(t)), "pessoa/indefinido")
    dias = (agora - data).days if data else None
    # rubrica do first-customer-finder: dor 25, fit 25, timing 20, alcance 15, evidência 15 (cada uma 0-5)
    dor = 5 if pede and (urg or orc) else 4 if pede else 2
    fit = 5 if len(tipo) == 1 else 4 if tipo else 1
    if dias is None: timing = 2
    elif dias <= 3: timing = 5
    elif dias <= 7: timing = 4
    elif dias <= 14: timing = 3
    else: timing = 1 if dias <= 45 else 0          # mais de 14 dias perde nota
    if urg and dias is not None and dias <= 7: timing = min(5, timing + 1)
    alcance = ALCANCE[porte]
    return {"tipo": tipo, "pedido": pede, "urgencia": urg, "orcamento": orc, "porte": porte, "dias": dias, "filtro": filtro,
            "categoria": "criador" if porte == "criador" else "empresa",
            "dim": {"dor": dor, "fit": fit, "timing": timing, "alcance": alcance}}


def nota(dim, evidencia):
    return round(dim["dor"] / 5 * 25 + dim["fit"] / 5 * 25 + dim["timing"] / 5 * 20 + dim["alcance"] / 5 * 15 + evidencia / 5 * 15)


def faixa(n):
    return "forte" if n >= 80 else "promissor" if n >= 65 else "plausível" if n >= 50 else "fora"


DETALHES = [  # (regex, pt, en): o que o post pede vira a frase do meio do rascunho
    (r"\b(cortes?|clips?)\b", "cortes com ritmo e legenda que prendem nos primeiros segundos", "tight clips with captions that hold the first seconds"),
    (r"\bmotion\b", "motion e pós junto com a edição", "motion and post along with the edit"),
    (r"\b(reels?|shorts|tiktok)\b", "vídeo vertical pensado para reels e shorts", "vertical edits built for reels and shorts"),
    (r"\b(youtube|yt|canal)\b", "edição para YouTube, do gancho à retenção", "YouTube edits, from hook to retention"),
    (r"\b(landing|site|website|p[áa]gina)\b", "site rápido e pronto para converter", "a fast site built to convert"),
    (r"\b(app|aplicativo|mobile)\b", "app com primeira versão funcional em poucas semanas", "an app with a working first version in a few weeks"),
    (r"\b(automa\w+|n8n|zapier|make\.com|integra\w+)\b", "automação ligando as ferramentas que vocês já usam", "automations wiring the tools you already use"),
    (r"\b(saas|mvp|sistema|plataforma|platform)\b", "MVP com escopo enxuto e entregas semanais", "an MVP with a lean scope and weekly deliveries"),
    (r"\b(shopify|e-?commerce|loja|store)\b", "loja virtual com checkout que converte", "a store with a checkout that converts"),
    (r"\b(bug|corrigir|fix|manuten[çc][ãa]o)\b", "correção e manutenção sem reescrever tudo", "fixes and maintenance without a rewrite"),
]


PESSOA = [(r"\bmeu\b", "seu"), (r"\bminha\b", "sua"), (r"\bmeus\b", "seus"), (r"\bminhas\b", "suas"), (r"\bnosso\b", "de vocês"),
          (r"\bnossa\b", "de vocês"), (r"\bmy\b", "your"), (r"\bour\b", "your"), (r"\bme\b", "you")]


def pedido_texto(t, tipos=()):
    """Trecho do próprio post que diz o que a pessoa procura (até ~90 letras), para citar no rascunho.
    Prefere o trecho que nomeia o serviço; pula pergunta retórica; troca 1ª pessoa por 2ª (meu canal -> seu canal)."""
    rx = r"(?i)\b(procuro|procuramos|preciso de|precisamos de|precisamos contratar|quero contratar|busco|buscamos|looking for|need|hiring|seeking)\b\s*[:\-—]?\s*(.{6,120}?)(?:[.!?\n]|$)"
    cands = [m for m in re.finditer(rx, t or "") if not retorica(t, m.start())]
    serv = [m for m in cands if any(re.search(SERVICOS[s]["chaves"], m.group(2), re.I) for s in tipos)]
    m = (serv or cands or [None])[0]
    if not m:
        return None
    s = re.sub(r"https?://\S+", "", re.sub(r"\s+", " ", m.group(2))).strip(" ,;:-—")
    s = re.sub(r"[^\w\s,.+&/'()-]", "", s).strip()
    for a, b in PESSOA:
        s = re.sub(a, b, s, flags=re.I)
    if s.isupper():
        s = s.lower()
    return s[:90].rsplit(" ", 1)[0] if len(s) > 90 else s


def rascunho(c):
    """Rascunho a partir do que o post pede (trecho citado + detalhe + urgência/orçamento). Menos de 90 palavras, nunca enviado."""
    t = c.get("texto") or ""
    en = (c.get("idioma") or "pt") == "en"
    s = c["tipo"][0] if c["tipo"] else "dev"
    padrao = {"dev": ("desenvolvimento", "a developer"), "video": ("edição de vídeo", "a video editor"), "design": ("design", "a designer"),
              "trafego": ("tráfego pago", "someone to run ads"), "social": ("social media", "a social media manager")}[s]
    oque = pedido_texto(t, c.get("tipo") or ()) or padrao[1 if en else 0]
    det = next(((pt, e) for rx, pt, e in DETALHES if re.search(rx, t, re.I)), None)
    if en:
        partes = [f"Hi! Saw you're looking for {oque}."]
        partes.append(f"That's what we do: {det[1]}." if det else "That's exactly what we do, with a fixed scope.")
        if c.get("urgencia"): partes.append("We can start this week.")
        if c.get("orcamento"): partes.append("Happy to send a fixed quote within your budget.")
        partes.append("Can I send 2-3 similar examples?")
    else:
        partes = [f"Oi! Vi que você procura {oque}."]
        partes.append(f"É o que a gente faz: {det[0]}." if det else "É exatamente o que a gente faz, com escopo fechado.")
        if c.get("urgencia"): partes.append("Dá para começar ainda esta semana.")
        if c.get("orcamento"): partes.append("Te mando um orçamento fechado dentro do que você falou.")
        partes.append("Posso te mandar 2 ou 3 exemplos parecidos?")
    r = " ".join(partes)
    return " ".join(r.split()[:85])


def rodar(tools, *args, timeout=300):
    """Chama pesq.py/x.py SEMPRE por chaves.py (as chaves nunca passam por aqui)."""
    cmd = [sys.executable, str(Path(tools) / "chaves.py"), "run", "--", sys.executable, *args]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run(cmd, cwd=tools, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                       env=env, creationflags=NO_WINDOW)
    return r.stdout


def json_da_saida(out):
    """x.py imprime avisos ('[x.py] ...', '[chaves] ...') antes do JSON; pega só a lista."""
    m = re.search(r"(?m)^\[\s*$|^\[\]\s*$|^\[\s*\{", out or "")
    if not m:
        return []
    try:
        d = json.loads(out[m.start():])
        return d if isinstance(d, list) else []
    except json.JSONDecodeError:
        return []


def coletar(tools, servicos, idiomas, por_consulta, usar_x, log):
    achados = {}
    for s in servicos:
        for idi in idiomas:
            for q in SERVICOS[s][idi]:
                out = rodar(tools, str(Path(tools) / "pesq.py"), "google", "garimpo-x", q, "x.com")
                for linha in out.splitlines():
                    m = TWEET.search(linha)
                    if m:
                        partes = linha.split(" | ")
                        achados.setdefault(m.group(2), {"id": m.group(2), "autor": m.group(1), "url": f"https://x.com/{m.group(1)}/status/{m.group(2)}",
                                                        "trecho": partes[-1] if len(partes) > 2 else "", "via": "google", "consulta": q})
                if usar_x:
                    itens = json_da_saida(rodar(tools, str(Path(tools) / "x.py"), q, "--n", str(por_consulta), "--modulo", "garimpo-x"))
                    for x in itens:
                        m = TWEET.search(x.get("url") or "")
                        if m:
                            achados.setdefault(m.group(2), {"id": m.group(2), "autor": m.group(1), "url": f"https://x.com/{m.group(1)}/status/{m.group(2)}",
                                                            "trecho": x.get("texto", ""), "via": "x.py", "consulta": q})
                log(f"  {s}/{idi} {q}: {len(achados)} posts no total")
    return list(achados.values())


def avaliar(posts, servicos, dias_max, cache_dir=None, agora=None, conferir_fn=conferir):
    agora = agora or datetime.now(timezone.utc)
    lista, descartes = [], []
    for p in posts:
        data = data_do_id(p["id"])
        if dias_max and data and (agora - data).days > dias_max:
            descartes.append({**p, "motivo": f"mais de {dias_max} dias"}); continue
        orig = conferir_fn(p["id"], cache_dir)
        if orig is None:
            descartes.append({**p, "motivo": "não conferido no original (apagado, privado ou fora do ar)"}); continue
        if orig.get("autor") and orig["autor"].lower() != p["autor"].lower():
            descartes.append({**p, "motivo": f"autor no original ({orig['autor']}) difere do link"}); continue
        c = classificar(orig["texto"], servicos, agora, data)
        item = {**p, "texto": orig["texto"], "data": data.date().isoformat() if data else orig.get("data"), "nome": orig.get("nome"),
                "likes": orig.get("likes"), "idioma": orig.get("idioma"), "conferido": "dado público do embed do X", **c}
        if c["filtro"]:
            descartes.append({**item, "motivo": c["filtro"]}); continue
        item["nota"] = nota(c["dim"], 5)
        item["faixa"] = faixa(item["nota"])
        item["rascunho"] = rascunho(item)
        (lista if item["nota"] >= 50 else descartes).append(item if item["nota"] >= 50 else {**item, "motivo": f"nota {item['nota']} < 50"})
    # empresa/empresário primeiro (o alvo); criador de conteúdo é categoria separada, ordenada pela própria nota
    lista.sort(key=lambda x: (x["categoria"] != "empresa", -x["nota"]))
    return lista, descartes


def janela_dias(posts, pedido):
    """--dias explícito vence; sem ele: 7 dias quando o Apify (x.py) trouxe post (dado fresco), 30 só com o Google."""
    if pedido is not None:
        return pedido
    return 7 if any(p.get("via") == "x.py" for p in posts) else 30


def md(lista, descartes, servicos, dias=None):
    emp = [x for x in lista if x["categoria"] == "empresa"]
    cri = [x for x in lista if x["categoria"] == "criador"]
    L = ["# Garimpo no X (proposta)", "", "Potenciais clientes por sinal público. **Nada foi enviado**: responder é decisão do dono, post a post.", "",
         f"Serviços: {', '.join(SERVICOS[s]['rotulo'] for s in servicos)} · janela {dias or '-'} dias · {len(emp)} empresas · "
         f"{len(cri)} criadores · {len(descartes)} descartados", ""]
    for titulo, grupo in (("Empresas e empresários (alvo)", emp), ("Criadores de conteúdo (categoria separada, nota própria)", cri)):
        L += [f"## {titulo}", ""]
        if not grupo:
            L += ["Nenhum nesta rodada.", ""]; continue
        L += ["| Nota | Faixa | Serviço | Quando | Urgência | Orçamento | Porte | Post |", "|---|---|---|---|---|---|---|---|"]
        for x in grupo:
            L.append(f"| {x['nota']} | {x['faixa']} | {', '.join(x['tipo'])} | {x['data']} ({x['dias']} d) | {'sim' if x['urgencia'] else '-'} | "
                     f"{'sim' if x['orcamento'] else '-'} | {x['porte']} | [@{x['autor']}]({x['url']}) |")
        L.append("")
    L += ["## Detalhe e rascunho de abordagem", ""]
    for x in lista:
        L += [f"### {x['nota']} · @{x['autor']} · {x['data']}", "", f"> {x['texto'][:500].replace(chr(10), ' ')}", "",
              f"Dimensões (0-5): dor {x['dim']['dor']}, fit {x['dim']['fit']}, timing {x['dim']['timing']}, alcance {x['dim']['alcance']}, evidência 5 · conferido: {x['conferido']}", "",
              f"Canal natural: responder no próprio post ou DM, se aberta. Rascunho (não enviado):", "", f"> {x['rascunho']}", ""]
    L += ["## Descartados", "", "| Post | Motivo |", "|---|---|"]
    for d in descartes:
        L.append(f"| {d['url']} | {d['motivo']} |")
    return "\n".join(L) + "\n"


def main(argv=None):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError: pass
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["buscar", "avaliar"]); ap.add_argument("--tools"); ap.add_argument("--entrada")
    ap.add_argument("--servicos", default="dev,video"); ap.add_argument("--idiomas", default="pt,en")
    ap.add_argument("--dias", type=int, default=None); ap.add_argument("--por-consulta", type=int, default=10)
    ap.add_argument("--sem-x", action="store_true"); ap.add_argument("--saida", required=True)
    a = ap.parse_args(argv)
    if "arkos.engine" in Path(a.saida).parts:
        print("recusado: entrega não fica dentro de arkos.engine", file=sys.stderr); return 2
    servicos = [s for s in a.servicos.split(",") if s]
    if not servicos or any(s not in SERVICOS for s in servicos):
        print(json.dumps({"excecao": "entrada_incompleta", "pergunta": f"quais serviços? opções: {', '.join(SERVICOS)}"}, ensure_ascii=False)); return 3
    saida = Path(a.saida); saida.mkdir(parents=True, exist_ok=True)
    if a.cmd == "buscar":
        if not a.tools or not (Path(a.tools) / "chaves.py").exists() or not (Path(a.tools) / "pesq.py").exists():
            print(json.dumps({"excecao": "fora_do_ar", "falta": "pasta _tools com chaves.py e pesq.py (--tools)"}, ensure_ascii=False)); return 3
        posts = coletar(a.tools, servicos, [i for i in a.idiomas.split(",") if i in ("pt", "en")], a.por_consulta, not a.sem_x,
                        lambda m: print(m, file=sys.stderr, flush=True))
        (saida / "coletados.json").write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        posts = json.loads(Path(a.entrada).read_text(encoding="utf-8"))
    dias = janela_dias(posts, a.dias)
    lista, descartes = avaliar(posts, servicos, dias, cache_dir=saida / "_conferidos")
    (saida / "garimpo.json").write_text(json.dumps({"dias": dias, "lista": lista, "descartes": descartes}, ensure_ascii=False, indent=1), encoding="utf-8")
    (saida / "garimpo.md").write_text(md(lista, descartes, servicos, dias), encoding="utf-8")
    print(json.dumps({"status": "ok", "na_lista": len(lista), "descartados": len(descartes), "pasta": str(saida)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
