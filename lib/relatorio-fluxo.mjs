// Linha de pensamento do relatório da ARKOS.
// coletar: fatos crus da execução (o Claude escreve o JSON do SCHEMA.md em cima deles, sem inventar).
// gerar:   roda engine/report/arkos-report.mjs em <casa>/workspace/<cliente>/<projeto>/relatorio/<data-id>/,
//          refaz o índice workspace/<cliente>/relatorios.html e abre no portal/navegador.
import { spawn, spawnSync } from "node:child_process";
import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { REPORT_DIR, pastasExecucoes } from "./core.mjs";
import { raizArkos } from "./casa.mjs";

export const slug = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9_]+/g, "-").replace(/^-|-$/g, "").slice(0, 60);
const lerJson = (f) => { try { return JSON.parse(readFileSync(f, "utf8").replace(/^﻿/, "")); } catch { return null; } };
const nome = (p) => p.split(/[\\/]/).pop();

export function ultimaExecucao(raiz) {
  const todas = [];
  for (const base of pastasExecucoes(raiz)) { try { for (const d of readdirSync(base)) todas.push(join(base, d)); } catch {} }
  return todas.sort((a, b) => (nome(a) < nome(b) ? 1 : -1))[0] || null;
}

function listarArquivos(dir, max = 200, base = dir, out = []) {
  try {
    for (const n of readdirSync(dir)) {
      if (out.length >= max || n === "relatorio" || n.startsWith(".")) continue;
      const f = join(dir, n), st = statSync(f);
      if (st.isDirectory()) listarArquivos(f, max, base, out);
      else out.push({ arquivo: f.slice(base.length + 1).replace(/\\/g, "/"), bytes: st.size, alterado: new Date(st.mtimeMs).toISOString() });
    }
  } catch {}
  return out;
}

// { execucao, cliente, projeto, pasta_entregas, aviso, entradas, rota, estado, saida, aprovacoes, artefatos, schema, destino, regras }
export function coletar({ raiz = raizArkos(process.cwd()), execucao, cliente, projeto } = {}) {
  const dir = execucao ? (existsSync(execucao) ? execucao : pastasExecucoes(raiz).map((b) => join(b, execucao)).find(existsSync)) : ultimaExecucao(raiz);
  if (!dir || !existsSync(dir)) return { erro: "nenhuma execução em arkos.engine/execucoes" };
  const ler = (n) => lerJson(join(dir, n));
  const entradas = ler("entradas.json"), saida = ler("saida.json");
  const resp = entradas?.respostas || entradas || {};
  const c = slug(cliente || saida?.cliente || resp.cliente) || null;
  const p = slug(projeto || saida?.projeto || resp.projeto) || null;
  const pasta = c && p ? join(raiz, "workspace", c, p) : null;
  return {
    execucao: { id: nome(dir), pasta: dir },
    cliente: c, projeto: p, pasta_entregas: pasta,
    aviso: ler("aviso.json"), entradas, rota: ler("rota.json"), estado: ler("estado.json"), saida,
    aprovacoes: listarArquivos(join(dir, "aprovacoes")),
    artefatos: pasta ? listarArquivos(pasta) : [],
    schema: join(REPORT_DIR, "SCHEMA.md"),
    destino: pasta ? join(pasta, "relatorio") : null,
    regras: "Escreva o JSON no formato do SCHEMA.md só com estes fatos e as fontes citadas. Número sem fonte não entra; estimativa leva '(estimativa)'. Pendência do prestador: owner voce, status waiting. Depois rode: node relatorio.mjs gerar <arquivo.json> --cliente <c> --projeto <p> --execucao <id> --abrir",
  };
}

