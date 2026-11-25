// Logo da ARKOS em todo lugar, com um renderizador só, em cascata: Sixel > mini Rotor D > texto ("◆").
// O modo é detectado uma vez (DA1 com prazo curto) e fica em ARKOS_LOGO, herdado pelos hooks e pela moldura.
import { config } from "./core.mjs";
import { miniRotor } from "./minirotor.mjs";
import { rotorLines, proporcaoCelula } from "./rotor.mjs";
import { sixel as codificar, rasterRotor, temSixel, limiteDA1, lerCelula, celulaSixel, ladoSixel } from "./sixel.mjs";

const ESC = "\x1b";
export const VOLT = `${ESC}[38;2;198;244;50m`, VERMELHO = `${ESC}[38;2;255;107;107m`, MUDO = `${ESC}[38;2;107;114;128m`, BRANCO = `${ESC}[38;2;242;243;245m`, Z = `${ESC}[0m`, NEGRITO = `${ESC}[1m`;

// modo sem consulta: preferência, depois o terminal conhecido; conhost e terminais sem nome caem no texto
export function modoProvavel(env = process.env, cfg = config()) {
  const pref = String(env.ARKOS_LOGO || cfg.miniRotor || env.ARKOS_MINIROTOR || "auto").toLowerCase();
  if (["sixel", "d", "texto"].includes(pref)) return pref;
  if (env.TERM_PROGRAM === "OMaestro" || env.OMAESTRO_TERMINAL_ID || env.WT_SESSION || env.TERM_PROGRAM) return "d";
  return "texto";
}

// detecção completa (uma vez por execução): DA1 com atributo 4 = Sixel
export async function detectarLogo({ diag = () => {} } = {}) {
  if (process.env.ARKOS_LOGO) return process.env.ARKOS_LOGO;
  const pref = String(config().miniRotor || process.env.ARKOS_MINIROTOR || "auto").toLowerCase();
  let modo = modoProvavel(process.env, { miniRotor: pref });
  if (pref === "auto" && process.stdin.isTTY && process.stdout.isTTY) {
    const limite = limiteDA1();
    const resp = await new Promise((ok) => {
      let buf = "";
      const fim = () => { clearTimeout(t); process.stdin.off("data", ler); try { process.stdin.setRawMode(false); } catch {} process.stdin.pause(); ok(buf); };
      const ler = (d) => { buf += d.toString("latin1"); if (/\[\?[\d;]*c/.test(buf)) fim(); };
      const t = setTimeout(fim, limite);
      try { process.stdin.setRawMode(true); } catch {}
      process.stdin.on("data", ler); process.stdin.resume();
      // CSI 16 t antes do DA1: o terminal responde em ordem, então a célula (se houver) chega antes do DA1
      process.stdout.write(`${ESC}[16t${ESC}[c`);
    });
    if (temSixel(resp)) modo = "sixel";
    const cel = lerCelula(resp);
    if (cel) process.env.ARKOS_CELULA_PX = cel;
    diag(`DA1 = ${JSON.stringify(resp) || `(sem resposta em ${limite} ms)`} · logo: ${modo} · célula ${celulaSixel().w}×${celulaSixel().h}`);
  } else diag(`logo: ${modo} (preferência ${pref}, sem consulta)`);
  process.env.ARKOS_LOGO = modo;
  return modo;
}

// marca pequena (2 colunas): mini Rotor D, ou "◆ " em Volt no modo texto. Fora da moldura o Sixel vira D
// (imagem solta numa linha de texto pode rolar a tela); dentro da moldura o Sixel é desenhado por cima.
export const marca = (q = 0) => miniRotor(q);

// etiqueta de mensagem: logo + ARKOS (Volt) ou, em erro, logo + ARKOS ▲ (vermelho)
// Fora da moldura não há ícone pequeno (bloco de 1-2 células deforma; Sixel solto rola a tela): só ARKOS em Volt.
// O logo de verdade aparece grande (boas-vindas, banner) e, dentro da moldura, no rodapé e no spinner.
export function etiqueta(tipo = "ok") {
  return tipo === "erro" ? `${VERMELHO}ARKOS ▲${Z}` : `${VOLT}ARKOS${Z}`;
}

// logo grande (H linhas) + texto à direita. Com Sixel: bloco em branco e a imagem desenhada por cima.
export function blocoComLogo(H, direita, modo = process.env.ARKOS_LOGO || modoProvavel()) {
  const sixel = modo === "sixel";
  const logo = sixel ? Array(H).fill(" ".repeat(2 * H)) : rotorLines(H, proporcaoCelula(process.env, config()));
  const larg = sixel ? 2 * H : logo[0].replace(/\x1b\[[0-9;]*m/g, "").length;
  const linhas = Array.from({ length: Math.max(H, direita.length) }, (_, i) => `  ${logo[i] || " ".repeat(larg)}    ${direita[i] || ""}`);
  let s = linhas.join("\n") + "\n";
  // Sixel: volta ao começo do bloco (já impresso, sem rolar), desenha e restaura o cursor
  if (sixel) s += `${ESC}7${ESC}[${linhas.length}A${ESC}[3G` + codificar(rasterRotor(ladoSixel(2 * H, H), ladoSixel(2 * H, H), 0)) + `${ESC}8`;
  return s;
}
