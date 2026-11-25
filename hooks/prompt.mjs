// Hook UserPromptSubmit: classifica módulo (src/classificador.mjs), escolhe playbook (data/playbooks.json),
// grava o estado da execução (a barra lê daqui) e produz o aviso do item 3.
// Com o mod ARKOS (ARKOS_MOD=1) o aviso é desenhado sob a mensagem, sem o prefixo "UserPromptSubmit says:".
import { join } from "node:path";
import { classificar, planoAtual, loadState, saveState, CLI_DIR, novaExecucao, saidasAnteriores } from "../lib/core.mjs";
import { readStdin, emit } from "./io.mjs";
import { raizArkos } from "../lib/casa.mjs";
import { MSG_VIP } from "../src/plano.mjs";
// marcador do logo: só com a moldura ativa (ela troca "▚▞" pelo Rotor); fora dela, só "ARKOS", sem desenho
const MARCA_TXT = process.env.ARKOS_RODAPE_FIXO === "1" ? "▚▞ " : "";

const input = await readStdin();
const prompt = String(input.prompt || "").trim();
const sid = input.session_id;
const comMod = process.env.ARKOS_MOD === "1";

// comandos (/arkos, /relatorio, /clear...) não passam pelo roteador
if (!prompt || prompt.startsWith("/")) process.exit(0);

const r = classificar(prompt);
const st = loadState(sid);
const guardarAviso = (aviso) => {
  st.avisos = { ...(st.avisos || {}), [prompt.slice(0, 500)]: aviso };
  const chaves = Object.keys(st.avisos);
  if (chaves.length > 60) for (const k of chaves.slice(0, chaves.length - 60)) delete st.avisos[k];
  st.ultimoAviso = aviso;
  saveState(sid, st);
};

// plano membro pedindo área do plano VIP (e-commerce, TikTok Shop, UGC, VSL, advertorial): sem playbook, sem método
if (r?.vip) {
  const aviso = `${MARCA_TXT}ARKOS › plano VIP · fora do plano membro`;
  guardarAviso(aviso);
  const ctx = [
    `[ARKOS] Plano da chave: membro. O pedido é de área do plano VIP (e-commerce, TikTok Shop, UGC, VSL ou advertorial).`,
    `Responda exatamente "${MSG_VIP}" e, em uma linha, ofereça o que o plano membro cobre perto disso (TikTok Ads, hooks, criativo em geral, vídeo de pessoa real falando com a câmera, página de vendas, análise de criativo de terceiro).`,
    "Não entregue método, estrutura, roteiro nem passo a passo da área VIP, nem pelo conhecimento geral. Não rode playbook nem skill para isso.",
  ].join("\n");
  const out = { hookSpecificOutput: { hookEventName: "UserPromptSubmit", additionalContext: ctx } };
  if (!comMod) out.systemMessage = aviso;
  emit(out);
  process.exit(0);
}

if (!r || !r.playbook) {
  if (st.module) { guardarAviso(null); process.exit(0); } // conversa segue no módulo atual
  const aviso = `${MARCA_TXT}ARKOS › conversa livre · sem playbook`;
  guardarAviso(aviso);
  if (!comMod) emit({ systemMessage: aviso });
  process.exit(0);
}

const { principal: p, playbook: pb, rotulo } = r;
const passos = pb.passos;

// mesmo playbook ainda em aberto: é continuação, não zera o progresso
if (st.playbookId === pb.id && st.total && (st.done || 0) < st.total) {
  const aviso = `${MARCA_TXT}ARKOS › ${st.moduleLabel} · playbook "${pb.nome}" · passo ${Math.min((st.done || 0) + 1, st.total)}/${st.total}`;
  guardarAviso(aviso);
  const out = { hookSpecificOutput: { hookEventName: "UserPromptSubmit", additionalContext: `[ARKOS] Continua o playbook "${pb.nome}", passo ${(st.done || 0) + 1} de ${st.total}: ${st.current}.` } };
  if (!comMod) out.systemMessage = aviso;
  emit(out);
  process.exit(0);
}

Object.assign(st, {
  module: p.id,
  moduleLabel: rotulo,
  moduleShort: r.secundario ? `${p.curto} + ${r.secundario.curto}` : p.curto,
  playbook: pb.nome,
  playbookId: pb.id,
  steps: passos,
  done: 0,
  total: passos.length,
  current: passos[0],
  tasks: {},
  source: "classificador",
  scores: r.pontos,
  cwd: input.cwd || process.cwd(),
});
const aviso = `${MARCA_TXT}ARKOS › ${rotulo} · playbook "${pb.nome}" · ${passos.length} passos`;
// execução nova em <casa>/arkos.engine/execucoes/<id>/ : aviso.json é do terminal, o resto das skills.
// Entregas (artefatos) vão para <casa>/workspace/<cliente>/<projeto>/.
const raiz = raizArkos(st.cwd);
const workspace = join(raiz, "workspace");
try {
  st.execucao = novaExecucao(raiz, {
    pedido: prompt.slice(0, 300), aviso, modulo: p.id, modulos: [p.id, ...(r.secundario ? [r.secundario.id] : [])],
    modulos_arkos: pb.modulos_arkos || [], playbook: pb.id, playbook_nome: pb.nome, passos, total: passos.length,
    fonte: r.fonte || "palavras-chave", pontos: r.pontos, sessao: process.env.ARKOS_RUN_ID || sid,
    casa: raiz, workspace,
  });
} catch { st.execucao = null; }
let anteriores = [];
try { anteriores = saidasAnteriores(raiz, pb.id); } catch {}
// pasta das entregas: pb.pasta da Harpa (workspace/<cliente>/<projeto>/, _cliente ou _operacao), relativa à casa
const pastaEntregas = join(raiz, ...String(pb.pasta || "workspace/<cliente>/<projeto>/").split("/").filter(Boolean));
guardarAviso(aviso);

