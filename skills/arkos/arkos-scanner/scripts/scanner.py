#!/usr/bin/env python3
"""arkos-scanner: varredura estatica de uma skill antes de instalar. Stdlib.

Nao executa nada. Le os arquivos de texto da pasta e casa cada linha com regras
de padrao perigoso. Inclui a regra da casa (janela visivel / subprocesso sem
janela oculta no Windows) e lista o que nao conseguiu varrer.
"""
import argparse
import json
import os
import re
import sys

# (regra, severidade, regex) por linha
REGRAS = [
    ("shell_destrutivo", "alto", re.compile(r"rm\s+-rf|rmdir\s+/s|del\s+/[sq]|format\s+[a-z]:|mkfs|>\s*/dev/sd")),
    ("rede_para_exec", "alto", re.compile(r"(curl|wget)[^\n]*\|\s*(sh|bash)|iwr[^\n]*\|\s*iex|Invoke-Expression|\beval\s*\(|\bexec\s*\(")),
    ("segredo_no_codigo", "alto", re.compile(r"sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("git_destrutivo", "alto", re.compile(r"push\s+--force|reset\s+--hard|clean\s+-[fd]+|--no-verify")),
    ("shell_true", "alto", re.compile(r"shell\s*=\s*True")),
    ("powershell_encoded", "alto", re.compile(r"powershell[^\n]*(-enc\b|-EncodedCommand)")),
    ("os_system", "medio", re.compile(r"os\.system\s*\(")),
    # le segredo: so com verbo de acesso perto do .env/.secrets (evita "nunca le .env")
    ("le_segredo", "medio", re.compile(r"(open|read|load|with\s+open|Get-Content|\bcat\b|source|dotenv|env_file)[^\n]{0,40}\.(env|secrets)|id_rsa|credentials\.json")),
    ("janela_visivel", "medio", re.compile(r"DETACHED_PROCESS|0x00000008\b|cmd\s+/c\s+start|Start-Process(?![^\n]*-WindowStyle\s+Hidden)")),
    ("ofuscacao", "medio", re.compile(r"b64decode|atob\s*\(|fromCharCode|(?:\\x[0-9a-fA-F]{2}){4,}")),
]

# deteccao de subprocesso (file-level): se existe e o arquivo NAO cita janela oculta
SPAWN = re.compile(r"subprocess\.(run|Popen|call|check_output)|\bPopen\s*\(|child_process|\.spawn\s*\(|execSync|os\.system\s*\(")
TEM_JANELA_OCULTA = re.compile(r"CREATE_NO_WINDOW|0x08000000|windowsHide")
FIXTURE = re.compile(r"scanner:\s*fixture")
# linha que DEFINE um padrao (re.compile/regex literal) ou marcada p/ ignorar nao
# e codigo perigoso: e a lista de assinaturas do proprio scanner. Evita que um
# scanner casque os proprios termos de deteccao.  # scanner: ignore
DEF_REGRA = re.compile(r"re\.compile\(|scanner:\s*ignore")

PULAR_DIR = {".git", "node_modules", "__pycache__", "graphify-out", ".arkos"}
EXTS = {".md", ".py", ".js", ".mjs", ".cjs", ".ts", ".sh", ".ps1", ".psm1", ".bat",
        ".cmd", ".json", ".txt", ".yaml", ".yml", ".toml", ".html", ".xml"}
# assets que nao precisam de varredura nem viram "nao varrido"
ASSET = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".woff", ".woff2",
         ".ttf", ".otf", ".pdf", ".mp4", ".mp3", ".zip", ".lock", ".map"}
MAX_BYTES = 2_000_000


def _em_tests(arquivo):
    return re.search(r"(^|[\\/])tests?([\\/]|$)", arquivo) is not None


def escanear_texto(texto, arquivo):
    achados = []
    tem_oculta = bool(TEM_JANELA_OCULTA.search(texto))
    em_tests = _em_tests(arquivo)
    for i, linha in enumerate(texto.splitlines(), 1):
        if DEF_REGRA.search(linha):  # linha de definicao de regra: nao e execucao
            continue
        fixture = bool(FIXTURE.search(linha))
        for regra, sev, rx in REGRAS:
            if rx.search(linha):
                s = sev
                # FP: em tests/ ou linha marcada fixture, 'alto' cai para 'medio'
                if s == "alto" and (em_tests or fixture):
                    s = "medio"
                achados.append({"arquivo": arquivo, "linha": i, "regra": regra,
                                "severidade": s, "trecho": linha.strip()[:160]})
    # file-level: subprocesso sem janela oculta (regra da casa)
    if SPAWN.search(texto) and not tem_oculta:
        achados.append({"arquivo": arquivo, "linha": 0,
                        "regra": "subprocesso_sem_janela_oculta", "severidade": "medio",
                        "trecho": "usa subprocesso e nao cita CREATE_NO_WINDOW/windowsHide"})
    return achados


def escanear_pasta(pasta):
    achados, nao_varridos = [], []
    for raiz, dirs, arqs in os.walk(pasta):
        dirs[:] = [d for d in dirs if d not in PULAR_DIR]
        for a in arqs:
            caminho = os.path.join(raiz, a)
            rel = os.path.relpath(caminho, pasta)
            ext = os.path.splitext(a)[1].lower()
            if ext in ASSET:
                continue
            if ext not in EXTS:
                nao_varridos.append(rel + " (extensao nao coberta)")
                continue
            try:
                if os.path.getsize(caminho) > MAX_BYTES:
                    nao_varridos.append(rel + " (grande demais)")
                    continue
                with open(caminho, "rb") as f:
                    bruto = f.read()
                if b"\x00" in bruto[:4096]:
                    nao_varridos.append(rel + " (binario)")
                    continue
                txt = bruto.decode("utf-8", errors="ignore")
            except OSError:
                nao_varridos.append(rel + " (erro de leitura)")
                continue
            achados += escanear_texto(txt, rel)
    return achados, nao_varridos


def veredito(achados, nao_varridos=None):
    nao_varridos = nao_varridos or []
    if nao_varridos:
        achados = achados + [{"arquivo": "(varios)", "linha": 0, "regra": "nao_varrido",
                              "severidade": "medio",
                              "trecho": f"{len(nao_varridos)} arquivo(s) nao varridos: "
                                        + ", ".join(nao_varridos[:8])}]
    alto = sum(1 for a in achados if a["severidade"] == "alto")
    medio = sum(1 for a in achados if a["severidade"] == "medio")
    if alto:
        v = "bloquear"
    elif medio:
        v = "revisar"
    else:
        v = "liberar"
    return {"veredito": v, "resumo": {"alto": alto, "medio": medio},
            "nao_varridos": nao_varridos, "achados": achados}


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # console do Windows (charmap)
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(prog="scanner")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("pasta")
    args = ap.parse_args(argv)
    if args.cmd == "scan":
        if not os.path.isdir(args.pasta):
            print(json.dumps({"erro": "pasta inexistente", "veredito": "bloquear"},
                             ensure_ascii=False))
            return 2
        achados, nao_varridos = escanear_pasta(args.pasta)
        res = veredito(achados, nao_varridos)
        print(json.dumps(res, ensure_ascii=False))
        return 2 if res["resumo"]["alto"] else (1 if res["resumo"]["medio"] else 0)
    return 1


if __name__ == "__main__":
    sys.exit(main())
