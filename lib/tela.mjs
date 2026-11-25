// Tela virtual do mini-multiplexador: a saída do claude vai para um terminal emulado (@xterm/headless)
// e só as linhas visíveis são desenhadas abaixo do cabeçalho, com diff por linha.
// Assim dá para recortar as primeiras linhas do claude (o bloco mascote/versão/plano/pasta).
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const ESC = "\x1b";

// modos que o terminal de verdade precisa ligar para o claude receber mouse, colagem e foco
const MODOS = new Set(["1000", "1002", "1003", "1004", "1005", "1006", "1015", "2004"]);

export function sgrDaCelula(c) {
  const p = ["0"];
  if (c.isBold()) p.push("1");
  if (c.isDim()) p.push("2");
  if (c.isItalic()) p.push("3");
  if (c.isUnderline()) p.push("4");
  if (c.isBlink()) p.push("5");
  if (c.isInverse()) p.push("7");
  if (c.isInvisible()) p.push("8");
  if (c.isStrikethrough()) p.push("9");
  if (c.isFgRGB()) { const v = c.getFgColor(); p.push(`38;2;${(v >> 16) & 255};${(v >> 8) & 255};${v & 255}`); }
  else if (c.isFgPalette()) p.push(`38;5;${c.getFgColor()}`);
  if (c.isBgRGB()) { const v = c.getBgColor(); p.push(`48;2;${(v >> 16) & 255};${(v >> 8) & 255};${v & 255}`); }
  else if (c.isBgPalette()) p.push(`48;5;${c.getBgColor()}`);
  return `${ESC}[${p.join(";")}m`;
}

// troca: { [coluna]: { ch, sgr? } } — mesmo número de colunas, o cursor não anda
export function linhaComCores(line, cols, troca = null) {
  if (!line) return "";
  let s = "", ultimo = "", cel;
  for (let x = 0; x < cols; x++) {
    cel = line.getCell(x, cel);
    if (!cel) break;
    const w = cel.getWidth();
    if (w === 0) continue; // segunda metade de caractere largo
    const t = troca && troca[x];
    const sgr = (t && t.sgr) || sgrDaCelula(cel);
    if (sgr !== ultimo) { s += sgr; ultimo = sgr; }
    s += t ? t.ch : cel.getChars() || " ";
  }
  return s + `${ESC}[0m`;
}

// ---------- marca ARKOS sobre a saída do Claude ----------
// glifos do spinner do Claude Code (1 coluna) e o Rotor girando no lugar deles
const SPIN = new Set(["·", "✢", "✳", "✶", "✻", "✽", "*", "✺", "✹", "✸", "✷"]);
import { quadroMini, sgrDe } from "./minirotor.mjs";
import { iconeSixel } from "./sixel.mjs";
import { LINHAS_HISTORICO, polegar } from "./rolagem.mjs";
const TRILHO = `${ESC}[0;38;2;70;74;80m`, AVISO = `${ESC}[0;1;38;2;10;11;13;48;2;198;244;50m`;
const VOLT = `${ESC}[0;1;38;2;198;244;50m`;
// mesmo comprimento por trecho, para cada pedaço manter a cor original da célula
const TROCAS_TEXTO = [["? for shortcuts", "? para atalhos "], ["auto mode on", "auto ativado"], ["(shift+tab to cycle)", "(shift+tab alterna) "], ["esc to interrupt", "esc interrompe  "]];
const mini = (q, x) => Object.fromEntries(quadroMini(q).map((c, i) => [x + i, { ch: c.ch, sgr: sgrDe(c) }]));

function celulas(line, cols) {
  const a = []; let cel;
  for (let x = 0; x < cols; x++) { cel = line.getCell(x, cel); if (!cel) break; a.push(cel.getWidth() === 0 ? "" : cel.getChars() || " "); }
  return a;
}

