// Banner do comando `arkos` (item 1 da referência). Linhas de status vivas (src/status.mjs).
import { C, config } from "./core.mjs";
import { miniRotor } from "./minirotor.mjs";
import { rotorLines, proporcaoCelula } from "./rotor.mjs";
import { statusInicial } from "../src/status.mjs";

const m = (s) => C.mute + s + C.reset;
const w = (s) => C.white + s + C.reset;

// "base ARKOS conectada · 14 módulos" -> destaque na palavra de estado, resto apagado
function linhaStatus(s) {
  if (!s) return "";
  if (s.estado === "erro") return `${C.red}● ${s.texto}${C.reset}${s.motivo ? C.red + " · " + s.motivo + C.reset : ""}`;
  if (s.estado === "aviso") return `${C.volt}▲ ${C.reset}${w(s.texto)}`;
  const [cabeca, ...resto] = s.texto.split(" · ");
  const dot = s.estado === "ok" ? C.volt + "●" : s.estado === "pendente" ? C.dim + "◌" : C.dim + "○";
  return `${dot}${C.reset} ${destacar(cabeca)}${resto.length ? " " + m("· " + resto.join(" · ")) : ""}`;
}

function destacar(cabeca) {
  // última(s) palavra(s) de estado em branco: "base ARKOS conectada", "perfil Clínica Lumière", "pacote de skills 187 skills"
  const regras = [/^(base ARKOS )(.+)$/, /^(perfil )(.+)$/, /^(pacote de skills )(.+)$/, /^(pacote ARKOS v[\d.]+: )(.+)$/];
  for (const r of regras) { const x = r.exec(cabeca); if (x) return C.white + x[1] + C.bold + x[2] + C.reset; }
  return w(cabeca);
}

// alturaLogo: 10 (janela alta) ou 8/6 (janela baixa). O layout é sempre o completo; só a arte encolhe.
export function bannerLines(cwd = process.cwd(), st = statusInicial(cwd), alturaLogo = 10, sixel = false, vivo = "") {
  // com Sixel o logo de verdade é desenhado por cima de um bloco vazio de 2H colunas (célula virtual 10×20 do WT)
  const logo = sixel ? Array(alturaLogo).fill(" ".repeat(2 * alturaLogo)) : rotorLines(alturaLogo, proporcaoCelula(process.env, config()));
  const largura = logo.length ? visivel(logo[0]) : 0;
  const status = [linhaStatus(st.base), linhaStatus(st.perfil), linhaStatus(st.skills), ...(st.atualizacao ? [linhaStatus(st.atualizacao)] : [])];
  const casa = process.env.ARKOS_CASA || config().casa;
  if (casa) status.push(`${C.volt}⌂${C.reset} ${w(casa)}`);
  const dica = `${m("digite ")}${w("/arkos")}${m(" para módulos · ")}${w("/relatorio")}${m(" abre o site local")}`;
  const titulo = C.bold + w("A R K O S   E N G I N E") + (vivo ? "   " + vivo : ""), sub = m("Advanced Resource & Knowledge Orchestration System");
  // com folga: linhas vazias entre os blocos; apertado: sem elas
  let right = ["", titulo, sub, "", ...status, dica, ""];
  if (right.length > alturaLogo) right = [titulo, sub, "", ...status, dica];
  if (right.length > alturaLogo) right = [titulo, sub, ...status, dica];
  if (right.length > alturaLogo) right = [titulo, ...status, dica];
  const pad = Math.max(0, Math.floor((alturaLogo - right.length) / 2));
  right = [...Array(pad).fill(""), ...right];
  const n = Math.max(alturaLogo, right.length);
  return Array.from({ length: n }, (_, i) => `  ${logo[i] || " ".repeat(largura)}    ${right[i] || ""}`);
}

const visivel = (s) => s.replace(/\[[0-9;]*m/g, "").length;

// Cabeçalho fixo do topo (modo PTY): sempre o layout completo (logo + status em lista + régua).
// A arte encolhe em janela baixa; só abaixo de 20 linhas ou 60 colunas vira a linha compacta.
export const alturaDoLogo = (rows) => (rows >= 34 ? 10 : rows >= 26 ? 8 : rows >= 20 ? 6 : 0);
export function headerLines(cols, rows, cwd = process.cwd(), st = statusInicial(cwd), sixel = false, vivo = "") {
  const rule = C.dim + "─".repeat(Math.max(10, cols - 4)) + C.reset;
  const altura = rows >= 34 ? 10 : rows >= 26 ? 8 : rows >= 20 ? 6 : 0;
  if (altura && cols >= 60) return [...bannerLines(cwd, st, altura, sixel, vivo), "  " + rule];
  const base = st.base.estado === "ok" ? C.volt + "● base online" : st.base.estado === "erro" ? C.red + "● base: " + (st.base.motivo || "erro") : C.dim + "○ base não conectada";
  const perfil = st.perfil.estado === "erro" ? C.red + "perfil com erro" : C.mute + (st.perfil.nome ? "perfil " + st.perfil.nome : "sem perfil");
  const upd = st.atualizacao ? `  ${C.volt}▲${C.reset} ${m(st.atualizacao.texto)}` : "";
  const line = `  ${miniRotor(0)} ${C.bold}${C.white}A R K O S   E N G I N E${C.reset}  ${vivo ? vivo + "  " : ""}${base}${C.reset} ${m("·")} ${perfil}${C.reset} ${m("· /arkos /relatorio")}${upd}${process.env.ARKOS_CASA ? `  ${C.volt}⌂${C.reset} ${m(process.env.ARKOS_CASA)}` : ""}`;
  return [line, "  " + rule];
}
