// Rolagem da área do meio (a conversa do Claude) com o topo e o rodapé parados.
// A moldura liga o mouse SGR (1000+1006) só para receber a roda. Se o próprio Claude ligar o mouse,
// tudo vai para ele como antes. Seleção de texto: Shift+arrastar (WT e O Maestro).
const ESC = "\x1b";
export const LINHAS_HISTORICO = 10000;
export const PASSO_RODA = 3;

// s: o que chegou do teclado/mouse. Devolve { passar, rolar, fim }.
// rolar > 0 sobe no histórico; fim = voltar ao fim (End, ou qualquer tecla quando rolado).
// ctx: { ativo (tela normal, não alternativa), claudeMouse, rolado, areaIni, areaFim (linhas reais, 1-based), pagina }
export function filtrarEntrada(s, ctx) {
  let rolar = 0, fim = false;
  const re = /\x1b\[<(\d+);(\d+);(\d+)([Mm])|\x1b\[5;2~|\x1b\[6;2~|\x1b\[1;2A|\x1b\[1;2B|\x1b\[F|\x1bOF|\x1b\[4~/g;
  const passar = s.replace(re, (seq, b, _x, y) => {
    if (b !== undefined) {
      if (ctx.claudeMouse) return seq; // o Claude pediu o mouse: é dele
      const bt = +b, linha = +y;
      if (ctx.ativo && bt & 64 && linha >= ctx.areaIni && linha <= ctx.areaFim) rolar += bt & 1 ? -PASSO_RODA : PASSO_RODA;
      return ""; // clique sem o Claude ter pedido mouse: descartado (seleção é com Shift)
    }
    if (!ctx.ativo) return seq;
    if (seq === `${ESC}[5;2~`) { rolar += ctx.pagina; return ""; }
    if (seq === `${ESC}[6;2~`) { rolar -= ctx.pagina; return ""; }
    if (seq === `${ESC}[1;2A`) { rolar += 1; return ""; }
    if (seq === `${ESC}[1;2B`) { rolar -= 1; return ""; }
    // End: só é da moldura quando a conversa está rolada
    if (ctx.rolado) { fim = true; return ""; }
    return seq;
  });
  if (passar && ctx.rolado && !rolar) fim = true; // digitar qualquer coisa volta ao fim
  return { passar, rolar, fim };
}

// Barra de rolagem: { inicio, tamanho } do polegar dentro de `altura` linhas.
// total = linhas do histórico + tela; rolagem = linhas acima do fim.
export function polegar(altura, total, rolagem) {
  if (total <= altura) return { inicio: 0, tamanho: altura };
  const tamanho = Math.max(1, Math.round((altura * altura) / total));
  const maxRol = total - altura;
  const frac = 1 - Math.min(rolagem, maxRol) / maxRol; // 0 = topo, 1 = fim
  return { inicio: Math.round(frac * (altura - tamanho)), tamanho };
}
