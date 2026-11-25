// Mini-multiplexador da ARKOS: roda o `claude` num PTY (ConPTY no Windows) com H linhas a menos
// e mantém o cabeçalho da ARKOS fixo no topo. Em vez de emular a tela inteira, traduz a saída:
// toda posição absoluta de linha ganha +H, a região de rolagem fica presa abaixo do cabeçalho e
// as respostas do terminal (posição do cursor, mouse) perdem H no caminho de volta.

const ESC = "\x1b";

// ---------- saída do claude -> terminal ----------
export function makeOutputTranslator(getH, getRows, onRedrawNeeded) {
  let pending = "";
  return function translate(chunk) {
    let s = pending + chunk;
    pending = "";
    let out = "";
    let i = 0;
    while (i < s.length) {
      const esc = s.indexOf(ESC, i);
      if (esc === -1) { out += s.slice(i); break; }
      out += s.slice(i, esc);
      // sequência incompleta no fim do pedaço: guarda para o próximo
      const seqEnd = scanSeq(s, esc);
      if (seqEnd === -1) { pending = s.slice(esc); break; }
      out += rewrite(s.slice(esc, seqEnd), getH(), getRows(), onRedrawNeeded);
      i = seqEnd;
    }
    return out;
  };
}

// Devolve o índice logo após a sequência que começa em s[i] (ESC), ou -1 se estiver incompleta.
export function scanSeq(s, i) {
  if (i + 1 >= s.length) return -1;
  const c = s[i + 1];
  if (c === "[") {
    for (let j = i + 2; j < s.length; j++) {
      const code = s.charCodeAt(j);
      if (code >= 0x40 && code <= 0x7e) return j + 1;
    }
    return -1;
  }
  if (c === "]" || c === "P" || c === "_" || c === "^") { // OSC/DCS/APC/PM até BEL ou ST
    for (let j = i + 2; j < s.length; j++) {
      if (s[j] === "\x07") return j + 1;
      if (s[j] === ESC) { if (j + 1 >= s.length) return -1; if (s[j + 1] === "\\") return j + 2; }
    }
    return -1;
  }
  if (c === "(" || c === ")" || c === "#" || c === "%") return i + 3 <= s.length ? i + 3 : -1;
  return i + 2;
}

function rewrite(seq, H, rows, redraw) {
  if (seq[1] !== "[") {
    // OSC 0/2 (título): a ARKOS manda no título da aba
    if (/^\x1b\][012];/.test(seq)) return "";
    if (seq === "\x1bc") { redraw(); return `${ESC}[${H + 1};${rows}r${ESC}[${H + 1};1H${ESC}[J`; }
    return seq;
  }
  const m = /^\x1b\[([?>=<!]?)([0-9;:]*)([ -\/]*)([@-~])$/.exec(seq);
  if (!m) return seq;
  const [, priv, params, inter, fin] = m;
  if (inter) return seq;
  const p = params === "" ? [] : params.split(";");
  const n = (k, d) => (p[k] === undefined || p[k] === "" ? d : Number(p[k]));

  if (!priv) {
    switch (fin) {
      case "H": case "f": // CUP: linha;coluna
        return `${ESC}[${n(0, 1) + H};${n(1, 1)}${fin}`;
      case "d": // VPA
        return `${ESC}[${n(0, 1) + H}d`;
      case "r": { // DECSTBM
        const top = n(0, 1), bot = p[1] === undefined || p[1] === "" ? rows - H : n(1, rows - H);
        return `${ESC}[${top + H};${Math.min(bot + H, rows)}r`;
      }
      case "J": {
        const mode = n(0, 0);
        if (mode === 0) return seq;
        // 1/2/3 apagariam o cabeçalho: apaga só a área do claude, guardando o cursor
        redraw(); // 1 apaga do topo até o cursor: o cabeçalho volta no redesenho
        if (mode === 1) return seq;
        return `${ESC}7${ESC}[${H + 1};1H${ESC}[J${ESC}8`;
      }
    }
    return seq;
  }
  if (priv === "?" && (fin === "h" || fin === "l")) {
    // troca de tela (alt-screen) limpa tudo: redesenhar o cabeçalho depois
    if (p.some((x) => x === "1049" || x === "47" || x === "1047")) redraw();
  }
  return seq;
}

// ---------- teclado/mouse -> claude ----------
export function makeInputTranslator(getH) {
  return function translate(data) {
    const H = getH();
    let s = typeof data === "string" ? data : data.toString("binary");
    // mouse SGR: ESC [ < b ; x ; y (M|m)
    s = s.replace(/\x1b\[<(\d+);(\d+);(\d+)([Mm])/g, (all, b, x, y, f) => {
      const yy = Number(y) - H;
      return yy < 1 ? "" : `\x1b[<${b};${x};${yy}${f}`;
    });
    // relatório de posição do cursor: ESC [ linha ; coluna R
    s = s.replace(/\x1b\[(\d+);(\d+)R/g, (all, r, c) => `\x1b[${Math.max(1, Number(r) - H)};${c}R`);
    // mouse X10 legado: ESC [ M b x y (bytes + 32)
    s = s.replace(/\x1b\[M([\s\S])([\s\S])([\s\S])/g, (all, b, x, y) => {
      const yy = y.charCodeAt(0) - H;
      return yy < 33 ? "" : `\x1b[M${b}${x}${String.fromCharCode(yy)}`;
    });
    return Buffer.from(s, "binary");
  };
}
