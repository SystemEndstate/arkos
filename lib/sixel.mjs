// Rotor de verdade em Sixel (Windows Terminal 1.22+). Geometria igual a brand/ e lib/rotor.mjs.
// O WT desenha Sixel numa célula virtual de 10×20 px, então 2 colunas × 1 linha = 20×20 px, quadrado em qualquer fonte.
const VOLT = [198, 244, 50], WHITE = [242, 243, 245];
const voltPolys = [[[32, 32], [148, 32], [148, 66], [118, 96], [32, 96]]];
const whitePolys = [
  [[224, 32], [224, 148], [190, 148], [160, 118], [160, 32]],
  [[224, 224], [108, 224], [108, 190], [138, 160], [224, 160]],
  [[32, 224], [32, 108], [66, 108], [96, 138], [96, 224]],
];
const gira = (p, q) => p.map(([x, y]) => { for (let i = 0; i < q; i++) [x, y] = [256 - y, x]; return [x, y]; });

function inside(px, py, poly) {
  let c = false;
  for (let i = 0, n = poly.length; i < n; i++) {
    const [x1, y1] = poly[i], [x2, y2] = poly[(i + 1) % n];
    if ((y1 > py) !== (y2 > py) && px < ((x2 - x1) * (py - y1)) / (y2 - y1) + x1) c = !c;
  }
  return c;
}

// q: quadro (a pá Volt gira 90° por quadro). Devolve matriz h×w de [r,g,b,alfa 0..1] com supersample 4×4.
export function rasterRotor(w, h, q = 0, margem = 24) {
  // as pás brancas giram junto: rodar todas mantém o desenho, então a Volt troca de canto girando só a cor
  const v = voltPolys.map((p) => gira(p, q)), b = [...whitePolys, ...voltPolys].map((p) => gira(p, q)).filter((p, i, a) => !v.some((x) => JSON.stringify(x) === JSON.stringify(p)));
  const S = 4, span = 256 - 2 * margem, px = [];
  for (let y = 0; y < h; y++) {
    const row = [];
    for (let x = 0; x < w; x++) {
      let nv = 0, nw = 0;
      for (let sy = 0; sy < S; sy++) for (let sx = 0; sx < S; sx++) {
        const X = margem + ((x + (sx + 0.5) / S) * span) / w, Y = margem + ((y + (sy + 0.5) / S) * span) / h;
        if (v.some((p) => inside(X, Y, p))) nv++; else if (b.some((p) => inside(X, Y, p))) nw++;
      }
      const a = (nv + nw) / (S * S);
      const cor = nv >= nw ? VOLT : WHITE;
      row.push([...cor, a]);
    }
    px.push(row);
  }
  return px;
}

// Sixel com fundo transparente: pixel com alfa < 0,5 fica sem tinta. Cores: Volt, branco e os tons de borda
// misturados com o Ink (#0A0B0D), em 3 níveis, para a borda não serrilhar.
export function sixel(px) {
  const h = px.length, w = px[0].length, INK = [10, 11, 13];
  const pal = [], idx = new Map();
  const cor = ([r, g, b, a]) => {
    if (a < 0.2) return -1;
    const k = a > 0.8 ? 1 : a > 0.5 ? 0.66 : 0.4;
    const c = [r, g, b].map((v, i) => Math.round(v * k + INK[i] * (1 - k)));
    const key = c.join(",");
    if (!idx.has(key)) { idx.set(key, pal.length); pal.push(c); }
    return idx.get(key);
  };
  const m = px.map((row) => row.map(cor));
  let s = `\x1bP0;1;0q"1;1;${w};${h}`;
  pal.forEach((c, i) => { s += `#${i};2;${c.map((v) => Math.round((v * 100) / 255)).join(";")}`; });
  for (let y0 = 0; y0 < h; y0 += 6) {
    const linhas = [];
    pal.forEach((_, ci) => {
      let row = "", usado = false;
      for (let x = 0; x < w; x++) {
        let bits = 0;
        for (let k = 0; k < 6 && y0 + k < h; k++) if (m[y0 + k][x] === ci) bits |= 1 << k;
        if (bits) usado = true;
        row += String.fromCharCode(63 + bits);
      }
      if (usado) linhas.push(`#${ci}` + row.replace(/(.)\1{3,}/g, (r, c) => `!${r.length}${c}`));
    });
    s += linhas.join("$") + "-";
  }
  return s + "\x1b\\";
}

// Tamanho da célula em pixels para o Sixel. Padrão: a célula virtual 10×20 do Windows Terminal (fixa, qualquer
// fonte). Outros terminais (O Maestro: xterm.js, ex. 7×17) desenham Sixel em pixel real: a detecção pergunta
// CSI 16 t junto com o DA1 e guarda a resposta em ARKOS_CELULA_PX ("LxA"), herdada pelos hooks e pela moldura.
export function celulaSixel(env = process.env) {
  const m = /^(\d+)x(\d+)$/.exec(env.ARKOS_CELULA_PX || "");
  const w = m ? +m[1] : 0, h = m ? +m[2] : 0;
  return w >= 4 && w <= 64 && h >= 8 && h <= 128 ? { w, h } : { w: 10, h: 20 };
}
// resposta ao CSI 16 t: ESC [ 6 ; altura ; largura t. No WT vale a célula virtual 10×20 (ignora a resposta).
export function lerCelula(resposta, env = process.env) {
  const m = /\x1b\[6;(\d+);(\d+)t/.exec(resposta || "");
  if (!m || (env.WT_SESSION && !(env.TERM_PROGRAM === "OMaestro" || env.OMAESTRO_TERMINAL_ID))) return null;
  return `${+m[2]}x${+m[1]}`;
}
// lado do quadrado (px) que cabe num bloco de colunas × linhas: o Rotor fica quadrado e não invade o texto
export function ladoSixel(colunas, linhas, env = process.env) {
  const { w, h } = celulaSixel(env);
  return Math.max(1, Math.min(colunas * w, linhas * h));
}

// ícone de 2 colunas × 1 linha (20×20 px na célula do WT); cache dos 4 quadros por tamanho
const cache = new Map();
export function iconeSixel(q = 0, colunas = 2, linhas = 1) {
  const lado = ladoSixel(colunas, linhas);
  const k = `${q}:${lado}`;
  if (!cache.has(k)) cache.set(k, sixel(rasterRotor(lado, lado, q % 4)));
  return cache.get(k);
}

// O terminal anuncia Sixel no DA1 (atributo 4). O xterm.js do O Maestro não anuncia.
// Quanto esperar a resposta ao DA1. No O Maestro a consulta é curta: o 1.3.5+ anuncia Sixel (atributo 4) na hora;
// o antigo responde sem o 4 ou não responde (terminal fora da tela), e aí fica o mini Rotor D como antes.
export function limiteDA1(env = process.env) { return env.TERM_PROGRAM === "OMaestro" || env.OMAESTRO_TERMINAL_ID ? 150 : 400; }
export function temSixel(respostaDA1) { return /\x1b\[\?[\d;]*c/.test(respostaDA1) && /[?;]4[;c]/.test(respostaDA1); }
