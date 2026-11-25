// Console do Windows: liga o processamento de sequências VT (ENABLE_VIRTUAL_TERMINAL_PROCESSING)
// no conhost antigo (Windows PowerShell 5.1, cmd). Sem dependência nativa: usa o próprio Node,
// que já liga VT ao escrever num TTY a partir do Node 12+ (libuv). Aqui só detectamos o caso sem cor.
export function ativarVT() {
  if (process.platform !== "win32") return true;
  // libuv liga ENABLE_VIRTUAL_TERMINAL_PROCESSING em stdout TTY; se o console não aceitar,
  // getColorDepth cai para 4 bits e o banner usa a paleta de 256 cores.
  try { return process.stdout.isTTY ? process.stdout.getColorDepth() >= 8 : false; } catch { return false; }
}

export function profundidadeCor() {
  if (process.env.ARKOS_CORES) return Number(process.env.ARKOS_CORES);
  if (process.env.COLORTERM === "truecolor" || process.env.WT_SESSION) return 24;
  try { return process.stdout.isTTY ? process.stdout.getColorDepth() : 24; } catch { return 24; }
}
