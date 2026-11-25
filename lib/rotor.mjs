// Logo Rotor em meio-blocos (mesma geometria de brand/ e terminal/build_mock.py).
import { fg, bg, C } from "./core.mjs";

const VOLT = "#C6F432", WHITE = "#F2F3F5";
const voltPolys = [[[32, 32], [148, 32], [148, 66], [118, 96], [32, 96]]];
const whitePolys = [
  [[224, 32], [224, 148], [190, 148], [160, 118], [160, 32]],
  [[224, 224], [108, 224], [108, 190], [138, 160], [224, 160]],
  [[32, 224], [32, 108], [66, 108], [96, 138], [96, 224]],
];

function inside(px, py, poly) {
  let c = false;
  for (let i = 0, n = poly.length; i < n; i++) {
    const [x1, y1] = poly[i], [x2, y2] = poly[(i + 1) % n];
    if ((y1 > py) !== (y2 > py) && px < ((x2 - x1) * (py - y1)) / (y2 - y1) + x1) c = !c;
  }
  return c;
}

// Proporção altura/largura da célula do terminal. Half-block quadrado exige W = H * proporção.
// O xterm.js do O Maestro não responde CSI 16 t; medido no print: ~2,75. Windows Terminal/conhost (Cascadia/Consolas): ~2,1.
// ARKOS_CELULA ou config.celula sobrescrevem.
export function proporcaoCelula(env = process.env, cfg = {}) {
  const n = Number(env.ARKOS_CELULA || cfg.celula);
  if (n > 1 && n < 4) return n;
  if (env.TERM_PROGRAM === "OMaestro" || env.OMAESTRO_TERMINAL_ID) return 2.75;
  return 2.1;
}

// Rotor com H linhas de texto (2H "pixels" em altura) e largura calculada para sair quadrado.
export function rotorLines(H = 10, prop = proporcaoCelula()) {
  const W = Math.max(4, Math.round(H * prop));
  const col = (gx, gy) => {
    const x = 24 + ((gx + 0.5) * 208) / W, y = 24 + ((gy + 0.5) * 208) / (2 * H);
    if (voltPolys.some((p) => inside(x, y, p))) return VOLT;
    if (whitePolys.some((p) => inside(x, y, p))) return WHITE;
    return null;
  };
  const out = [];
  for (let r = 0; r < H; r++) {
    let line = "";
    for (let c = 0; c < W; c++) {
      const t = col(c, 2 * r), b = col(c, 2 * r + 1);
      if (!t && !b) line += " ";
      else if (t === b) line += fg(t) + "█";
      else if (!b) line += fg(t) + "▀";
      else if (!t) line += fg(b) + "▄";
      else line += fg(t) + bg(b) + "▀" + "[49m";
    }
    out.push(line + C.reset);
  }
  return out;
}
