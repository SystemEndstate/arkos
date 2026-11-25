// statusLine da ARKOS (item 7):
// ▚ ARKOS │ módulo › playbook │ ● base │ passo N/M ■■□ │ ctx % │ relatório :porta
import { miniRotor } from "./lib/minirotor.mjs";
import { C, loadState, saveState, base, bar, reportServer, progresso } from "./lib/core.mjs";

export function ctxPercent(input) {
  const cw = input.context_window;
  if (!cw) return null;
  if (typeof cw.used_percentage === "number") return Math.round(cw.used_percentage);
  const u = cw.current_usage;
  const size = cw.context_window_size;
  if (u && size) {
    const used = (u.input_tokens || 0) + (u.cache_creation_input_tokens || 0) + (u.cache_read_input_tokens || 0);
    return Math.round((used / size) * 100);
  }
  return null;
}

// Status vivo do topo (mesma fonte do rodapé): módulo · estado · base · ctx.
// animando = turno do Claude rodando (spinner na tela da moldura).
// estado ao vivo (só no rodapé da moldura, que sabe se o turno está rodando)
export function estadoVivo(st, animando = false) {
  const pg = progresso(st);
  const falha = st.lastFailure && Date.now() - Date.parse(st.lastFailure.at) < 60000;
  const passo = pg.total ? ` passo ${Math.min(pg.done + (pg.done >= pg.total ? 0 : 1), pg.total)}/${pg.total}` : "";
  return falha ? `${C.red}falha${passo}${C.reset}`
    : pg.bloqueada ? `${C.red}bloqueada${passo}${C.reset}`
    : animando ? `${C.volt}executando${passo}…${C.reset}`
    : pg.total && pg.done >= pg.total ? `${C.volt}concluído${C.reset}`
    : `${C.mute}aguardando comando${C.reset}`;
}

const visivel = (s) => [...s.replace(/\[[0-9;]*m/g, "")].length;

// opts: { vivo: animando (true/false) = mostra o estado ao vivo; cols = largura para encaixar por prioridade }
export function render(input, st = loadState(input.session_id), b = base(), rep = reportServer(), icone = true, opts = {}) {
  const sep = ` ${C.dim}│${C.reset} `;
  // ícone só no rodapé da moldura (que troca pelo Sixel); a statusLine fora dela fica só com ARKOS
  const ic = !icone ? "" : process.env.ARKOS_LOGO === "texto" ? `${C.volt}◆${C.reset} ` : `${miniRotor(0)} `;
  // [texto, prioridade]: em terminal estreito some primeiro a menor prioridade; ARKOS nunca some
  const parts = [[`${ic}${C.volt}ARKOS${C.reset}`, 99]];
  if (opts.vivo !== undefined) parts.push([estadoVivo(st, opts.vivo), 50]);

  if (st.module) parts.push([`${C.white}${st.moduleShort} › ${st.playbook}${C.reset}`, 40]);
  else parts.push([`${C.mute}sem módulo${C.reset}`, 40]);

  // base: status vivo checado pelo `arkos` (st.baseStatus); sem ele, só a config
  const bs = st.baseStatus || (b.connected ? { estado: "ok" } : { estado: "off" });
  parts.push([bs.estado === "ok"
    ? `${C.volt}●${C.reset} ${C.mute}base online${C.reset}`
    : bs.estado === "erro"
      ? `${C.red}● base: ${bs.motivo || "erro"}${C.reset}`
      : bs.estado === "pendente"
        ? `${C.dim}◌${C.reset} ${C.mute}base verificando${C.reset}`
        : `${C.dim}○${C.reset} ${C.mute}base não conectada${C.reset}`, 20]);

  const pg = progresso(st);
  if (pg.total) {
    const n = Math.min(pg.done + (pg.done >= pg.total ? 0 : 1), pg.total);
    let p = `${C.white}passo ${n}/${pg.total}${C.reset} ${bar(pg.done, pg.total)}`;
    if (pg.bloqueada) p += ` ${C.red}bloqueada${C.reset}`;
    if (/^cancelad/i.test(pg.saida || "")) p += ` ${C.red}cancelado${C.reset}`;
    if (pg.proximo) p += ` ${C.mute}› próximo:${C.reset} ${C.volt}${pg.proximo}${C.reset}`;
    parts.push([p, 30]);
  } else parts.push([`${C.dim}passo —/—${C.reset}`, 30]);

  const pct = ctxPercent(input) ?? st.ctx ?? null;
  parts.push([pct != null ? `${C.mute}ctx ${pct}%${C.reset}` : `${C.dim}ctx —${C.reset}`, 60]);

  if (rep) parts.push([`${C.mute}relatório${C.reset} ${C.white}:${rep.port}${C.reset}`, 10]);

  let vivas = parts;
  const linha = () => " " + vivas.map((p) => p[0]).join(sep);
  if (opts.cols) while (visivel(linha()) > opts.cols - 1 && vivas.length > 1) {
    const menor = Math.min(...vivas.map((p) => p[1]));
    vivas = vivas.filter((p) => p[1] !== menor);
  }
  return linha();
}

if (import.meta.url === `file:///${(process.argv[1] || "").replace(/\\/g, "/")}` || process.argv[1]?.endsWith("statusline.mjs")) {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  let input = {};
  try { input = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}"); } catch {}
  if (process.env.ARKOS_RODAPE_FIXO === "1") {
    // modo moldura: o rodapé é desenhado pelo `arkos` na última linha (sempre visível, mesmo com menus);
    // aqui só guardamos o uso de contexto que o Claude Code informa
    const st = loadState(input.session_id);
    const pct = ctxPercent(input);
    if (pct != null && st.ctx !== pct) { st.ctx = pct; saveState(input.session_id, st); }
    process.stdout.write("");
  } else process.stdout.write(render(input, undefined, undefined, undefined, false));
}
