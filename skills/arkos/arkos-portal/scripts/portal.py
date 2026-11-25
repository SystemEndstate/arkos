#!/usr/bin/env python3
"""arkos-portal: conferir paginas com Playwright headless (casca sobre node).

Sala limpa: usa o Playwright publico (Apache-2.0) via node, janela oculta. Monta o
roteiro node; em --dry-run nao executa. Somente stdlib.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _raiz_node(cwd=None):
    """Diretorio para gravar o roteiro .js: precisa ter node_modules/playwright
    alcancavel subindo a arvore. %TEMP% nao tem; por isso gravamos no projeto."""
    return cwd or os.getcwd()


def _node_path_env(cwd):
    """NODE_PATH apontando para onde o playwright resolve (robustez extra)."""
    env = dict(os.environ)
    extra = os.path.join(cwd, "node_modules")
    try:
        p = subprocess.run(
            ["node", "-e", "process.stdout.write(require.resolve('playwright'))"],
            capture_output=True, text=True, cwd=cwd, timeout=15,
            **({"creationflags": CREATE_NO_WINDOW} if os.name == "nt" else {}))
        if p.returncode == 0 and p.stdout:
            # .../node_modules/playwright/index.js -> .../node_modules
            nm = p.stdout
            idx = nm.replace("\\", "/").rfind("/node_modules/")
            if idx != -1:
                extra = os.pathsep.join([extra, nm[:idx + len("/node_modules")]])
    except (OSError, subprocess.SubprocessError):
        pass
    env["NODE_PATH"] = os.pathsep.join(filter(None, [extra, env.get("NODE_PATH", "")]))
    return env


def url_valida(url):
    return bool(re.match(r"^(https?://|file://)", url or ""))


def disponivel():
    return shutil.which("node") is not None


def roteiro_node(url, out, texto_esperado, seletor):
    """Script node headless. windowsHide fica na chamada do subprocesso node."""
    esp = json.dumps(texto_esperado or "")
    sel = json.dumps(seletor or "")
    return f"""const {{ chromium }} = require('playwright');
(async () => {{
  const browser = await chromium.launch({{ headless: true }});
  const page = await browser.newPage();
  const erros = [];
  page.on('console', m => {{ if (m.type() === 'error') erros.push(m.text()); }});
  page.on('pageerror', e => erros.push(String(e)));
  try {{
    await page.goto({json.dumps(url)}, {{ waitUntil: 'networkidle', timeout: 30000 }});
    await page.screenshot({{ path: {json.dumps(out)}, fullPage: true }});
    let encontrou = true;
    const esperado = {esp}, seletor = {sel};
    if (esperado) encontrou = (await page.content()).includes(esperado);
    if (seletor) encontrou = encontrou && (await page.$(seletor)) !== null;
    console.log(JSON.stringify({{ url: {json.dumps(url)}, print: {json.dumps(out)},
      console_erros: erros, encontrou }}));
  }} catch (e) {{
    console.log(JSON.stringify({{ url: {json.dumps(url)}, erro: String(e),
      console_erros: erros, encontrou: false }}));
  }} finally {{ await browser.close(); }}
}})();
"""


def testar(url, out, texto_esperado=None, seletor=None, dry_run=False, cwd=None):
    if not url_valida(url):
        return {"erro": "url invalida (use http(s) ou file://)", "url": url}
    cwd = _raiz_node(cwd)
    script = roteiro_node(url, out, texto_esperado, seletor)
    if dry_run:
        return {"url": url, "dry_run": True, "script_node": script,
                "cmd": ["node", "<roteiro no projeto>"], "cwd": cwd,
                "janela": "oculta" if os.name == "nt" else "n/a"}
    if not disponivel():
        return {"erro": "node ausente",
                "instrucao": "npm i -D playwright && npx playwright install chromium"}
    # grava o roteiro DENTRO do projeto (nao em %TEMP%): require('playwright') resolve
    tmp_path = os.path.join(cwd, f".arkos-portal-{uuid.uuid4().hex}.js")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(script)
        kw = {"capture_output": True, "text": True, "timeout": 90,
              "cwd": cwd, "env": _node_path_env(cwd)}
        if os.name == "nt":
            kw["creationflags"] = CREATE_NO_WINDOW
        p = subprocess.run(["node", tmp_path], **kw)
        try:
            return json.loads(p.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return {"erro": "saida do node ilegivel", "stderr": p.stderr[-500:]}
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def check():
    if not disponivel():
        return {"ok": False, "instrucao": "instalar node + playwright"}
    try:
        kw = {"capture_output": True, "text": True, "timeout": 20}
        if os.name == "nt":
            kw["creationflags"] = CREATE_NO_WINDOW
        p = subprocess.run(["node", "--version"], **kw)
        return {"ok": p.returncode == 0, "node": p.stdout.strip()}
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "motivo": str(e)}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="portal")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    t = sub.add_parser("testar")
    t.add_argument("--url", required=True)
    t.add_argument("--out", default="print.png")
    t.add_argument("--texto-esperado", default=None)
    t.add_argument("--seletor", default=None)
    t.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "check":
        print(json.dumps(check(), ensure_ascii=False))
        return 0
    if args.cmd == "testar":
        res = testar(args.url, args.out, args.texto_esperado, args.seletor, args.dry_run)
        print(json.dumps(res, ensure_ascii=False))
        return 0 if "erro" not in res else 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