export function indiceCliente(raiz, cliente) {
  const base = join(raiz, "workspace", cliente);
  const itens = [];
  let projetos = [];
  try { projetos = readdirSync(base).filter((p) => existsSync(join(base, p, "relatorio"))); } catch {}
  for (const p of projetos) for (const r of readdirSync(join(base, p, "relatorio"))) {
    const idx = join(base, p, "relatorio", r, "index.html");
    if (!existsSync(idx)) continue;
    const j = lerJson(join(base, p, "relatorio", r, "report.json")) || {};
    itens.push({ projeto: p, pasta: r, titulo: j.title || r, tipo: j.kind || "", data: j.date || "", t: statSync(idx).mtimeMs });
  }
  itens.sort((a, b) => b.t - a.t);
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
  const linhas = itens.map((i) => `<tr><td><a href="${encodeURI(`${i.projeto}/relatorio/${i.pasta}/index.html`)}">${esc(i.titulo)}</a></td><td>${esc(i.projeto)}</td><td>${esc(i.tipo)}</td><td>${esc(i.data || new Date(i.t).toLocaleDateString("pt-BR"))}</td></tr>`).join("");
  const html = `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ARKOS · relatórios · ${esc(cliente)}</title>
<style>body{background:#0A0B0D;color:#F2F3F5;font:15px/1.5 system-ui,sans-serif;margin:0 auto;padding:40px 16px;max-width:960px}h1{font-size:20px;letter-spacing:.3em;margin:0;font-weight:600}h1 b{color:#C6F432}p{color:#8b9099}table{width:100%;border-collapse:collapse;margin-top:24px}td,th{text-align:left;padding:10px 8px;border-bottom:1px solid #22252b}th{color:#8b9099;font-weight:500;font-size:13px}a{color:#C6F432;text-decoration:none}a:hover{text-decoration:underline}@media(max-width:560px){td:nth-child(3),th:nth-child(3){display:none}}</style>
<h1><b>A R K O S</b>&nbsp; RELATÓRIOS</h1><p>Cliente <strong>${esc(cliente)}</strong> · ${itens.length} relatório(s) · atualizado em ${new Date().toLocaleString("pt-BR")}</p>
<table><tr><th>Relatório</th><th>Projeto</th><th>Tipo</th><th>Data</th></tr>${linhas || '<tr><td colspan="4">nenhum relatório ainda</td></tr>'}</table>`;
  writeFileSync(join(base, "relatorios.html"), html, "utf8");
  return join(base, "relatorios.html");
}

export function abrir(alvo) {
  const viaMaestro = process.env.OMAESTRO_TERMINAL_ID;
  const url = "file:///" + alvo.replace(/\\/g, "/");
  const cmd = viaMaestro ? ["maestro", ["open", JSON.stringify(alvo)]] : ["rundll32", ["url.dll,FileProtocolHandler", url]];
  const c = spawn(cmd[0], cmd[1], { detached: true, stdio: "ignore", windowsHide: true, shell: !!viaMaestro });
  c.on("error", () => {});
  c.unref();
}

// gera o site do relatório; devolve { pagina, indice } ou { erro }
export function gerar(src, { raiz = raizArkos(process.cwd()), cliente, projeto, execucao } = {}) {
  const dados = lerJson(src);
  if (!dados?.title || !Array.isArray(dados.sections)) return { erro: "JSON fora do SCHEMA.md: faltam title/sections" };
  const c = slug(cliente || dados.cliente || "geral"), p = slug(projeto || dados.projeto || "geral");
  const id = slug(execucao || dados.run || dados.id || "relatorio");
  const hoje = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const out = join(raiz, "workspace", c, p, "relatorio", id.startsWith(hoje) ? id : `${hoje}-${id}`);
  dados.id ||= `${c}-${p}-${id}`;
  mkdirSync(out, { recursive: true });
  const tmp = join(out, "_conteudo.json");
  writeFileSync(tmp, JSON.stringify(dados, null, 2), "utf8");
  const r = spawnSync(process.execPath, [join(REPORT_DIR, "arkos-report.mjs"), tmp, "--out", out, "--quiet"], { encoding: "utf8", windowsHide: true });
  rmSync(tmp, { force: true });
  if (r.status !== 0) return { erro: r.stderr || "o gerador falhou" };
  return { pagina: join(out, "index.html"), indice: indiceCliente(raiz, c) };
}
