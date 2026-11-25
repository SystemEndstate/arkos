// Núcleo da CLI ARKOS: caminhos, config, estado de sessão, classificador de módulos.
// Sem dependências. Tudo síncrono e rápido (a statusLine roda a cada atualização).
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync, statSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { homedir, userInfo } from "node:os";
import { fileURLToPath } from "node:url";

export const CLI_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const ARKOS_ROOT = resolve(CLI_DIR, "..");
export const HOME_DIR = process.env.ARKOS_HOME || join(homedir(), ".arkos");
export const SESS_DIR = join(HOME_DIR, "sessions");
export const PKG = readJson(join(CLI_DIR, "package.json"), { version: "0.0.0" });
export const VERSION = PKG.version;

export function readJson(p, fallback = null) {
  try { return JSON.parse(readFileSync(p, "utf8").replace(/^﻿/, "")); } catch { return fallback; }
}

export function writeJson(p, obj) {
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(obj, null, 2));
}

// ---------- módulos (dados em data/, lógica em src/classificador.mjs) ----------
export { modulos as modules, classificar, proximosElos, anterioresElos, usarPlano, planoAtual } from "../src/classificador.mjs";
import { proximosElos as _proximos, anterioresElos as _anteriores } from "../src/classificador.mjs";

// ---------- estado da sessão ----------
// Chave do estado: a execução do `arkos` (ARKOS_RUN_ID, sobrevive a /clear) ou o session_id.
export function stateKey(sessionId) { return process.env.ARKOS_RUN_ID || sessionId; }
export function sessionPath(id) {
  const safe = String(stateKey(id) || "sem-sessao").replace(/[^a-zA-Z0-9_-]/g, "");
  return join(SESS_DIR, `${safe || "sem-sessao"}.json`);
}
export function loadState(id) { return readJson(sessionPath(id), {}); }
export function saveState(id, st) { st.updatedAt = new Date().toISOString(); writeJson(sessionPath(id), st); }

// ---------- execuções (<casa>/arkos.engine/execucoes/<id>/; o .arkos/execucoes antigo ainda é lido) ----------
export const pastasExecucoes = (raiz) => [join(raiz, "arkos.engine", "execucoes"), join(raiz, ".arkos", "execucoes")];
// O terminal escreve aviso.json; as skills escrevem entradas.json, rota.json e estado.json.
export function novaExecucao(raizProjeto, dados) {
  const d = new Date();
  const carimbo = d.toISOString().slice(0, 19).replace(/[-:T]/g, "").replace(/^(\d{8})(\d{6})$/, "$1-$2");
  const id = `${carimbo}-${dados.playbook}-${Math.random().toString(36).slice(2, 6)}`;
  const dir = join(pastasExecucoes(raizProjeto)[0], id);
  writeJson(join(dir, "aviso.json"), { id, criado_em: d.toISOString(), ...dados });
  return { id, dir };
}

// Execução anterior do mesmo projeto cuja saida.json (status feito) é o elo anterior da esteira deste playbook.
export function saidaAnterior(raizProjeto, playbookId) {
  return saidasAnteriores(raizProjeto, playbookId, 1)[0]?.arquivo || null;
}

// Até `max` elos anteriores concluídos, o mais recente de cada cliente/projeto (o intake escolhe o do mesmo cliente).
export function saidasAnteriores(raizProjeto, playbookId, max = 5) {
  const antes = new Set(_anteriores(playbookId));
  if (!antes.size) return [];
  let dirs = [];
  for (const base of pastasExecucoes(raizProjeto)) { try { dirs.push(...readdirSync(base).map((d) => [d, base])); } catch {} }
  dirs.sort((a, b) => (a[0] < b[0] ? 1 : -1));
  const vistos = new Set(), lista = [];
  for (const [d, base] of dirs) {
    const f = join(base, d, "saida.json"), s = readJson(f);
    if (!s || !antes.has(s.playbook) || !/^feito/i.test(String(s.status || ""))) continue;
    const chave = `${s.cliente || ""}/${s.projeto || ""}`;
    if (vistos.has(chave)) continue;
    vistos.add(chave);
    lista.push({ arquivo: f, cliente: s.cliente || null, projeto: s.projeto || null });
    if (lista.length >= max) break;
  }
  return lista;
}

// Progresso para o rodapé: estado.json (arkos-playbook) > rota.json (arkos-roteador) > lista de tarefas/passo.mjs.
export function progresso(st) {
  const dir = st.execucao?.dir;
  // saida.json (arkos-playbook, fim da execução): status e próximo elo da esteira
  const extra = () => {
    const s = dir && readJson(join(dir, "saida.json"));
    if (!s) return {};
    const feito = /^feito/i.test(String(s.status || ""));
    const proximo = feito ? (s.proximos?.[0] || _proximos(s.playbook || st.playbookId)[0] || null) : null;
    return { saida: String(s.status || ""), proximo };
  };
  if (dir) {
    for (const f of ["estado.json", "rota.json"]) {
      const e = readJson(join(dir, f));
      if (!e) continue;
      let total = Number(e.total) || 0, done = null, current = e.etapa_atual || e.atual || null;
      const lista = Array.isArray(e.etapas) ? e.etapas : e.etapas && typeof e.etapas === "object" ? Object.entries(e.etapas).map(([id, v]) => ({ id, ...(typeof v === "string" ? { status: v } : v) })) : null;
      if (lista) {
        total ||= lista.length;
        done = lista.filter((x) => /^(conclu|feito|ok|done|completed)/i.test(String(x.status || ""))).length;
        current ||= lista.find((x) => /^(andamento|rodando|em_andamento|running|in_progress|aguardando|portao)/i.test(String(x.status || "")))?.nome || null;
      }
      if (done === null && e.passo) done = /^(conclu|done|completed)/i.test(String(e.status || "")) ? Number(e.passo) : Number(e.passo) - 1;
      const bloqueada = (lista || []).some((x) => /^bloquead/i.test(String(x.status || ""))) || /^bloquead/i.test(String(e.status || ""));
      if (total && done !== null) return { ...extra(), done: Math.max(0, Math.min(done, total)), total, current: current || st.current, fonte: f, bloqueada };
    }
  }
  return { ...extra(), done: st.done || 0, total: st.total || 0, current: st.current, fonte: "terminal" };
}

