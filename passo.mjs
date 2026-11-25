// Alternativa à lista de tarefas: o Claude marca o progresso do playbook.
// Uso: node passo.mjs <N> [nome]   começa o passo N (passos antes dele contam como concluídos)
//      node passo.mjs feito <N>    conclui o passo N (o próximo fica em andamento)
//      node passo.mjs fim          playbook concluído
//      node passo.mjs gate <verde|amarelo|vermelho>   veredito do gate em <execução>/gate.json (painel e revisão leem dali)
// Sessão: a execução do `arkos` (ARKOS_RUN_ID herdado pelo Bash); sem ela, a mais recente na mesma pasta.
import { readdirSync, statSync, writeFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { SESS_DIR, readJson, loadState, saveState } from "./lib/core.mjs";

const [a, b, ...rest] = process.argv.slice(2);
let id = process.env.ARKOS_RUN_ID;
let st = id ? loadState(id) : null;
if (!st || !st.total) {
  const cwd = resolve(process.cwd()).toLowerCase();
  let files = [];
  try { files = readdirSync(SESS_DIR).map((f) => join(SESS_DIR, f)).sort((x, y) => statSync(y).mtimeMs - statSync(x).mtimeMs); } catch {}
  const file = files.find((f) => (readJson(f)?.cwd || "").toLowerCase() === cwd);
  if (!file) { console.log("ARKOS: nenhuma sessão ativa"); process.exit(0); }
  id = file.split(/[\/]/).pop().replace(/\.json$/, "");
  st = readJson(file, {});
}
if (!st.total) { console.log("ARKOS: sessão sem playbook"); process.exit(0); }
if (a === "gate") {
  const cor = String(b || "").toLowerCase();
  if (!["verde", "amarelo", "vermelho"].includes(cor)) { console.log("uso: node passo.mjs gate verde|amarelo|vermelho"); process.exit(2); }
  const dir = st.execucao?.dir;
  if (!dir || !existsSync(dir)) { console.log("ARKOS: sessão sem pasta de execução"); process.exit(0); }
  const arq = join(dir, "gate.json");
  const antes = readJson(arq, {});
  const g = { cor, tentativas: (antes.tentativas || 0) + 1, em: new Date().toISOString(), historico: [...(antes.historico || []), { cor, em: new Date().toISOString() }] };
  writeFileSync(arq, JSON.stringify(g, null, 2), "utf8");
  console.log(`ARKOS gate ${cor} (tentativa ${g.tentativas})`);
  process.exit(0);
}
const passo = (n) => Math.max(1, Math.min(Number(n) || 1, st.total));

if (a === "fim") st.done = st.total;
else if (a === "feito") st.done = Math.max(st.done || 0, passo(b));
else {
  st.done = passo(a) - 1;
  if (b || rest.length) st.current = [b, ...rest].filter(Boolean).join(" ");
}
if (st.done < st.total && (a === "feito" || !(b || rest.length))) st.current = st.steps?.[st.done] || st.current;
saveState(id, st);
console.log(`ARKOS passo ${Math.min(st.done + 1, st.total)}/${st.total}${st.done >= st.total ? " (concluído)" : ` · ${st.current}`}`);