// devolve { troca, animado } para a linha: spinner -> Rotor (girando se o turno está rodando), textos em português
export function marcarLinha(line, cols, quadro, sixel = false) {
  if (!line) return null;
  const cs = celulas(line, cols);
  let troca = null, animado = false;
  const icones = []; // posições do Rotor: com Sixel, as 2 células ficam em branco e a imagem vai por cima
  const icone = (q, x) => { icones.push({ x, q }); return sixel ? { [x]: { ch: " " }, [x + 1]: { ch: " " } } : mini(q, x); };
  let x0 = 0; while (x0 < cs.length && cs[x0] === " ") x0++;
  if (x0 < 4 && SPIN.has(cs[x0]) && cs[x0 + 1] === " " && /\p{L}/u.test((cs[x0 + 2] === " " ? cs[x0 + 3] : cs[x0 + 2]) || "")) {
    const resto = cs.slice(x0 + 2).join("");
    animado = /…|\.\.\./.test(resto) || /esc to interrupt|para interromper/.test(resto);
    troca = icone(animado ? quadro : 0, x0); // glifo + espaço -> Rotor de 2 colunas
  }
  // marcador "▚▞" (hooks, mod, rodapé fora da moldura) -> Rotor parado
  for (let x = 0; x < cs.length - 1; x++) if (cs[x] === "▚" && cs[x + 1] === "▞") troca = { ...(troca || {}), ...icone(0, x) };
  const txt = cs.join("");
  for (const [de, para] of TROCAS_TEXTO) {
    const i = txt.indexOf(de);
    if (i === -1) continue;
    // índice no texto = coluna (sem caractere largo antes) — confere pela junção das células
    if (cs.slice(0, i).join("").length !== i) continue;
    troca ||= {};
    for (let k = 0; k < para.length; k++) troca[i + k] = { ch: para[k] };
  }
  return troca ? { troca, animado, icones } : null;
}

// Linhas do topo que são o bloco de abertura do claude (mascote, versão, plano, pasta) + linha vazia.
export function linhasDoBlocoClaude(textos) {
  const i = textos.findIndex((t) => /Claude Code v\d/.test(t));
  if (i === -1 || i > 3) return 0;
  let fim = i;
  while (fim + 1 < textos.length && fim < i + 3 && textos[fim + 1].trim() !== "" && !/^\s*[❯>]/.test(textos[fim + 1])) fim++;
  while (fim + 1 < textos.length && textos[fim + 1].trim() === "" && fim < i + 5) fim++;
  return fim + 1;
}

// Blocos de abertura do Claude Code (mascote + "Claude Code vX" + modelo/plano + pasta + linhas vazias)
// em qualquer ponto do texto: o histórico da moldura não mostra (o Claude redesenha depois de /clear, /compact, resize).
// textos: linhas do buffer; devolve o conjunto de índices a esconder.
const MASCOTE = /[▐▛▜▌▝▘▗▖█▀▄]/;
export function blocosDeAbertura(textos) {
  const fora = new Set();
  for (let i = 0; i < textos.length; i++) {
    const t = textos[i];
    if (!/Claude Code v\d/.test(t)) continue;
    let ini = i, fim = i;
    if (/╭/.test(t)) { // caixa (versões antigas / janela estreita): até a linha com ╰
      while (fim + 1 < textos.length && fim < i + 20 && !/╰/.test(textos[fim])) fim++;
    } else {
      while (ini > 0 && ini > i - 2 && textos[ini - 1].trim() && MASCOTE.test(textos[ini - 1])) ini--;
      while (fim + 1 < textos.length && fim < i + 3 && textos[fim + 1].trim() && !/^\s*[❯>]/.test(textos[fim + 1])) fim++;
    }
    while (fim + 1 < textos.length && fim < i + 24 && !textos[fim + 1].trim()) fim++;
    for (let k = ini; k <= fim; k++) fora.add(k);
    i = fim;
  }
  return fora;
}

export class TelaVirtual {
  constructor({ cols, linhas, extra, out, topo, aoResponder, sixel = false, janelaAjuste = 700 }) {
    this.sixel = sixel;
    // depois de redimensionar, o ConPTY repinta a tela com quebras de linha a mais: o que sobe para o histórico
    // nessa janela é cópia da tela e fica escondido (senão a conversa aparece repetida ao rolar)
    this.janelaAjuste = janelaAjuste;
    this.ocultos = []; // [{ ini, fim }] marcadores do xterm: sobrevivem ao corte do histórico e ao reflow
    this.ajuste = null;
    const { Terminal } = require("@xterm/headless");
    this.extra = extra; // linhas a mais no claude, que ficam escondidas no topo
    this.out = out;
    this.topo = topo; // primeira linha (1-based) do terminal real abaixo do cabeçalho
    this.cols = cols;
    this.linhas = linhas; // linhas visíveis
    this.term = new Terminal({ cols, rows: linhas + extra, scrollback: LINHAS_HISTORICO, allowProposedApi: true });
    this.term.onData((d) => aoResponder(d)); // respostas a DA/CPR vão de volta ao claude
    this.cache = [];
    this.pendente = false;
    this.corte = extra;
    this.quadro = 0;
    this.rolagem = 0; // linhas acima do fim (0 = acompanhando a conversa)
    this.novas = false;
    this.ultTotal = 0;
    this.claudeMouse = false;
    // Rotor girando: enquanto houver spinner ativo na tela, redesenha a cada 120 ms (só a linha muda)
    this.giro = setInterval(() => { if (this.animando && !this.parado) { this.quadro++; this.desenhar(); } }, 120);
    this.giro.unref?.();
  }

