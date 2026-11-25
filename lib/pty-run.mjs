// Roda o claude num PTY abaixo do cabeçalho fixo da ARKOS (mini-multiplexador com tela virtual).
import { createRequire } from "node:module";
import { appendFileSync } from "node:fs";
import { join } from "node:path";
import { HOME_DIR } from "./core.mjs";
const vistos = new Set();
// log de diagnóstico do rodapé (~/.arkos/rodape-debug.log): cada mensagem uma vez por execução
// menor tamanho que vai para o claude; abaixo disso a moldura segura o último tamanho bom
export const TAMANHO_MIN = { cols: 40, rows: 12 };

export function diag(msg) {
  const chave = msg.replace(/\d+/g, "#");
  if (vistos.has(chave)) return;
  vistos.add(chave);
  try { appendFileSync(join(HOME_DIR, "rodape-debug.log"), `${new Date().toISOString()} ${msg}
`); } catch {}
}
import { makeInputTranslator } from "./mux.mjs";
import { headerLines, alturaDoLogo } from "./banner.mjs";
import { sixel as codificar, rasterRotor, iconeSixel, ladoSixel } from "./sixel.mjs";
import { miniRotor } from "./minirotor.mjs";
const MINI0 = miniRotor(0);
const logos = new Map();
const logoSixel = (h) => { const l = ladoSixel(2 * h, h); if (!logos.has(l)) logos.set(l, codificar(rasterRotor(l, l, 0))); return logos.get(l); };
import { TelaVirtual } from "./tela.mjs";
import { filtrarEntrada } from "./rolagem.mjs";
import { statusInicial } from "../src/status.mjs";
import { StringDecoder } from "node:string_decoder";
import { readFileSync } from "node:fs";

const require = createRequire(import.meta.url);
const ESC = "\x1b";

