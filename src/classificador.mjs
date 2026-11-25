// Classificador de módulo da ARKOS: pontuação por palavras-chave (pt-BR + en) sobre data/modulos.json,
// e escolha de playbook em data/playbooks.json. Determinístico, sem rede; depois pode passar ao Jev.
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { planoLocal, TEMA_VIP } from "./plano.mjs";

const DATA = join(dirname(fileURLToPath(import.meta.url)), "..", "data");
const load = (f) => JSON.parse(readFileSync(f.includes("/") || f.includes("\\") ? f : join(DATA, f), "utf8").replace(/^﻿/, ""));

export const FORTE = 3;
export const FRACO = 1;

// catálogo pelo plano da chave: playbooks-<plano>.json (o do VIP pode vir do pacote baixado da base); sem eles, playbooks.json
let plano = null;
export const planoAtual = () => (plano ??= planoLocal());
export function usarPlano(p) { plano = p === "vip" ? "vip" : "membro"; cache = null; return plano; }
const arqPlaybooks = () => {
  const nome = `playbooks-${planoAtual()}.json`;
  const doPacote = join(process.env.ARKOS_HOME || join(homedir(), ".arkos"), "pacote-vip", "data", nome);
  if (planoAtual() === "vip" && !existsSync(join(DATA, nome)) && existsSync(doPacote)) return doPacote;
  return existsSync(join(DATA, nome)) ? nome : "playbooks.json";
};

let cache;
function dados() {
  if (!cache) {
    const { modulos } = load("modulos.json");
    const { playbooks, esteiras = [] } = load(arqPlaybooks());
    for (const m of modulos) {
      m.termos = [...(m.pt || []), ...(m.en || [])].map((raw) => {
        const forte = raw.startsWith("!");
        return { termo: dobrar(forte ? raw.slice(1) : raw), peso: forte ? FORTE : FRACO };
      });
    }
    cache = { modulos, playbooks, esteiras };
  }
  return cache;
}

export const modulos = () => dados().modulos;
export const playbooks = () => dados().playbooks;
export const esteiras = () => dados().esteiras || [];

// Elos vizinhos de um playbook nas esteiras (schema v0.3 da Harpa).
export function proximosElos(id) {
  const r = [];
  for (const e of esteiras()) e.elos.forEach((l, i) => { if (l.playbook === id && e.elos[i + 1]) r.push(e.elos[i + 1].playbook); });
  return [...new Set(r)];
}
export function anterioresElos(id) {
  const r = [];
  for (const e of esteiras()) e.elos.forEach((l, i) => { if (l.playbook === id && i > 0) r.push(e.elos[i - 1].playbook); });
  return [...new Set(r)];
}

export function dobrar(s) {
  return String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

// Casa palavra inteira (com plural simples) para termos de uma palavra; frase por substring.
export function casa(texto, termo) {
  const esc = termo.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  if (termo.includes(" ")) return new RegExp(`(^|[^a-z0-9])${esc}`).test(texto);
  return new RegExp(`(^|[^a-z0-9])${esc}(s|es)?($|[^a-z0-9])`).test(texto);
}

export function pontuar(texto) {
  const t = dobrar(texto);
  return modulos().map((m) => {
    let pontos = 0;
    const achados = [];
    for (const { termo, peso } of m.termos) {
      if (achados.some((a) => a.startsWith(termo) || termo.startsWith(a))) continue; // angulo/angulos uma vez
      if (casa(t, termo)) { pontos += peso; achados.push(termo); }
    }
    return { modulo: m, pontos, achados };
  }).filter((x) => x.pontos > 0).sort((a, b) => b.pontos - a.pontos);
}

export function escolherPlaybook(principal, secundario, texto) {
  const t = dobrar(texto);
  const daqui = playbooks().filter((p) => p.modulos.includes(principal.id));
  // vence o gatilho mais longo que casar ("auditar a conta" > "meta ads")
  let porGatilho = null, maior = 0;
  for (const p of daqui) for (const g of p.gatilhos || []) if (g.length > maior && casa(t, dobrar(g))) { porGatilho = p; maior = g.length; }
  if (porGatilho) return porGatilho;
  if (secundario) {
    const ambos = daqui.find((p) => p.modulos.includes(secundario.id));
    if (ambos) return ambos;
  }
  return daqui[0] || null;
}

// { principal, secundario|null, playbook, pontos } ou null quando nada casa.
// Sem módulo pelas palavras-chave: procura o pedido nos gatilhos de todos os playbooks.
export function porGatilho(texto) {
  const t = dobrar(texto);
  const p = playbooks().find((pb) => (pb.gatilhos || []).some((g) => g.length >= 4 && casa(t, dobrar(g))));
  if (!p) return null;
  const principal = modulos().find((m) => m.id === p.modulos[0]);
  return principal ? { principal, secundario: null, playbook: p, rotulo: principal.nome, pontos: [], fonte: "gatilho" } : null;
}

export function classificar(texto) {
  // membro pedindo área do plano VIP: não roteia (o hook responde "Isso faz parte do plano VIP.")
  if (planoAtual() !== "vip" && TEMA_VIP.test(dobrar(texto))) return { vip: true, playbook: null, rotulo: "plano VIP", pontos: [] };
  const r = pontuar(texto);
  if (!r.length) return porGatilho(texto);
  const [a, b] = r;
  const secundario = b && b.pontos >= FORTE && b.pontos * 2 >= a.pontos ? b.modulo : null;
  const playbook = escolherPlaybook(a.modulo, secundario, texto);
  return {
    principal: a.modulo,
    secundario,
    playbook,
    rotulo: secundario ? `${a.modulo.nome} + ${secundario.nome}` : a.modulo.nome,
    pontos: r.map((x) => [x.modulo.id, x.pontos]),
  };
}
