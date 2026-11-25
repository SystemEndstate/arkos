// Hook SessionStart: registra a sessão no estado da execução e passa o perfil do negócio ao modelo.
// Nada visível aqui (o cabeçalho fixo já mostra a marca); só contexto.
import { loadState, saveState, profile, VERSION, planoLocal } from "../lib/core.mjs";
import { readStdin, emit } from "./io.mjs";

const input = await readStdin();
const st = loadState(input.session_id);
st.sessionId = input.session_id;
// /clear começa conversa nova: módulo, passos e contexto voltam ao zero
if (input.source === "clear") {
  for (const k of ["module", "moduleLabel", "moduleShort", "playbook", "playbookId", "steps", "done", "total", "current", "tasks", "lastFailure"]) delete st[k];
  st.ctx = null;
}
st.inicio ??= new Date().toISOString();
saveState(input.session_id, st);

const p = profile(input.cwd || process.cwd());
const linhas = [`[ARKOS v${VERSION}] Sessão iniciada pelo comando arkos.`];
// regras de acesso: o plano decide o limite B (sigilo de skill) e os bloqueios; a base filtra conteúdo no servidor
const plano = planoLocal();
linhas.push(plano === "vip"
  ? "[ARKOS] Plano da chave: vip. Acesso total; pode dizer o nome exato das skills. Limites A, C e D continuam valendo."
  : "[ARKOS] Plano da chave: membro. Bloqueado: e-commerce, TikTok Shop, UGC, VSL e advertorial (responder \"Isso faz parte do plano VIP.\"). Skill: só a função, nunca o nome técnico. Limites A, C e D valem.");
if (p && !p._erro) linhas.push(`Perfil do negócio: ${JSON.stringify(Object.fromEntries(Object.entries(p).filter(([k]) => !k.startsWith("_"))))}`);
if (p && p._erro) linhas.push(`Perfil do negócio com erro: ${p._erro}. Avise o usuário uma vez.`);
emit({ hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: linhas.join("\n") } });