// corta texto com cores em `max` colunas visíveis (o rodapé nunca quebra linha)
export function cortar(txt, max) {
  let vis = 0, out = "";
  for (let i = 0; i < txt.length; ) {
    const m = /^\x1b\[[0-9;]*m/.exec(txt.slice(i, i + 80)); // SGR com frente+fundo RGB passa de 32
    if (m) { out += m[0]; i += m[0].length; continue; }
    const ch = String.fromCodePoint(txt.codePointAt(i));
    if (vis + 1 > max - 1) break;
    out += ch; vis += 1; i += ch.length;
  }
  return out;
}

// linhas do topo do claude escondidas: o bloco de abertura (mascote, versão, plano, pasta) + 1 vazia
export const EXTRA = 4;

// checar(): Promise com o status vivo; roda no início e a cada `intervalo` ms.
export function runInPty(cmd, args, env, title, { checar, aoStatus, intervalo = 60000, rodape, sixel = false, vivo } = {}) {
  const pty = require("@lydell/node-pty");
  const out = process.stdout;
  let cols = out.columns || 120, rows = out.rows || 40;
  let st = statusInicial();
  let vivoAtual = "";
  let header = headerLines(cols, rows, process.cwd(), st, sixel, vivoAtual);
  let H = header.length;
  const rodapeSixel = sixel && process.env.ARKOS_RODAPE_SIXEL !== "0";
  diag(`rodapé: ${rodapeSixel ? "sixel" : "D"} (sixel=${sixel}, ARKOS_RODAPE_SIXEL=${process.env.ARKOS_RODAPE_SIXEL ?? "-"})`);
  // última linha: rodapé ARKOS fixo. Com Sixel, o rodapé sobe para a penúltima e a última fica vazia:
  // depois da imagem o terminal desce o cursor uma linha, e na última linha isso rola a tela (e a imagem some).
  const R = rodape ? (rodapeSixel ? 2 : 1) : 0;
  const linhaRodape = () => (rodapeSixel ? rows - 1 : rows);
  const visiveis = () => Math.max(5, rows - H - R);
  let ultimoRodape = "";
  const paintRodape = (forcar = false) => {
    if (!rodape) return "";
    let txt = "";
    try { txt = cortar(rodape(tela?.animando || false, cols), cols); } catch { return ""; }
    if (!forcar && txt === ultimoRodape) return "";
    ultimoRodape = txt;
    // Rotor em Sixel no rodapé: as 2 células do mini Rotor ficam em branco e a imagem vai por cima.
    // A região de rolagem (DECSTBM) termina na penúltima linha: o avanço de linha depois da imagem, na última linha
    // (fora da região), não rola a tela. ARKOS_RODAPE_SIXEL=0 volta ao mini Rotor D.
    if (rodapeSixel) {
      const i = txt.indexOf(MINI0);
      if (i === -1) diag("rodapé: mini Rotor não achado no texto, ficou o D");
      if (i !== -1) {
        const col = cortar(txt.slice(0, i), 999).replace(/\[[0-9;]*m/g, "").length + 1;
        txt = txt.slice(0, i) + "  " + txt.slice(i + MINI0.length);
        diag(`rodapé: sixel desenhado na linha ${linhaRodape()} coluna ${col}`);
        return `${ESC}[?2026h${ESC}7${ESC}[${linhaRodape()};1H${ESC}[0m${ESC}[2K${txt}${ESC}[0m${ESC}[${rows};1H${ESC}[2K${ESC}[${linhaRodape()};${col}H${iconeSixel(0)}${ESC}8${ESC}[?2026l`;
      }
    }
    return `${ESC}[?2026h${ESC}7${ESC}[${linhaRodape()};1H${ESC}[0m${ESC}[2K${txt}${ESC}[0m${ESC}8${ESC}[?2026l`;
  };

  const paintHeader = () => {
    let s = `${ESC}[?2026h${ESC}7`;
    header.forEach((l, i) => { s += `${ESC}[${i + 1};1H${ESC}[0m${ESC}[2K${cortar(l, cols + 1)}${ESC}[0m`; });
    const alt = alturaDoLogo(rows);
    if (sixel && H > 2 && alt) s += `${ESC}[1;3H` + logoSixel(alt);
    return s + `${ESC}8${ESC}[?2026l`;
  };

  // ?1000h?1006h: a roda do mouse chega como evento SGR e rola o histórico da moldura (ARKOS_ROLAGEM=0 desliga)
  const rolagem = process.env.ARKOS_ROLAGEM !== "0";
  out.write(`${ESC}]0;${title}\x07${ESC}[?1049h${ESC}[r${ESC}[2J` + (rolagem ? `${ESC}[?1000h${ESC}[?1006h` : ""));
  out.write(paintHeader());

  const child = pty.spawn(cmd, args, {
    name: "xterm-256color", cols, rows: visiveis() + EXTRA, cwd: process.cwd(), env, useConpty: true,
  });
  const tela = new TelaVirtual({ cols, linhas: visiveis(), extra: EXTRA, out, topo: H + 1, aoResponder: (d) => child.write(d), sixel });
  child.onData((d) => tela.escrever(d));
  tela.aoMudarAnimando = () => { const s = paintRodape(); if (s) out.write(s); };

  // mouse e posição do cursor: linha real -> linha do claude (desconta cabeçalho, soma o topo escondido)
  const tIn = makeInputTranslator(() => H - EXTRA);
  const stdin = process.stdin;
  if (stdin.isTTY) stdin.setRawMode(true);
  stdin.resume();
  const utf8 = new StringDecoder("utf8"); // acento e emoji chegam em bytes UTF-8, às vezes partidos
  const aoTeclar = (d) => {
    let s = utf8.write(tIn(d)); // mouse já em linhas do claude: a área visível é EXTRA+1 .. EXTRA+visiveis
    if (s && rolagem) {
      const f = filtrarEntrada(s, { ativo: tela.podeRolar(), claudeMouse: tela.claudeMouse, rolado: tela.rolagem > 0, areaIni: EXTRA + 1, areaFim: EXTRA + visiveis(), pagina: Math.max(1, visiveis() - 2) });
      if (f.rolar || /\[</.test(s)) diag(`rolagem: tela=${tela.term.buffer.active.type} claudeMouse=${tela.claudeMouse} base=${tela.term.buffer.active.baseY} rolar=${f.rolar}`);
      if (f.rolar) tela.rolar(f.rolar);
      if (f.fim) tela.rolar(-Infinity);
      s = f.passar;
    }
    if (s) child.write(s);
  };
  stdin.on("data", aoTeclar);

  const refazerTudo = () => {
    try { child.resize(cols, visiveis() + EXTRA); } catch {}
    tela.redimensionar(cols, visiveis(), H + 1);
    out.write(`${ESC}[2J` + paintHeader() + paintRodape(true));
    tela.desenhar(true);
  };

  // Tamanho minúsculo (aba escondida, painel animando ao sair e voltar) não chega ao claude: ele reescreveria a
  // conversa em colunas estreitas e isso ficaria no histórico. Resizes em sequência viram um só.
  let tResize = null;
  const aplicarTamanho = () => {
    tResize = null;
    const c = out.columns, r = out.rows;
    if (!(c >= TAMANHO_MIN.cols && r >= TAMANHO_MIN.rows)) { diag(`resize ignorado: ${c}x${r}`); return; }
    if (c === cols && r === rows) { out.write(`${ESC}[2J` + paintHeader() + paintRodape(true)); tela.desenhar(true); return; }
    cols = c; rows = r;
    header = headerLines(cols, rows, process.cwd(), st, sixel, vivoAtual);
    H = header.length;
    refazerTudo();
  };
  const aoRedimensionar = () => { clearTimeout(tResize); tResize = setTimeout(aplicarTamanho, 120); };
  out.on("resize", aoRedimensionar);

  let timer;
  const timerRodape = rodape ? setInterval(() => {
    const s = paintRodape(); if (s) out.write(s);
    // status vivo no topo (mesma fonte do rodapé): redesenha só quando muda
    if (vivo) { let v = ""; try { v = vivo(tela.animando); } catch {} if (v !== vivoAtual) { vivoAtual = v; header = headerLines(cols, rows, process.cwd(), st, sixel, vivoAtual); out.write(paintHeader()); } }
  }, 400) : null;
  out.write(paintRodape(true));
  if (checar) {
    const rodar = () => checar().then((s) => {
      st = s; aoStatus?.(s);
      const novo = headerLines(cols, rows, process.cwd(), st, sixel, vivoAtual);
      const mudouAltura = novo.length !== H;
      header = novo; H = novo.length;
      if (mudouAltura) refazerTudo(); else out.write(paintHeader());
    }).catch(() => {});
    rodar();
    timer = setInterval(rodar, intervalo);
  }

  return new Promise((done) => {
    child.onExit(async ({ exitCode }) => {
      clearInterval(timer); clearInterval(timerRodape);
      await new Promise((r) => setTimeout(r, 60)); // deixa a emulação engolir o último pedaço
      tela.parar();
      const retomar = /claude --resume ([0-9a-f-]{36})/.exec(tela.textoCompleto());
      out.off("resize", aoRedimensionar); clearTimeout(tResize);
      stdin.off("data", aoTeclar);
      if (stdin.isTTY) stdin.setRawMode(false);
      stdin.pause();
      // desliga o que o claude possa ter ligado e devolve a tela normal
      out.write(`${ESC}[?1000l${ESC}[?1002l${ESC}[?1003l${ESC}[?1006l${ESC}[?1004l${ESC}[?2004l${ESC}[0m${ESC}[r${ESC}[?25h${ESC}[?1049l`);
      done({ code: exitCode ?? 0, retomar: retomar?.[1] || null });
    });
  });
}