  // escreve a saída do claude; repassa ao terminal real só os modos de mouse/colagem/foco
  escrever(dados) {
    const re = /\x1b\[\?([\d;]+)([hl])/g;
    let m, modos = "";
    while ((m = re.exec(dados))) {
      const todos = m[1].split(";");
      if (todos.some((x) => x === "1000" || x === "1002" || x === "1003")) this.claudeMouse = m[2] === "h";
      // 1000/1006 ficam sempre ligados pela moldura (roda do histórico): o Claude desligar não desliga
      const ps = todos.filter((x) => MODOS.has(x) && !(m[2] === "l" && (x === "1000" || x === "1006")));
      if (ps.length) modos += `${ESC}[?${ps.join(";")}${m[2]}`;
    }
    if (modos) this.out.write(modos);
    this.term.write(dados, () => {
      const b = this.term.buffer.active;
      if (b.type !== "normal") this.rolagem = 0;
      else if (this.rolagem > 0) {
        // saída nova enquanto rolado: a vista fica parada no mesmo trecho e aparece o aviso
        const n = this.listaHistorico().length;
        const d = n - this.ultTotal;
        if (d > 0) { this.rolagem += d; this.novas = true; }
        this.rolagem = Math.min(this.rolagem, Math.max(0, n - this.linhas));
        this.ultTotal = n;
      }
      this.agendar();
    });
  }

  // índices absolutos mostrados ao rolar: histórico sem os blocos de abertura + a janela ao vivo
  listaHistorico() {
    const b = this.term.buffer.active;
    const vivoIni = b.baseY + this.extra;
    const textos = [];
    for (let y = 0; y < vivoIni; y++) textos.push(b.getLine(y)?.translateToString(true) || "");
    const fora = blocosDeAbertura(textos);
    // cópias da tela que o ConPTY empurrou para o histórico ao redimensionar
    const faixas = this.ocultos.map(({ ini, fim }) => [ini.isDisposed ? 0 : ini.line, fim.isDisposed ? -1 : fim.line]);
    if (this.ajuste) faixas.push([this.ajuste.ini.isDisposed ? 0 : this.ajuste.ini.line, vivoIni]);
    for (const [a, z] of faixas) for (let y = Math.max(0, a); y < Math.min(z, vivoIni); y++) fora.add(y);
    const lista = [];
    for (let y = 0; y < vivoIni; y++) if (!fora.has(y)) lista.push(y);
    for (let y = 0; y < this.linhas; y++) lista.push(vivoIni + y);
    return lista;
  }

  podeRolar() { return this.term.buffer.active.type === "normal"; }

  // n > 0 sobe; Infinity/-Infinity vão ao topo/fim
  rolar(n) {
    const b = this.term.buffer.active;
    if (b.type !== "normal") return;
    const antes = this.rolagem;
    const total = this.listaHistorico().length;
    this.ultTotal = total;
    this.rolagem = Math.max(0, Math.min(this.rolagem + n, total - this.linhas));
    if (this.rolagem === 0) this.novas = false;
    if (this.rolagem !== antes) this.desenhar();
  }

  parar() { this.parado = true; clearInterval(this.giro); }

  // texto de todas as linhas do claude (para achar o "claude --resume <id>" que ele imprime ao sair)
  textoCompleto() {
    const b = this.term.buffer.active, a = [];
    for (let y = 0; y < this.linhas + this.extra; y++) a.push(b.getLine(b.viewportY + y)?.translateToString(true) || "");
    return a.join(" ");
  }

  agendar() {
    if (this.pendente || this.parado) return;
    this.pendente = true;
    setTimeout(() => { this.pendente = false; if (!this.parado) this.desenhar(); }, 12);
  }

  // O claude tem `extra` linhas a mais que a área visível; as `extra` do topo ficam sempre escondidas.
  // Em tela cheia o claude desenha o bloco de abertura (mascote, versão, plano, pasta) justamente nelas.
  calcularCorte() { return this.extra; }

  desenhar(tudo = false) {
    const b = this.term.buffer.active;
    this.corte = this.calcularCorte();
    let s = `${ESC}[?2026h${ESC}[?25l`;
    let animando = false;
    const redesenhadas = new Set(), icones = [];
    const rol = b.type === "normal" ? this.rolagem : 0;
    // rolado: linhas do histórico filtrado (sem o bloco de abertura do Claude); ao vivo: a janela de sempre
    const lista = rol > 0 ? this.listaHistorico() : null;
    const inicio = lista ? lista.length - this.linhas - rol : 0;
    const idx = (y) => (lista ? lista[inicio + y] : b.baseY + this.corte + y);
    // barra de rolagem na última coluna, só enquanto rolado
    const barra = lista ? polegar(this.linhas, lista.length, rol) : null;
    const aviso = this.novas && rol > 0 ? " ↓ novas mensagens · End volta " : "";
    for (let y = 0; y < this.linhas; y++) {
      const linha = idx(y) === undefined ? null : b.getLine(idx(y));
      let mk = marcarLinha(linha, this.cols, this.quadro, this.sixel);
      if (barra) {
        const t = { ...(mk?.troca || {}) };
        const noPolegar = y >= barra.inicio && y < barra.inicio + barra.tamanho;
        t[this.cols - 1] = noPolegar ? { ch: "┃", sgr: VOLT } : { ch: "│", sgr: TRILHO };
        if (aviso && y === this.linhas - 1) { const x0 = Math.max(0, this.cols - 2 - aviso.length); for (let k = 0; k < aviso.length; k++) t[x0 + k] = { ch: aviso[k], sgr: AVISO }; }
        mk = { troca: t, animado: mk?.animado || false, icones: mk?.icones || [] };
      }
      if (mk?.animado) animando = true;
      if (this.sixel && mk?.icones.length) for (const ic of mk.icones) icones.push({ ...ic, y, animado: mk.animado });
      const l = linhaComCores(linha, this.cols, mk?.troca);
      if (tudo || this.cache[y] !== l) {
        s += `${ESC}[${this.topo + y};1H${ESC}[0m${ESC}[2K${l}`;
        this.cache[y] = l;
        redesenhadas.add(y);
      }
    }
    // Sixel por cima das células em branco: na linha redesenhada (o texto apagou a imagem) e no spinner a cada quadro
    for (const ic of icones) if (tudo || redesenhadas.has(ic.y) || ic.animado) s += `${ESC}[${this.topo + ic.y};${ic.x + 1}H` + iconeSixel(ic.q);
    const cy = rol > 0 ? -1 : b.cursorY - this.corte;
    const escondido = this.term._core?.coreService?.isCursorHidden;
    if (cy >= 0 && cy < this.linhas) {
      s += `${ESC}[${this.topo + cy};${b.cursorX + 1}H`;
      if (!escondido) s += `${ESC}[?25h`;
    }
    s += `${ESC}[?2026l`;
    const mudou = this.animando !== animando;
    this.animando = animando;
    this.out.write(s);
    if (mudou) this.aoMudarAnimando?.(animando); // rodapé muda na hora: executando… / aguardando comando
  }

  redimensionar(cols, linhas, topo) {
    this.cols = cols; this.linhas = linhas; this.topo = topo;
    const b = this.term.buffer.active;
    // marca o topo da tela de agora (antes do reflow): dele para baixo, o que subir na janela de ajuste é repintura
    if (b.type === "normal" && !this.ajuste) {
      const ini = this.term.registerMarker(-b.cursorY);
      if (ini) this.ajuste = { ini };
    }
    this.term.resize(cols, linhas + this.extra);
    this.cache = [];
    if (!this.ajuste) return;
    clearTimeout(this.fimAjuste); // resizes em sequência (animação, arrastar a borda) viram uma janela só
    this.fimAjuste = setTimeout(() => this.fecharAjuste(), this.janelaAjuste);
    this.fimAjuste.unref?.();
  }

  // fim da janela: a faixa escondida vai do topo marcado até o topo da tela de agora (escrita já processada)
  fecharAjuste() {
    const aj = this.ajuste;
    if (!aj) return;
    this.term.write("", () => {
      const b = this.term.buffer.active;
      const fim = b.type === "normal" ? this.term.registerMarker(-b.cursorY) : null;
      if (fim && !aj.ini.isDisposed && fim.line > aj.ini.line) this.ocultos.push({ ini: aj.ini, fim });
      else { aj.ini.dispose(); fim?.dispose(); }
      this.ocultos = this.ocultos.filter((o) => !o.fim.isDisposed); // faixa que já saiu do histórico
      if (this.ocultos.length > 200) this.ocultos.splice(0, this.ocultos.length - 200);
      this.ajuste = null;
      if (!this.parado) this.desenhar();
    });
  }
}
