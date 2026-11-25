"""Base comum das skills de arquivo da ARKOS (arkos-docx, -pdf, -pptx, -xlsx, -artes, -site).

Escrito do zero para a ARKOS. Resolve a pasta-casa, aplica a marca, roda subprocesso
sem janela e para cedo quando falta entrada (exceção `entrada_incompleta`).
"""
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import unicodedata

# ---- marca ARKOS (Volt só em fundo escuro; no papel claro a marca é monocromática)
INK = "0A0B0D"
VOLT = "C6F432"
GRAPHITE = "1C1E22"
STEEL = "6B7079"
PAPER = "F1F2EF"
LINE = "E1E3DF"
FONTE = "Inter Tight"
FONTE_MONO = "JetBrains Mono"
AUTOR = "ARKOS Engine"

CREATE_NO_WINDOW = 0x08000000

ENTRADA_INCOMPLETA = 2  # código de saída da exceção entrada_incompleta
FORA_DO_AR = 3          # ferramenta externa indisponível e sem alternativa


def slug(texto, limite=64):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return (t[:limite].rstrip("-")) or "arquivo"


def hoje():
    return _dt.date.today().isoformat()


def carregar_spec(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def exigir(spec, campos, contexto="spec"):
    """Exceção entrada_incompleta: lista tudo o que falta de uma vez e para sem escrever nada."""
    faltando = []
    for c in campos:
        v = spec
        for parte in c.split("."):
            v = v.get(parte) if isinstance(v, dict) else None
        if v in (None, "", [], {}):
            faltando.append(c)
    if faltando:
        print(json.dumps({"status": "aguardando", "excecao": "entrada_incompleta",
                          "contexto": contexto, "falta": faltando}, ensure_ascii=False))
        sys.exit(ENTRADA_INCOMPLETA)


def pasta_casa(casa, cliente, projeto, sub):
    """workspace/<cliente>/<projeto>/<sub>/ dentro da casa do prestador."""
    if not (casa and cliente and projeto):
        print(json.dumps({"status": "aguardando", "excecao": "entrada_incompleta",
                          "falta": [n for n, v in (("--casa", casa), ("--cliente", cliente), ("--projeto", projeto)) if not v]},
                         ensure_ascii=False))
        sys.exit(ENTRADA_INCOMPLETA)
    p = os.path.join(casa, "workspace", slug(cliente), slug(projeto), sub)
    os.makedirs(p, exist_ok=True)
    return p


def caminho_novo(pasta, titulo, ext):
    """<slug>-<AAAA-MM-DD>.<ext>; nunca sobrescreve: -v2, -v3..."""
    base = f"{slug(titulo)}-{hoje()}"
    alvo = os.path.join(pasta, f"{base}.{ext}")
    n = 2
    while os.path.exists(alvo):
        alvo = os.path.join(pasta, f"{base}-v{n}.{ext}")
        n += 1
    return alvo


def rodar_oculto(cmd, timeout=120, **kw):
    """Subprocesso sem janela no Windows: CREATE_NO_WINDOW (a flag de processo destacado faz os filhos abrirem janela)."""
    flags = CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=flags, **kw)


def achar_chrome():
    cands = [os.environ.get("ARKOS_CHROME", ""),
             r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
             "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    return next((c for c in cands if c and os.path.isfile(c)), None)


def saida(status, **dados):
    print(json.dumps({"status": status, **dados}, ensure_ascii=False))


def base_sem_data(caminho):
    """Nome do arquivo sem extensão, sem a data e o -vN que caminho_novo põe."""
    b = os.path.splitext(os.path.basename(caminho))[0]
    return re.sub(r"-\d{4}-\d{2}-\d{2}(-v\d+)?$", "", b)


def aplicar_chaves(obj, chaves):
    """Troca {{chave}} em todo texto do spec (dict/list/str)."""
    if isinstance(obj, str):
        for k, v in (chaves or {}).items():
            obj = obj.replace("{{" + k + "}}", str(v))
        return obj
    if isinstance(obj, list):
        return [aplicar_chaves(x, chaves) for x in obj]
    if isinstance(obj, dict):
        return {k: aplicar_chaves(v, chaves) for k, v in obj.items()}
    return obj


def pendentes(obj):
    """Placeholders {{...}} que sobraram: documento com isso não está pronto."""
    return sorted(set(re.findall(r"\{\{([^{}]+)\}\}", json.dumps(obj, ensure_ascii=False))))


try:  # acentos certos no console do Windows
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
