// Pasta-casa da ARKOS: de qualquer pasta, o `arkos` abre o Claude nela.
// <casa>\arkos.engine (config e estado interno), docs, tools e workspace (entregas: workspace\<cliente>\<projeto>\).
import { existsSync, mkdirSync, writeFileSync, readdirSync, statSync, cpSync } from "node:fs";
import { join, resolve } from "node:path";
import { homedir } from "node:os";
import { createInterface } from "node:readline";
import { HOME_DIR, config, writeJson } from "./core.mjs";
import { etiqueta, blocoComLogo, VOLT, MUDO, BRANCO, NEGRITO } from "./marca.mjs";

export const CASA_PADRAO = join(homedir(), "ARKOS");
export const MOTOR = "arkos.engine";

const READMES = {
  [MOTOR]: "# arkos.engine\n\nConfig e estado interno da ARKOS: `execucoes/` (aviso.json, entradas.json, rota.json, estado.json, saida.json de cada playbook), `perfil.json` (perfil do negócio) e `logs/`.\nNão guarde entregas aqui: elas vão para `../workspace/`.\n",
  docs: "# docs\n\nDocumentação de apoio do prestador: manuais, briefings recebidos, materiais de referência que valem para vários clientes.\n",
  tools: "# tools\n\nFerramentas e scripts próprios do prestador (utilitários, modelos, binários) usados pela ARKOS ou à mão.\n",
  workspace: "# workspace\n\nPasta PRINCIPAL. Toda entrega fica aqui dentro, organizada por cliente e projeto:\n\n    workspace\\<cliente>\\<projeto>\\\n\nEx.: `workspace\\clinica-lumiere\\lancamento-2026-11\\`. Os playbooks da ARKOS gravam os artefatos aqui.\n",
};

export const casaConfigurada = () => config().casa || null;

export function salvarCasa(dir) {
  const f = join(HOME_DIR, "config.json");
  writeJson(f, { ...config(), casa: resolve(dir) });
}

// Cria a estrutura sem sobrescrever nada. Migra o .arkos\ antigo da casa para arkos.engine\ (só o que falta).
export function prepararCasa(casa) {
  const criadas = [];
  mkdirSync(casa, { recursive: true });
  for (const [pasta, txt] of Object.entries(READMES)) {
    const d = join(casa, pasta);
    if (!existsSync(d)) { mkdirSync(d, { recursive: true }); criadas.push(pasta); }
    const r = join(d, "README.md");
    if (!existsSync(r)) writeFileSync(r, txt, "utf8");
  }
  for (const sub of ["execucoes", "logs"]) mkdirSync(join(casa, MOTOR, sub), { recursive: true });
  const antigo = join(casa, ".arkos");
  if (existsSync(antigo) && statSync(antigo).isDirectory()) {
    for (const nome of readdirSync(antigo)) {
      const dst = join(casa, MOTOR, nome);
      try { cpSync(join(antigo, nome), dst, { recursive: true, force: false, errorOnExist: false }); } catch {}
    }
  }
  return criadas;
}

// raiz da ARKOS para execuções e perfil: a casa (se existir), senão a pasta dada
export function raizArkos(cwd = process.cwd()) {
  const c = process.env.ARKOS_CASA || casaConfigurada();
  return c && existsSync(c) ? c : cwd;
}

export function perguntar(texto) {
  return new Promise((ok) => {
    const rl = createInterface({ input: process.stdin, output: process.stdout });
    let feito = false;
    rl.question(texto, (r) => { feito = true; ok(r.trim()); rl.close(); });
    rl.on("close", () => { if (!feito) ok(""); });
  });
}

const V = VOLT, M = MUDO, Z = "\x1b[0m";

// tela de boas-vindas da pergunta da casa: logo bem desenhado, ARKOS ENGINE, a explicação e a pergunta
export function boasVindas(padrao) {
  return "\n" + blocoComLogo(6, ["", `${NEGRITO}${BRANCO}A R K O S   E N G I N E${Z}`, `${M}Advanced Resource & Knowledge Orchestration System${Z}`, "",
    `${BRANCO}Pasta-casa:${Z} ${M}de qualquer pasta a ARKOS abre aqui, e as entregas ficam em${Z}`, `${M}${join("workspace", "<cliente>", "<projeto>")} dentro dela.${Z}`]) + "\n";
}

// pergunta onde fica a casa (existente ou nova) e grava no config
export async function escolherCasa(padrao = casaConfigurada() || CASA_PADRAO) {
  process.stdout.write(boasVindas(padrao));
  for (;;) {
    const r = await perguntar(`${etiqueta()} onde fica a pasta da ARKOS? ${M}(Enter = ${padrao})${Z} `);
    const dir = resolve((r || padrao).replace(/^["']|["']$/g, "").replace(/^~(?=$|[\\/])/, homedir()));
    if (!existsSync(dir)) {
      const c = await perguntar(`  ${dir} não existe. Criar? ${M}(S/n)${Z} `);
      if (/^n/i.test(c)) continue;
    }
    prepararCasa(dir);
    salvarCasa(dir);
    console.log(`${etiqueta()} ${V}⌂${Z} casa: ${dir}`);
    return dir;
  }
}

// Resolve a casa antes de abrir: pergunta na primeira vez; casa apagada = avisa e pergunta (recriar ou outra).
// interativo=false (pipe, -p): não pergunta; sem casa válida devolve null (fica na pasta atual).
export async function resolverCasa(interativo) {
  const c = casaConfigurada();
  if (c && existsSync(c)) { prepararCasa(c); return c; }
  if (!interativo) return null;
  if (!c) return escolherCasa(CASA_PADRAO);
  console.log(`${etiqueta("erro")} a pasta-casa ${c} não existe mais.`);
  const r = await perguntar(`  ${M}[R]${Z} recriar nesse lugar · ${M}[O]${Z} escolher outra pasta ${M}(R/o)${Z} `);
  if (/^o/i.test(r)) return escolherCasa(CASA_PADRAO);
  prepararCasa(c);
  console.log(`${etiqueta()} ${V}⌂${Z} casa recriada: ${c}`);
  return c;
}