// ---------- perfil, base, skills, relatório ----------
export function config() {
  return readJson(join(HOME_DIR, "config.json"), {});
}

// Perfil do negócio (módulo A): arkos.engine/perfil.json (ou o .arkos/perfil.json antigo) subindo a partir da pasta,
// depois o da casa, senão o padrão em ~/.arkos/config.json
export function profile(cwd = process.cwd()) {
  let dir = resolve(cwd);
  const casa = process.env.ARKOS_CASA || config().casa;
  const candidatos = [];
  for (let i = 0; i < 8; i++) {
    candidatos.push(join(dir, "arkos.engine", "perfil.json"), join(dir, ".arkos", "perfil.json"));
    const up = dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  if (casa) candidatos.push(join(casa, "arkos.engine", "perfil.json"));
  for (const f of candidatos) {
    if (existsSync(f)) {
      try { return { ...JSON.parse(readFileSync(f, "utf8").replace(/^﻿/, "")), _src: f }; }
      catch { return { _erro: "perfil.json com JSON quebrado", _src: f }; }
    }
  }
  const c = config();
  return c.perfil ? { ...c.perfil, _src: "config" } : null;
}

export function prestador() {
  const c = config();
  if (c.prestador) return c.prestador;
  try { return userInfo().username; } catch { return process.env.USERNAME || "?"; }
}

// Base de conhecimento (MCP arkos-base). Só "conectada" quando há config MCP real apontada.
export function base() {
  const c = config();
  const mcp = c.base && c.base.mcpConfig;
  if (mcp && existsSync(mcp)) return { connected: true, mcpConfig: mcp, label: c.base.label || "arkos-base" };
  return { connected: false, mcpConfig: null, label: "arkos-base" };
}

// Skills que o Claude enxerga: ~/.claude/skills + skills do projeto (.claude/skills)
export function countSkills(cwd = process.cwd()) {
  const dirs = [join(homedir(), ".claude", "skills"), join(cwd, ".claude", "skills")];
  const seen = new Set();
  for (const d of dirs) {
    let list = [];
    try { list = readdirSync(d); } catch { continue; }
    for (const n of list) {
      try { if (existsSync(join(d, n, "SKILL.md"))) seen.add(n); } catch {}
    }
  }
  return seen.size;
}

export const REPORT_DIR = join(ARKOS_ROOT, "engine", "report");
export const REPORT_STATE = join(HOME_DIR, "relatorio.json");

export function reportServer() {
  const r = readJson(REPORT_STATE);
  if (!r || !r.pid) return null;
  try { process.kill(r.pid, 0); return r; } catch { return null; }
}

// ---------- cores ----------
export const C = {
  volt: "\x1b[38;2;198;244;50m",
  white: "\x1b[38;2;242;243;245m",
  mute: "\x1b[38;2;107;114;128m",
  dim: "\x1b[38;2;75;81;96m",
  red: "\x1b[38;2;255;107;107m",
  voltEscuro: "\x1b[38;2;110;138;24m",
  bold: "\x1b[1m",
  reset: "\x1b[0m",
};
export const fg = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  return `\x1b[38;2;${(n >> 16) & 255};${(n >> 8) & 255};${n & 255}m`;
};
export const bg = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  return `\x1b[48;2;${(n >> 16) & 255};${(n >> 8) & 255};${n & 255}m`;
};

// Barra de passos: concluídos em Volt, o passo em andamento em Volt escuro, o resto vazio.
// Com até 8 passos, um bloco por passo; acima disso, proporcional.
export function bar(done, total, width = 4) {
  if (!total) return "";
  const w = total <= 8 ? total : width;
  const feitos = Math.max(0, Math.min(w, Math.floor((done / total) * w)));
  const andando = done < total ? Math.min(w - feitos, Math.max(1, Math.round(((done + 1) / total) * w) - feitos)) : 0;
  return C.volt + "■".repeat(feitos) + C.voltEscuro + "■".repeat(andando) + C.dim + "□".repeat(w - feitos - andando) + C.reset;
}

// Versão lida na hora do package.json (o processo pode estar aberto desde antes de uma atualização).
export function versaoAtual() { return readJson(join(CLI_DIR, "package.json"), PKG).version || VERSION; }


// Plano da chave (engine/REGRAS-ACESSO-E-SIGILO.md): "vip" só com plano vip explícito no payload; sem licença,
// sem campo ou ilegível = "membro" (padrão seguro). Aqui o payload NÃO é conferido (o segredo só existe no
// servidor da base): serve para o sigilo de skill (limite B) e para o sync. Conteúdo da base é filtrado no servidor.
export { planoLocal } from "../src/plano.mjs";
