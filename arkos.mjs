#!/usr/bin/env node
// Comando `arkos`: Claude Code com a camada ARKOS (cabeçalho fixo, tema, statusLine, hooks, mod, /arkos, /relatorio).
// Não toca no ~/.claude/settings.json: tudo entra por --settings/--plugin-dir só nesta execução.
import { spawn } from "node:child_process";
import { join, basename, delimiter } from "node:path";
import { existsSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { createRequire } from "node:module";
import { CLI_DIR, HOME_DIR, VERSION, writeJson, loadState, saveState, sessionPath, config as config0 } from "./lib/core.mjs";
import { bannerLines } from "./lib/banner.mjs";
import { statusCompleto } from "./src/status.mjs";
import { ativarVT } from "./lib/console.mjs";
import * as marcaLib from "./lib/marca.mjs";

const args = process.argv.slice(2);
ativarVT();

if (args[0] === "--version" || args[0] === "-V") { console.log(`arkos ${VERSION}`); process.exit(0); }
if (args[0] === "update") {
  // Atualiza a CLI: git pull (instalação por clone) ou zip do GitHub (atualizacao.zip), npm install e skills sync
  // (chave VIP: o sync baixa de novo o pacote VIP da base).
  const { execFileSync } = await import("node:child_process");
  const run = (cmd, a) => execFileSync(cmd, a, { cwd: CLI_DIR, stdio: "inherit", windowsHide: true, shell: process.platform === "win32" });
  try {
    if (existsSync(join(CLI_DIR, ".git"))) run("git", ["pull", "--ff-only"]);
    else await (await import("./lib/atualizar.mjs")).atualizarPorZip(config0().atualizacao?.zip, CLI_DIR);
    run("npm", ["install", "--omit=dev", "--no-fund", "--no-audit"]);
    // o pacote de skills vem junto com o framework (skills novas chegam para todos)
    run(process.execPath, [join(CLI_DIR, "arkos.mjs"), "skills", "sync"]);
    console.log(`${marcaLib.etiqueta()} atualizada.`);
  } catch {
    console.error(`${marcaLib.etiqueta("erro")} não consegui atualizar sozinha. Na pasta ${CLI_DIR}: git pull && npm install`);
    process.exit(1);
  }
  process.exit(0);
}
if (args[0] === "--diag-rodape") {
  // diagnóstico do Rotor no rodapé: versão, caminho, DA1 e o desenho do rodapé com Sixel na penúltima linha
  const { temSixel, iconeSixel, lerCelula, celulaSixel } = await import("./lib/sixel.mjs");
  const buf = await new Promise((ok) => {
    let b = ""; const ler = (d) => { b += d.toString("latin1"); if (/\[\?[\d;]*c/.test(b)) fim(); };
    const fim = () => { clearTimeout(t); process.stdin.off("data", ler); try { process.stdin.setRawMode(false); } catch {} process.stdin.pause(); ok(b); };
    const t = setTimeout(fim, 600);
    try { process.stdin.setRawMode(true); } catch {} process.stdin.on("data", ler); process.stdin.resume(); process.stdout.write("[16t[c");
  });
  { const c = lerCelula(buf); if (c) process.env.ARKOS_CELULA_PX = c; }
  const linhas = [
    `arkos ${VERSION} · ${CLI_DIR}`,
    `TERM_PROGRAM=${process.env.TERM_PROGRAM || "-"} · WT_SESSION=${process.env.WT_SESSION ? "sim" : "não"} · tela ${process.stdout.columns}x${process.stdout.rows}`,
    `DA1 = ${JSON.stringify(buf)} · Sixel: ${temSixel(buf) ? "SIM" : "NÃO"} · célula ${celulaSixel().w}×${celulaSixel().h} px`,
    `config miniRotor = ${config0().miniRotor ?? "auto"} · ARKOS_RODAPE_SIXEL = ${process.env.ARKOS_RODAPE_SIXEL ?? "-"}`,
  ];
  console.log(linhas.join("\n"));
  // ícone pequeno só existe em Sixel; sem Sixel, fora da moldura fica só "ARKOS" (nada de bloco de 1-2 células)
  if (temSixel(buf)) process.stdout.write("\nícone de teste (deve aparecer o Rotor antes de ARKOS):  " + iconeSixel(0) + " ARKOS\n\n");
  else { process.env.ARKOS_LOGO = marcaLib.modoProvavel(); process.stdout.write(`\n${marcaLib.etiqueta()} sem Sixel neste terminal (modo ${process.env.ARKOS_LOGO}): fora da moldura não há ícone pequeno.\n\n`); }
  try { (await import("node:fs")).appendFileSync(join(HOME_DIR, "rodape-debug.log"), `${new Date().toISOString()} --diag-rodape ${linhas.join(" | ")}\n`); } catch {}
  process.exit(0);
}
if (args[0] === "--banner") {
  console.log("\n" + bannerLines(process.cwd(), await statusCompleto()).join("\n") + "\n");
  process.exit(0);
}

async function casaLib0() { return import("./lib/casa.mjs"); }
// ---------- pacote de skills ----------
// `arkos skills [sync|remover|status]`: instala/atualiza exatamente o pacote da ARKOS em ~/.claude/skills
if (args[0] === "skills") {
  const sk = await import("./lib/skills-pacote.mjs");
  const E = marcaLib.etiqueta(), ERR = marcaLib.etiqueta("erro");
  const acao = args[1] || "status";
  if (acao === "status") {
    const s = sk.statusPacote();
    console.log(s ? `${E} pacote ARKOS v${s.versao}: ${s.presentes}/${s.total} skills (${s.nossas} instaladas pelo pacote) · ${sk.pastaSkills()}` : `${ERR} manifesto do pacote não encontrado`);
    process.exit(0);
  }
  if (acao === "remover") {
    const n = sk.remover();
    console.log(`${E} ${n.length} skills do pacote removidas de ${sk.pastaSkills()} (as pessoais ficaram)`);
    process.exit(0);
  }
  if (acao === "sync") {
    const substituir = args.includes("--substituir");
    const interativo = process.stdin.isTTY && process.stdout.isTTY;
    const perguntar = async (nome, link) => substituir || (interativo && /^s/i.test(await casaLib0().perguntar(`${E} já existe uma skill sua chamada "${nome}"${link ? " (link)" : ""}. Trocar pela do pacote? (s/N) `)));
    const iso = args.indexOf("--so"), it = args.indexOf("--trava");
    const so = iso !== -1 ? args[iso + 1].split(",").filter(Boolean) : null;
    let r;
    try { r = await sk.sincronizar({ perguntar, log: (m) => console.log(m), so }); }
    finally { if (it !== -1) { try { (await import("node:fs")).rmSync(args[it + 1], { force: true }); } catch {} } }
    const p = sk.carregarPacote();
    console.log(`${E} pacote ARKOS v${p.versao}: ${r.instaladas.length} instaladas · ${r.atualizadas.length} atualizadas · ${r.iguais.length} já em dia · ${r.pessoais.length} pessoais mantidas`);
    if (r.pessoais.length) console.log(`  pessoais com o mesmo nome (mantidas; troque com --substituir): ${r.pessoais.join(", ")}`);
    if (r.custos.length) console.log(`  usam API paga (cada prestador usa a própria chave):`); for (const c of r.custos) console.log(`   - ${c}`);
    for (const b of r.bloqueadas) console.log(`${ERR} bloqueada: ${b}`);
    for (const e of r.erros) console.log(`${ERR} ${e}`);
    for (const x of r.plugins.filter((x) => x.estado === "falhou")) console.log(`${ERR} plugin ${x.nome}: ${x.erro}`);
    const falhou = r.erros.length + r.bloqueadas.length + r.plugins.filter((x) => x.estado === "falhou").length;
    if (falhou) console.log(`${ERR} pacote incompleto: ${falhou} item(ns) não instalaram. Os playbooks que dependem deles param com aviso.`);
    process.exit(falhou ? 1 : 0);
  }
  console.log("uso: arkos skills [status|sync [--substituir]|remover]");
  process.exit(2);
}

// ---------- pasta-casa ----------
// `arkos setup`: escolhe (ou cria) a pasta da ARKOS. `arkos casa [caminho]`: mostra ou troca, com confirmação.
const casaLib = await casaLib0();
if (args[0] === "setup" || args[0] === "casa") await detectarSixel(); // logo certo nas perguntas
if (args[0] === "setup") { await casaLib.escolherCasa(); process.exit(0); }
if (args[0] === "casa") {
  const atual = casaLib.casaConfigurada();
  if (!args[1]) { console.log(`${marcaLib.etiqueta()} ` + (atual ? `⌂ ${atual}` : "casa não definida: rode arkos setup")); process.exit(0); }
  const { resolve: res } = await import("node:path");
  const nova = res(args.slice(1).join(" "));
  const ok = await casaLib.perguntar(`${marcaLib.etiqueta()} trocar a casa de ${atual || "(nenhuma)"} para ${nova}? (s/N) `);
  if (!/^s/i.test(ok)) { console.log(`${marcaLib.etiqueta()} nada mudou.`); process.exit(0); }
  casaLib.prepararCasa(nova); casaLib.salvarCasa(nova);
  console.log(`${marcaLib.etiqueta()} ⌂ casa: ${nova}`);
  process.exit(0);
}
// De qualquer pasta, a ARKOS abre na casa. --aqui (opcional) fica na pasta atual.
{
  const i = args.indexOf("--aqui");
  const aqui = i !== -1; if (aqui) args.splice(i, 1);
  const interativoCasa = process.stdin.isTTY && process.stdout.isTTY && !args.some((x) => ["-p", "--print", "-h", "--help", "-v", "--version"].includes(x));
  if (interativoCasa) await detectarSixel(); // logo certo já na pergunta da casa (uma consulta DA1 por execução)
  const casa = await casaLib.resolverCasa(interativoCasa);
  if (casa) { process.env.ARKOS_CASA = casa; if (!aqui) process.chdir(casa); }
}

// node-pty precisa do caminho do executável (não resolve PATHEXT sozinho)
function resolveClaude(cmd) {
  if (/[\\/]/.test(cmd)) return cmd;
  const exts = process.platform === "win32" ? (process.env.PATHEXT || ".EXE;.CMD").split(";") : [""];
  for (const dir of (process.env.PATH || "").split(delimiter)) {
    for (const e of exts) { const f = join(dir, cmd + e.toLowerCase()); if (existsSync(f)) return f; }
  }
  return cmd;
}

const node = JSON.stringify(process.execPath);
const script = (rel) => `${node} ${JSON.stringify(join(CLI_DIR, rel))}`;

export function buildSettings() {
  return {
    theme: "custom:arkos:arkos",
    statusLine: { type: "command", command: script("statusline.mjs"), padding: 0 },
    spinnerVerbs: {
      mode: "replace",
      // espaço na frente: a moldura troca "glifo + espaço" pelo mini Rotor de 2 colunas
      verbs: [" Orquestrando recursos", " Consultando base", " Montando relatório", " Roteando módulo",
        " Cruzando referências", " Calibrando playbook", " Executando passo", " Validando entrega"],
    },
    spinnerTipsEnabled: false,
    hooks: {
      SessionStart: [{ hooks: [{ type: "command", command: script("hooks/session.mjs"), timeout: 10 }] }],
      UserPromptSubmit: [{ hooks: [{ type: "command", command: script("hooks/prompt.mjs"), timeout: 10 }] }],
      PostToolUse: [{ matcher: "TodoWrite|TaskCreate|TaskUpdate", hooks: [{ type: "command", command: script("hooks/progress.mjs"), timeout: 10 }] }],
      PostToolUseFailure: [{ hooks: [{ type: "command", command: script("hooks/failure.mjs"), timeout: 10 }] }],
    },
  };
}

const runId = randomUUID();
const settingsPath = join(HOME_DIR, "arkos-settings.json");
writeJson(settingsPath, buildSettings());

const claudeArgs = [
  "--settings", settingsPath,
  "--plugin-dir", join(CLI_DIR, "plugin"),
  "--append-system-prompt-file", join(CLI_DIR, "prompt", "arkos.md"),
];
const { config } = await import("./lib/core.mjs");
const mcp = config().base?.mcpConfig;
if (mcp && existsSync(mcp)) claudeArgs.push("--mcp-config", mcp);
claudeArgs.push(...args);

const projeto = basename(process.cwd());
const title = `ARKOS · ${projeto}`;
const env = {
  ...process.env, ARKOS: "1", ARKOS_VERSION: VERSION, ARKOS_RUN_ID: runId, ARKOS_CLI_DIR: CLI_DIR,
  ARKOS_PROJETO: projeto, CLAUDE_CODE_DISABLE_TERMINAL_TITLE: "1",
  ARKOS_MOD: process.env.ARKOS_MOD ?? "1",
};
// estado da execução: a barra lê a base daqui
const guardarStatus = (s) => { const st = loadState(runId); st.baseStatus = s.base; st.projeto = projeto; saveState(runId, st); };
process.env.ARKOS_RUN_ID = runId; // loadState/saveState usam a chave da execução
env.ARKOS_ESTADO = sessionPath(runId);
const claudeCmd = process.env.ARKOS_CLAUDE || "claude";

// Topo fixo: claude em tela cheia dentro de um PTY, cabeçalho da ARKOS por cima.
// ARKOS_TOPO=0 volta ao modo simples (banner rola junto com a conversa).
// rodapé fixo da moldura: mesmo texto da statusLine, lido do estado da execução
async function carregarRodape() {
  const { render } = await import("./statusline.mjs");
  const { base, reportServer } = await import("./lib/core.mjs");
  // estado ao vivo (aguardando / executando…) só no rodapé; cols encaixa por prioridade
  return (animando = false, cols) => render({ session_id: runId }, loadState(runId), base(), reportServer(), true, { vivo: animando, cols });
}
const rodapeFixo = await carregarRodape();

// Só sessão interativa ganha a moldura: -p/--print, ajuda, versão e subcomandos do claude saem direto no terminal.
const SUBCOMANDOS = new Set(["mcp", "plugin", "plugins", "config", "doctor", "update", "install", "setup-token", "migrate-installer", "agents", "auth", "login", "logout"]);
const naoInterativo = args.some((a) => ["-p", "--print", "-h", "--help", "-v", "--version"].includes(a)) || SUBCOMANDOS.has(args[0]);
if (process.stdout.isTTY && process.stdin.isTTY && process.env.ARKOS_TOPO !== "0" && !naoInterativo) {
  let runInPty = null;
  try { ({ runInPty } = await import("./lib/pty-run.mjs")); await require_pty_ok(); }
  catch (e) {
    runInPty = null; // sem moldura: segue no modo simples e deixa o motivo registrado
    try { (await import("node:fs")).appendFileSync(join(HOME_DIR, "moldura-erro.log"), `${new Date().toISOString()} ${e.stack || e}
`); } catch {}
  }
  if (runInPty) {
    const sixel = await detectarSixel();
    // qualquer falha da moldura: devolve o terminal limpo e mostra o erro na tela (e no log), em vez de nada
    const falhou = (e) => {
      process.stdout.write("[?2026l[0m[r[?25h[?1049l");
      try { (require_fs()).appendFileSync(join(HOME_DIR, "moldura-erro.log"), `${new Date().toISOString()} ${e?.stack || e}
`); } catch {}
      process.stderr.write(`
${marcaLib.etiqueta("erro")} a moldura falhou: ${e?.message || e}
  Detalhes em ${join(HOME_DIR, "moldura-erro.log")}. Para abrir sem moldura: $env:ARKOS_TOPO="0"; arkos

`);
      process.exit(1);
    };
    process.on("uncaughtException", falhou);
    process.on("unhandledRejection", falhou);
    const { code, retomar } = await runInPty(resolveClaude(claudeCmd), claudeArgs, { ...env, CLAUDE_CODE_NO_FLICKER: "1", ARKOS_RODAPE_FIXO: "1" }, title,
      { checar: () => statusCompleto(), aoStatus: guardarStatus, rodape: rodapeFixo, sixel });
    process.stdout.write("\n" + bannerLines().join("\n") + "\n");
    if (retomar) process.stdout.write(`\n  \x1b[38;2;107;114;128mRetomar esta sessão:\x1b[0m arkos --resume ${retomar}\n`);
    process.stdout.write("\n");
    process.exit(code);
  }
}

// Rotor em Sixel (logo de verdade) quando o terminal anuncia no DA1; config miniRotor: "d" força o meio-bloco, "sixel" força a imagem.
async function detectarSixel() {
  const { diag } = await import("./lib/pty-run.mjs");
  diag(`arkos ${VERSION} em ${CLI_DIR} · TERM_PROGRAM=${process.env.TERM_PROGRAM || "-"} WT_SESSION=${process.env.WT_SESSION ? "sim" : "não"} · preferência miniRotor=${config0().miniRotor || process.env.ARKOS_MINIROTOR || "auto"}`);
  return (await marcaLib.detectarLogo({ diag })) === "sixel";
}

function require_fs() { return createRequire(import.meta.url)("node:fs"); }

function require_pty_ok() {
  // falha cedo se o binário nativo do node-pty não carregar (ex.: arquitetura sem prebuild)
  return import("node:module").then(({ createRequire }) => createRequire(import.meta.url)("@lydell/node-pty"));
}

// pacote de skills pré-instalado: faltou alguma? sincroniza em segundo plano (o status mostra "incompleto" até resolver)
if (process.env.ARKOS_SKILLS_AUTO !== "0") {
  try { const sk = await import("./lib/skills-pacote.mjs"); if (sk.faltando().length) sk.syncEmSegundoPlano(join(CLI_DIR, "arkos.mjs")); } catch {}
}
const st0 = await statusCompleto();
// versão nova publicada no GitHub + atualizacao.auto: atualiza em segundo plano (vale na próxima abertura)
if (st0.atualizacao && config0().atualizacao?.auto === true) {
  const { atualizarEmSegundoPlano } = await import("./lib/atualizar.mjs");
  if (atualizarEmSegundoPlano(join(CLI_DIR, "arkos.mjs"), HOME_DIR)) st0.atualizacao = { ...st0.atualizacao, texto: st0.atualizacao.texto.replace("· arkos update", "· atualizando em segundo plano") };
}
guardarStatus(st0);
// -p/subcomandos: saída limpa (sem banner nem título), para script e pipe
if (!naoInterativo && process.stdout.isTTY) process.stdout.write(`\x1b]0;${title}\x07` + "\n" + bannerLines(process.cwd(), st0).join("\n") + "\n\n");
const child = spawn(claudeCmd, claudeArgs, { stdio: "inherit", env, windowsHide: true });
process.on("SIGINT", () => {}); // Ctrl+C é do Claude
child.on("error", (e) => {
  console.error(`${marcaLib.etiqueta("erro")} não achei o comando "claude" (${e.code}). Instale o Claude Code e tente de novo.`);
  process.exit(127);
});
child.on("exit", (code, sig) => process.exit(code ?? (sig ? 1 : 0)));
