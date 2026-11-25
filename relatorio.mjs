// /relatorio: sobe (se preciso) um servidor estático local para engine/report/reports e devolve a URL.
// Uso: node relatorio.mjs [--serve] [--porta 4810] [--stop]
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { readFileSync, existsSync, statSync, readdirSync, rmSync } from "node:fs";
import { join, extname, normalize } from "node:path";
import { REPORT_DIR, REPORT_STATE, writeJson, reportServer } from "./lib/core.mjs";

const ROOT = join(REPORT_DIR, "reports");
const args = process.argv.slice(2);
const portArg = Number(args[args.indexOf("--porta") + 1]) || 4810;

const TYPES = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".woff2": "font/woff2", ".ttf": "font/ttf", ".ico": "image/x-icon" };

function listReports() {
  try {
    return readdirSync(ROOT).filter((d) => existsSync(join(ROOT, d, "index.html")))
      .map((d) => ({ d, t: statSync(join(ROOT, d, "index.html")).mtimeMs })).sort((a, b) => b.t - a.t).map((x) => x.d);
  } catch { return []; }
}

function serve(port) {
  const srv = createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
    if (p === "/") {
      const items = listReports().map((d) => `<li><a href="/${d}/">${d}</a></li>`).join("");
      res.writeHead(200, { "content-type": TYPES[".html"] });
      return res.end(`<!doctype html><meta charset="utf-8"><title>ARKOS · relatórios</title><body style="background:#0A0B0D;color:#F2F3F5;font:16px system-ui;padding:40px"><h1 style="color:#C6F432">▚ ARKOS · relatórios</h1><ul>${items || "<li>nenhum relatório ainda</li>"}</ul>`);
    }
    const file = normalize(join(ROOT, p.endsWith("/") ? p + "index.html" : p));
    if (!file.startsWith(ROOT) || !existsSync(file) || statSync(file).isDirectory()) { res.writeHead(404); return res.end("não encontrado"); }
    res.writeHead(200, { "content-type": TYPES[extname(file)] || "application/octet-stream" });
    res.end(readFileSync(file));
  });
  srv.listen(port, "127.0.0.1", () => writeJson(REPORT_STATE, { port, pid: process.pid, root: ROOT, startedAt: new Date().toISOString() }));
  srv.on("error", (e) => { console.error(e.message); process.exit(1); });
}

// linha de pensamento do relatório: coletar (fatos da execução) e gerar (site em workspace/<cliente>/<projeto>/relatorio/)
const opt = (n) => { const i = args.indexOf(n); return i === -1 ? undefined : args[i + 1]; };
if (args[0] === "coletar" || args[0] === "gerar") {
  const fluxo = await import("./lib/relatorio-fluxo.mjs");
  const o = { cliente: opt("--cliente"), projeto: opt("--projeto"), execucao: opt("--execucao") };
  if (args[0] === "coletar") { const f = fluxo.coletar(o); console.log(JSON.stringify(f, null, 2)); process.exit(f.erro ? 1 : 0); }
  if (!args[1] || !existsSync(args[1])) { console.error("uso: node relatorio.mjs gerar <conteudo.json> --cliente <c> --projeto <p> [--execucao <id>] [--abrir]"); process.exit(2); }
  const r = fluxo.gerar(args[1], o);
  if (r.erro) { console.error(r.erro); process.exit(1); }
  console.log(`relatório gerado: ${r.pagina}`);
  console.log(`índice do cliente: ${r.indice}`);
  if (args.includes("--abrir")) fluxo.abrir(r.pagina);
  process.exit(0);
}

if (args.includes("--serve")) {
  serve(portArg);
} else if (args.includes("--stop")) {
  const r = reportServer();
  if (r) { try { process.kill(r.pid); } catch {} }
  try { rmSync(REPORT_STATE); } catch {}
  console.log(r ? `relatório parado (:${r.port})` : "relatório não estava rodando");
} else {
  let r = reportServer();
  if (!r) {
    const child = spawn(process.execPath, [process.argv[1], "--serve", "--porta", String(portArg)], { detached: true, stdio: "ignore", windowsHide: true });
    child.unref();
    for (let i = 0; i < 40 && !(r = reportServer()); i++) await new Promise((ok) => setTimeout(ok, 100));
  }
  if (!r) { console.log("não consegui subir o servidor do relatório"); process.exit(1); }
  const last = listReports()[0];
  const url = `http://127.0.0.1:${r.port}/${last ? last + "/" : ""}`;
  console.log(`relatório no ar: ${url}`);
  console.log(`todos: http://127.0.0.1:${r.port}/`);
  if (args.includes("--abrir")) {
    // dentro do O Maestro abre no portal; fora dele, no navegador padrão (sem janela de terminal)
    const viaMaestro = process.env.OMAESTRO_TERMINAL_ID;
    const cmd = viaMaestro ? ["maestro", ["open", url]] : ["rundll32", ["url.dll,FileProtocolHandler", url]];
    const c = spawn(cmd[0], cmd[1], { detached: true, stdio: "ignore", windowsHide: true, shell: viaMaestro ? true : false });
    c.on("error", () => console.log("abra o endereço acima no navegador"));
    c.unref();
  }
}
