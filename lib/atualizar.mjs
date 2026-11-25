// Atualização da instalação pública (sem git): baixa o zip do main no GitHub e troca os arquivos da CLI.
// Endereços vêm do ~/.arkos/config.json (atualizacao.fonte = versao.json, atualizacao.zip = zip do main),
// gravados pelo instalador a partir da organização. Nada fixo aqui.
import { spawn, spawnSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, mkdtempSync, openSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const tarExe = () => (process.platform === "win32" ? join(process.env.SystemRoot || "C:\\Windows", "System32", "tar.exe") : "tar");
const MANTER = new Set(["node_modules", ".git"]);

export async function atualizarPorZip(zip, destino) {
  if (!zip) throw new Error("sem atualizacao.zip no config: reinstale pelo instalador de uma linha");
  const tmp = mkdtempSync(join(tmpdir(), "arkos-upd-"));
  try {
    const r = await fetch(zip);
    if (!r.ok) throw new Error(`download: HTTP ${r.status}`);
    const arq = join(tmp, "arkos.zip");
    writeFileSync(arq, Buffer.from(await r.arrayBuffer()));
    const x = spawnSync(tarExe(), ["-xf", arq, "-C", tmp], { windowsHide: true, encoding: "utf8" });
    if (x.status !== 0) throw new Error(`zip: ${(x.stderr || "").trim().slice(0, 120)}`);
    const raiz = readdirSync(tmp).map((n) => join(tmp, n)).find((f) => statSync(f).isDirectory() && existsSync(join(f, "arkos.mjs")));
    if (!raiz) throw new Error("zip sem arkos.mjs");
    for (const n of readdirSync(destino)) if (!MANTER.has(n)) rmSync(join(destino, n), { recursive: true, force: true });
    for (const n of readdirSync(raiz)) if (!MANTER.has(n)) cpSync(join(raiz, n), join(destino, n), { recursive: true });
  } finally { rmSync(tmp, { recursive: true, force: true }); }
}

// ao abrir: versão nova no GitHub + atualizacao.auto = atualiza em segundo plano, sem janela, um por vez (trava 30 min)
export function atualizarEmSegundoPlano(cliArq, home) {
  const trava = join(home, "update.lock");
  try { if (Date.now() - statSync(trava).mtimeMs < 30 * 60000) return false; } catch {}
  mkdirSync(home, { recursive: true });
  writeFileSync(trava, String(Date.now()));
  const log = join(home, "update.log");
  const c = spawn(process.execPath, [cliArq, "update"], { detached: true, windowsHide: true, stdio: ["ignore", openSync(log, "w"), openSync(log, "a")] });
  c.unref();
  return true;
}