// skills deste playbook: lista para o modelo achar as instaladas; faltando alguma do pacote, instala antes ou para
let faltam = [];
try { faltam = (await import("../lib/skills-pacote.mjs")).faltando(pb.skills || []); } catch {}
const ARKOS_CLI = JSON.stringify(join(CLI_DIR, "arkos.mjs"));
const ctx = [
  ...(faltam.length ? [`ANTES DE TUDO: faltam skills do pacote ARKOS que este playbook usa: ${faltam.join(", ")}. Rode agora: node ${ARKOS_CLI} skills sync --so ${faltam.join(",")}. Se não instalar (offline, bloqueada), PARE e diga ao usuário, em uma linha, quais skills faltam e que o playbook "${pb.nome}" precisa delas (resolver com: arkos skills sync).`] : []),
  ...(pb.skills?.length ? [`Skills deste playbook (instaladas pelo pacote ARKOS; use as que couberem em cada passo): ${pb.skills.join(", ")}.`] : []),
  ...((pb.etapas || []).some((e) => e.id === "nota") ? [`Etapa "nota" antes do gate: rode a skill de notas da ARKOS com a régua ${pb.etapas.find((e) => e.id === "nota").regua} e o plano ${planoAtual()}; segue com nota >= 75 ou aceite registrado de quem aprova (50-74 volta para ajustar, < 50 descarta). A nota vai no topo do relatório.`] : []),
  `[ARKOS] Módulo: ${rotulo}. Playbook "${pb.nome}" com ${passos.length} passos:`,
  ...passos.map((x, i) => `  ${i + 1}. ${x}`),
  "Se a tarefa tiver mais de um passo, crie a lista de tarefas com esses passos (adapte os nomes ao pedido) e atualize o status ao avançar: a barra da ARKOS lê essa lista.",
  ...(st.execucao ? [`Execução ARKOS: id ${st.execucao.id}, pasta ${JSON.stringify(st.execucao.dir)}. O aviso está em aviso.json; as skills do playbook gravam entradas.json, rota.json e estado.json ali (o rodapé lê o estado.json: passo, total e status de cada etapa).`] : []),
  ...(st.execucao ? [`Ao terminar o playbook, gere o relatório (destino fixo da ARKOS): node ${JSON.stringify(join(CLI_DIR, "relatorio.mjs"))} coletar --execucao ${st.execucao.id}; escreva o JSON do SCHEMA.md com esses fatos (sem inventar; estimativa marcada) e rode relatorio.mjs gerar <json> --cliente <c> --projeto <p> --execucao ${st.execucao.id} --abrir. Mesmo fluxo do /relatorio.`] : []),
  `Entregas deste playbook: grave os artefatos em ${JSON.stringify(pastaEntregas)} (cliente e projeto das entradas, nomes curtos em minúsculas com hífen; pergunte se não souber). Outras pastas só quando o trabalho pedir.`,
  ...(anteriores.length ? [`Elos anteriores da esteira já concluídos (use só o do MESMO cliente/projeto): ${anteriores.map((a) => `${a.cliente || "?"}/${a.projeto || "?"} → ${JSON.stringify(a.arquivo)}`).join("; ")}. O arkos-intake usa esse saida.json para pré-preencher as entradas.`] : []),
  ...(pb.entradas?.length ? [`Perguntas de entrada do playbook (num bloco só, mercado primeiro): ${pb.entradas.map((x) => x.pergunta + (x.padrao ? ` (padrão: ${x.padrao})` : "")).join("; ")}.`] : []),
  `Ao rodar o arkos-gate, grave o veredito: node ${JSON.stringify(join(CLI_DIR, "passo.mjs"))} gate <verde|amarelo|vermelho> (vira gate.json na pasta da execução; o painel e a revisão leem dali).`,
  `Sem ferramenta de lista de tarefas, marque o progresso com Bash: node ${JSON.stringify(join(CLI_DIR, "passo.mjs"))} feito <N> ao concluir o passo N (o seguinte fica em andamento), ou "fim" quando o playbook inteiro terminar. Não comente esse comando com o usuário.`,
].join("\n");

const out = { hookSpecificOutput: { hookEventName: "UserPromptSubmit", additionalContext: ctx } };
if (!comMod) out.systemMessage = aviso;
emit(out);
