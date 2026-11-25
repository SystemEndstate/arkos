// Mini Rotor: 2 colunas × 1 linha, grade 4×2 de quadrantes, 3 cores (Volt, branco, vazio).
// Cada célula só tem frente + fundo, então em cada quadro o vazio central cede onde a célula já tem 2 cores.
// Quadro q: a pá Volt no canto q (0 TL, 1 TR, 2 BR, 3 BL), girando 90° por quadro.
const V = [198, 244, 50], W = [242, 243, 245], _ = null;
const FRAMES = [
  [[V, V, _, W], [W, W, W, W]], // pá Volt em cima à esquerda; fenda no topo entre as pás
  [[W, W, W, V], [W, _, W, V]],
  [[W, W, W, W], [W, _, V, V]],
  [[W, W, _, W], [V, V, W, W]],
];
// máscara TL TR BL BR -> quadrante
const QUAD = { 0: " ", 1: "▘", 2: "▝", 3: "▀", 4: "▖", 5: "▌", 6: "▞", 7: "▛", 8: "▗", 9: "▚", 10: "▐", 11: "▜", 12: "▄", 13: "▙", 14: "▟", 15: "█" };
const igual = (a, b) => a === b;

// célula a partir de [TL, TR, BL, BR] -> { ch, fg, bg }
function celula(px) {
  const cores = [...new Set(px.filter(Boolean))];
  const fg = cores[0] || null, bg = cores[1] || null;
  let m = 0;
  px.forEach((c, i) => { if (c && igual(c, fg)) m |= [1, 2, 4, 8][i]; });
  return { ch: QUAD[m], fg, bg };
}

// ARKOS_LOGO=texto (conhost e terminais sem os quadrantes): "◆ " em Volt, mesmas 2 colunas; gira ◆/◇
export function quadroMini(q = 0) {
  if (process.env.ARKOS_LOGO === "texto") return [{ ch: ((q % 2) + 2) % 2 ? "◇" : "◆", fg: V, bg: null }, { ch: " ", fg: null, bg: null }];
  const f = FRAMES[((q % 4) + 4) % 4];
  return [0, 1].map((cx) => celula([f[0][2 * cx], f[0][2 * cx + 1], f[1][2 * cx], f[1][2 * cx + 1]]));
}

const sgr = ({ fg, bg }) => `\x1b[0;${fg ? `38;2;${fg.join(";")}` : "39"};${bg ? `48;2;${bg.join(";")}` : "49"}m`;
export const sgrDe = sgr;
export const hexDe = (c) => (c ? "#" + c.map((n) => n.toString(16).padStart(2, "0")).join("") : undefined);

// ANSI pronto (2 colunas), para rodapé e banner
export function miniRotor(q = 0) { return quadroMini(q).map((c) => sgr(c) + c.ch).join("") + "\x1b[0m"; }

// marcador de texto puro (hooks, mod): a moldura troca por miniRotor parado
export const MARCA = "▚▞";
