// Linhas de status VIVAS do cabeçalho: base (MCP arkos-base), perfil, skills e aviso de atualização.
// Cada checagem tem timeout curto e nunca lança: devolve { estado: "ok"|"pendente"|"erro"|"off", texto, motivo }.
import { playbooks } from "./classificador.mjs";
import { readFileSync, existsSync } from "node:fs";
import { statusPacote } from "../lib/skills-pacote.mjs";
import { config, profile, prestador, countSkills, versaoAtual, modules } from "../lib/core.mjs";

const TIMEOUT_MS = 1500;

async function comTimeout(promessa, ms = TIMEOUT_MS) {
  let t;
  const limite = new Promise((_, nao) => { t = setTimeout(() => nao(new Error("tempo esgotado")), ms); });
  try { return await Promise.race([promessa, limite]); } finally { clearTimeout(t); }
}

export const MCP_NOVA = "2026-07-28";
export const MCP_ANTIGA = "2025-06-18";

// corpo JSON-RPC de uma resposta MCP (JSON puro ou SSE com linhas "data: {...}"); null se não der para ler
export async function respostaJsonRpc(r) {
  try {
    const t = await r.text();
    const linhas = /^\s*[{[]/.test(t) ? [t] : t.split(/\r?\n/).filter((l) => l.startsWith("data:")).map((l) => l.slice(5));
    for (const l of linhas) { try { const j = JSON.parse(l); if (j && (j.result || j.error)) return j; } catch {} }
  } catch {}
  return null;
}

// Base: lê a config MCP apontada em ~/.arkos/config.json e sonda o servidor: server/discover (spec 2026-07-28)
// e, se ele não conhecer o método, "initialize" (spec 2025-*).
// módulos da ARKOS: ids distintos em modulos_arkos dos playbooks (hoje 28); sem esse campo, os 14 do terminal
export function modulosArkos() {
  const ids = new Set(playbooks().flatMap((p) => p.modulos_arkos || []));
  return ids.size || modules().length;
}

export async function checarBase() {
  const n = modulosArkos();
  const caminho = config().base?.mcpConfig;
  if (!caminho) return { estado: "off", texto: `base ARKOS não conectada · ${n} módulos · MCP pendente` };
  let srv;
  try {
    const cfg = JSON.parse(readFileSync(caminho, "utf8"));
    srv = cfg.mcpServers?.["arkos-base"] || Object.values(cfg.mcpServers || {})[0];
    if (!srv) throw new Error("sem servidor no arquivo");
  } catch (e) {
    return { estado: "erro", texto: "base ARKOS com erro", motivo: existsSync(caminho) ? "config MCP inválida" : "config MCP não encontrada" };
  }
  if (!srv.url) return { estado: "ok", texto: `base ARKOS configurada · ${n} módulos · MCP local` };
  const headers = { "content-type": "application/json", accept: "application/json, text/event-stream" };
  for (const [k, v] of Object.entries(srv.headers || {})) headers[k] = String(v).replace(/\$\{(\w+)\}/g, (_, e) => process.env[e] || "");
  const t0 = Date.now();
  const post = (body, extra = {}, ms = TIMEOUT_MS) => comTimeout(fetch(srv.url, { method: "POST", headers: { ...headers, ...extra }, body: JSON.stringify(body) }), ms);
  try {
    // spec MCP 2026-07-28: sem initialize/sessão; server/discover anuncia versões e capacidades.
    // Servidor antigo (2025-*) não conhece o método: cai no initialize.
    let r = await post({ jsonrpc: "2.0", id: 1, method: "server/discover", params: { _meta: { protocolVersion: MCP_NOVA } } }, { "mcp-protocol-version": MCP_NOVA });
    if (r.status !== 401 && r.status !== 403 && !(r.ok && (await respostaJsonRpc(r))?.result)) {
      const resta = TIMEOUT_MS * 1.2 - (Date.now() - t0);
      r = await post({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: MCP_ANTIGA, capabilities: {}, clientInfo: { name: "arkos", version: versaoAtual() } } }, {}, Math.max(resta, 300));
    }
    if (r.status === 401 || r.status === 403) return { estado: "erro", texto: "base ARKOS recusou o acesso", motivo: `login inválido (${r.status})` };
    if (!r.ok) return { estado: "erro", texto: "base ARKOS fora do ar", motivo: `HTTP ${r.status}` };
    return { estado: "ok", texto: `base ARKOS conectada · ${n} módulos · MCP seguro` };
  } catch (e) {
    const cod = e.cause?.code || e.cause?.errors?.[0]?.code || "";
    const MOTIVOS = { ECONNREFUSED: "conexão recusada", ENOTFOUND: "endereço não encontrado", ECONNRESET: "conexão caiu", ETIMEDOUT: "sem resposta", CERT_HAS_EXPIRED: "certificado vencido" };
    const motivo = /tempo/.test(String(e.message)) ? "sem resposta em 1,5 s" : MOTIVOS[cod] || cod || "sem conexão";
    return { estado: "erro", texto: "base ARKOS fora do ar", motivo };
  }
}

export function checarPerfil(cwd = process.cwd()) {
  const p = profile(cwd);
  const resto = `prestador ${prestador()} · v${versaoAtual()}`;
  if (!p) return { estado: "off", texto: `perfil nenhum · ${resto}`, nome: null };
  if (p._erro) return { estado: "erro", texto: "perfil com erro", motivo: p._erro };
  return { estado: "ok", texto: `perfil ${p.nome || p.name || "sem nome"} · ${resto}`, nome: p.nome || p.name };
}

export function checarSkills(cwd = process.cwd()) {
  try {
    const p = statusPacote();
    if (p) return p.presentes === p.total
      ? { estado: "ok", texto: `pacote ARKOS v${p.versao}: ${p.presentes}/${p.total} skills` }
      : { estado: "erro", texto: `pacote ARKOS v${p.versao}: incompleto (${p.presentes}/${p.total})${p.sincronizando ? " · sincronizando" : ""}`, motivo: p.sincronizando ? "instalando as que faltam" : "rode arkos skills sync" };
    const n = countSkills(cwd);
    return n > 0 ? { estado: "ok", texto: `pacote de skills ${n} skills · carregadas do ~/.claude` } : { estado: "erro", texto: "pacote de skills vazio", motivo: "nenhuma SKILL.md em ~/.claude/skills" };
  } catch (e) { return { estado: "erro", texto: "pacote de skills ilegível", motivo: String(e.message).slice(0, 40) }; }
}

export function compararVersao(a, b) {
  const pa = String(a).replace(/^v/, "").split(/[.-]/).map((x) => parseInt(x, 10) || 0);
  const pb = String(b).replace(/^v/, "").split(/[.-]/).map((x) => parseInt(x, 10) || 0);
  for (let i = 0; i < 3; i++) if ((pa[i] || 0) !== (pb[i] || 0)) return (pa[i] || 0) > (pb[i] || 0) ? 1 : -1;
  return 0;
}

// Fonte de versão: ~/.arkos/config.json → atualizacao.fonte (arquivo local ou URL com { "versao": "0.2.0" }).
// Falha silenciosa: sem fonte, fonte fora do ar ou JSON ruim = sem aviso.
export async function checarAtualizacao() {
  const fonte = config().atualizacao?.fonte;
  if (!fonte) return null;
  try {
    let txt;
    if (/^https?:\/\//.test(fonte)) {
      const r = await comTimeout(fetch(fonte, { headers: { accept: "application/json" } }));
      if (!r.ok) return null;
      txt = await r.text();
    } else txt = readFileSync(fonte, "utf8");
    const v = JSON.parse(txt.replace(/^﻿/, "")).versao;
    if (v && compararVersao(v, versaoAtual()) > 0) return { estado: "aviso", texto: `nova versão ARKOS v${String(v).replace(/^v/, "")} disponível · arkos update` };
  } catch {}
  return null;
}

export async function statusCompleto(cwd = process.cwd()) {
  const [base, atualizacao] = await Promise.all([checarBase(), checarAtualizacao()]);
  return { base, perfil: checarPerfil(cwd), skills: checarSkills(cwd), atualizacao };
}

// Estado inicial (síncrono) enquanto a checagem da base roda.
export function statusInicial(cwd = process.cwd()) {
  const caminho = config().base?.mcpConfig;
  return {
    base: caminho ? { estado: "pendente", texto: "base ARKOS verificando…" } : { estado: "off", texto: `base ARKOS não conectada · ${modulosArkos()} módulos · MCP pendente` },
    perfil: checarPerfil(cwd), skills: checarSkills(cwd), atualizacao: null,
  };
}
