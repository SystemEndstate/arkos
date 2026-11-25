// Saída do /arkos: tabela dos módulos + o ativo nesta sessão (lido do estado mais recente).
import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { modules, SESS_DIR, readJson } from "./lib/core.mjs";
import { playbooks } from "./src/classificador.mjs";

let active = null;
try {
  const last = readdirSync(SESS_DIR).map((f) => join(SESS_DIR, f)).sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs)[0];
  if (last) active = readJson(last);
} catch {}

const lines = ["| # | Módulo | Playbooks (passos) |", "|---|---|---|"];
modules().forEach((m, i) => {
  const on = active?.module === m.id ? " ◀ ativo" : "";
  const pb = playbooks().filter((p) => p.modulos.includes(m.id)).map((p) => `${p.nome} (${p.passos.length})`).join(", ");
  lines.push(`| ${i + 1} | ${m.nome}${on} | ${pb} |`);
});
console.log(lines.join("\n"));
