// Pacote de skills da ARKOS: o mesmo conjunto, na mesma versão, em toda máquina da equipe.
// Manifesto: skills/pacote.json (curadoria da Harpa). Cada skill vem do repo da ARKOS (arkos-*)
// ou de um repo GitHub num commit fixo, passa pelo skill-scanner e vai com o LICENSE.
// O que foi instalado fica registrado em <ARKOS_HOME>/skills-pacote.json (para atualizar e remover).
import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { openSync, cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync, lstatSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { HOME_DIR as HOME0, planoLocal, config } from "./core.mjs";
const HOME = () => process.env.ARKOS_HOME || HOME0; // lido na hora (testes isolam o registro)

const CLI = join(dirname(fileURLToPath(import.meta.url)), "..");
export const MANIFESTO = join(CLI, "skills", "pacote.json");
const SCANNER = join(CLI, "skills", "_scanner", "scan_skill.py");
const LICENCAS_OK = /^(MIT|Apache-2\.0|BSD-[23]-Clause|ISC|0BSD|Unlicense|CC0-1\.0|ARKOS \(própria\))$/;

// onde o Claude Code lê as skills: CLAUDE_CONFIG_DIR/skills quando definido, senão ~/.claude/skills
export const pastaSkills = () => process.env.ARKOS_SKILLS_DIR || join(process.env.CLAUDE_CONFIG_DIR || join(homedir(), ".claude"), "skills");
const registroArq = () => join(HOME(), "skills-pacote.json");
const lerJson = (f, padrao) => { try { return JSON.parse(readFileSync(f, "utf8").replace(/^\uFEFF/, "")); } catch { return padrao; } };
export const carregarPacote = (arq = MANIFESTO) => lerJson(arq, null);
export const carregarRegistro = () => lerJson(registroArq(), { instaladas: {} });
const salvarRegistro = (r) => { mkdirSync(HOME(), { recursive: true }); writeFileSync(registroArq(), JSON.stringify(r, null, 2), "utf8"); };

// hash do conteúdo da pasta (detecta skill própria alterada entre versões)
function hashPasta(dir) {
  const h = createHash("sha1");
  const andar = (d) => { for (const n of readdirSync(d).sort()) { const f = join(d, n); if (statSync(f).isDirectory()) andar(f); else h.update(n).update(readFileSync(f)); } };
  andar(dir);
  return h.digest("hex").slice(0, 16);
}

// Ajustes da ARKOS sobre skill de terceiro (campo "ajustes" do manifesto, caminho relativo ao cli/):
// JSON [{ arquivo, de, para, porque, fonte }]. Troca exata de texto aplicada DEPOIS de copiar do commit fixo,
// então a cópia baixada nunca é editada à mão e o sync não apaga a correção. Se o "de" sumir (o autor mudou o
// texto no commit novo) e o "para" não estiver lá, a skill dá erro em vez de instalar sem o ajuste.
export function lerAjustes(s) {
  if (!s.ajustes) return null;
  const arq = join(CLI, s.ajustes);
  const lista = lerJson(arq, null);
  if (!Array.isArray(lista) || !lista.length) throw new Error(`ajustes ilegíveis: ${s.ajustes}`);
  for (const a of lista) if (!a.arquivo || !a.de || a.para == null || /(^|[\/])\.\.([\/]|$)/.test(a.arquivo)) throw new Error(`ajuste inválido em ${s.ajustes}`);
  return { lista, hash: createHash("sha1").update(readFileSync(arq)).digest("hex").slice(0, 8) };
}
export function aplicarAjustes(dir, lista) {
  for (const a of lista) {
    const f = join(dir, a.arquivo);
    const t = existsSync(f) ? readFileSync(f, "utf8") : null;
    if (t == null) throw new Error(`ajuste: ${a.arquivo} não existe`);
    if (t.includes(a.de)) writeFileSync(f, t.split(a.de).join(a.para), "utf8");
    else if (!t.includes(a.para)) throw new Error(`ajuste não aplica em ${a.arquivo}: o texto original mudou no commit; revise ${a.porque ? "(" + a.porque + ")" : ""}`);
  }
}

const tarExe = () => (process.platform === "win32" ? join(process.env.SystemRoot || "C:\\Windows", "System32", "tar.exe") : "tar");

// baixa o repo no commit fixo (uma vez por repo@commit) e devolve a pasta extraída
async function baixarRepo(repo, commit, log) {
  const cache = join(HOME(), "cache", "repos", `${repo.replace("/", "__")}@${commit.slice(0, 12)}`);
  if (existsSync(join(cache, ".ok"))) return cache;
  rmSync(cache, { recursive: true, force: true });
  mkdirSync(cache, { recursive: true });
  log(`  baixando ${repo}@${commit.slice(0, 7)}`);
  const r = await fetch(`https://codeload.github.com/${repo}/tar.gz/${commit}`);
  if (!r.ok) throw new Error(`download ${repo}@${commit.slice(0, 7)}: HTTP ${r.status}`);
  const tgz = join(cache, "_repo.tar.gz");
  writeFileSync(tgz, Buffer.from(await r.arrayBuffer()));
  const x = spawnSync(tarExe(), ["-xzf", tgz, "-C", cache, "--strip-components=1"], { windowsHide: true, encoding: "utf8" });
  rmSync(tgz, { force: true });
  if (x.status !== 0) throw new Error(`tar: ${(x.stderr || "").trim().slice(0, 120)}`);
  writeFileSync(join(cache, ".ok"), "");
  return cache;
}

// ---------- pacote VIP (instalação pública) ----------
// O repositório público não traz skill VIP. Com chave VIP, o sync baixa o pacote do servidor da base
// (GET <base>/pacote-vip com a licença no Bearer); a base confere assinatura, plano, revogação e suspensão.
// Licença editada à mão (plano trocado) tem assinatura inválida: a base devolve 403 e nada VIP entra.
export const pastaVip = () => join(HOME(), "pacote-vip");
const lerLicenca = () => { try { return readFileSync(join(HOME(), "licenca.txt"), "utf8").trim(); } catch { return ""; } };
const baseUrl = () => process.env.ARKOS_BASE_URL || config().base?.url || "";
const temVipNoManifesto = (pacote) => pacote.skills.some((s) => s.acesso !== "todos");
export const pacoteVipLocal = () => lerJson(join(pastaVip(), "pacote-vip.json"), null);

export async function baixarPacoteVip({ base = baseUrl(), licenca = lerLicenca(), log = console.log } = {}) {
  if (!base) return { erro: "chave VIP sem endereço da base (~/.arkos/config.json → base.url)" };
  if (!licenca) return { erro: "sem chave em ~/.arkos/licenca.txt" };
  let r;
  try { r = await fetch(new URL("/pacote-vip", base).href, { headers: { authorization: `Bearer ${licenca}` } }); }
  catch (e) { return { erro: `base fora do ar (${e.message})` }; }
  if (r.status === 403) return { erro: "a base recusou o pacote VIP (403): a chave não é VIP válida" };
  if (!r.ok) return { erro: `HTTP ${r.status}` };
  const dir = pastaVip(), novo = `${dir}.novo`;
  rmSync(novo, { recursive: true, force: true });
  mkdirSync(novo, { recursive: true });
  const tgz = join(novo, "_vip.tar.gz");
  writeFileSync(tgz, Buffer.from(await r.arrayBuffer()));
  const x = spawnSync(tarExe(), ["-xzf", tgz, "-C", novo], { windowsHide: true, encoding: "utf8" });
  rmSync(tgz, { force: true });
  if (x.status !== 0 || !existsSync(join(novo, "pacote-vip.json"))) { rmSync(novo, { recursive: true, force: true }); return { erro: "pacote VIP corrompido" }; }
  rmSync(dir, { recursive: true, force: true });
  cpSync(novo, dir, { recursive: true });
  rmSync(novo, { recursive: true, force: true });
  log("  pacote VIP baixado da base");
  return pacoteVipLocal();
}

// skill-scanner (getsentry/skills, Apache-2.0, junto no repo). Bloqueia achado crítico.
// aceitos: { "<categoria>": "por que foi revisado e aceito" } (campo scanner_aceito do manifesto)
export function escanear(dir, aceitos = {}) {
  const tentativas = [["uv", ["run", "--quiet", SCANNER, dir]], ["python", [SCANNER, dir]], ["py", ["-3", SCANNER, dir]]];
  for (const [cmd, args] of tentativas) {
    const r = spawnSync(cmd, args, { encoding: "utf8", windowsHide: true, env: { ...process.env, PYTHONIOENCODING: "utf-8" }, timeout: 120000 });
    if (r.error || r.status !== 0) continue;
    try {
      const j = JSON.parse(r.stdout);
      const crit = (j.findings || []).filter((f) => f.severity === "critical" && !aceitos[f.category]);
      return { ok: crit.length === 0, achados: j.findings?.length || 0, criticos: crit.map((f) => f.message || f.category || f.type).slice(0, 3) };
    } catch { continue; }
  }
  return { ok: false, erro: "skill-scanner não rodou (precisa de uv ou python com pyyaml)" };
}

// perguntar(nome) => Promise<boolean>: sobrescrever uma skill pessoal com o mesmo nome?
// so: lista de nomes (instala só essas, sem remover nada); plugins: instala os plugins nativos do manifesto
export async function sincronizar({ pacote = carregarPacote(), perguntar = async () => false, log = console.log, scanner = escanear, baixar = baixarRepo, so = null, plugins = instalarPlugins, plano = planoLocal(), vip = baixarPacoteVip } = {}) {
  if (!pacote) throw new Error(`manifesto não encontrado: ${MANIFESTO}`);
  const destino = pastaSkills();
  mkdirSync(destino, { recursive: true });
  const reg = carregarRegistro();
  const res = { instaladas: [], atualizadas: [], iguais: [], pessoais: [], bloqueadas: [], erros: [], custos: [], plugins: [] };
  let lista = pacote.skills, vipFalhou = false;
  if (plano === "vip" && !temVipNoManifesto(pacote) && vip) {
    const pv = await vip({ log });
    if (!pv || pv.erro) { vipFalhou = true; res.erros.push(`pacote VIP: ${pv?.erro || "não baixou"}`); }
    else { // versão VIP de uma skill pública (completa) substitui a pública
      const nomesVip = new Set((pv.skills || []).map((s) => s.nome));
      lista = [...lista.filter((s) => !nomesVip.has(s.nome)), ...(pv.skills || [])];
    }
  }
  for (const s of lista) {
    if (so && !so.includes(s.nome)) continue;
    // skill de área VIP (e-commerce, TikTok Shop, UGC, VSL, advertorial) não vai para chave membro
    if (s.acesso !== "todos" && plano !== "vip") { res.bloqueadas.push(`${s.nome} (plano VIP)`); continue; }
    try {
      if (!LICENCAS_OK.test(s.licenca || "")) { res.bloqueadas.push(`${s.nome} (licença ${s.licenca || "ausente"})`); continue; }
      let origem, versao, licencaArq = null;
      if (s.fonte.tipo === "repo") {
        origem = join(CLI, s.fonte.caminho);
        if (!existsSync(join(origem, "SKILL.md"))) throw new Error("SKILL.md ausente no repo da ARKOS");
        versao = hashPasta(origem);
      } else if (s.fonte.tipo === "vip") {
        origem = join(pastaVip(), s.fonte.caminho);
        if (/(^|[\/])\.\.([\/]|$)/.test(s.fonte.caminho) || !existsSync(join(origem, "SKILL.md"))) throw new Error("SKILL.md ausente no pacote VIP");
        versao = hashPasta(origem);
      } else if (s.fonte.tipo === "github") {
        if (!/^[0-9a-f]{40}$/.test(s.fonte.commit || "")) throw new Error("commit fixo ausente (40 hex)");
        const raiz = await baixar(s.fonte.repo, s.fonte.commit, log);
        origem = join(raiz, s.fonte.caminho);
        if (!existsSync(join(origem, "SKILL.md"))) throw new Error(`SKILL.md não está em ${s.fonte.caminho}`);
        licencaArq = readdirSync(raiz).find((n) => /^(LICEN[CS]E|COPYING)(\.|$)/i.test(n));
        if (!licencaArq && !readdirSync(origem).some((n) => /^LICEN[CS]E/i.test(n))) throw new Error("repo sem arquivo LICENSE");
        licencaArq = licencaArq && join(raiz, licencaArq);
        versao = s.fonte.commit;
      } else throw new Error(`fonte desconhecida: ${s.fonte.tipo}`);

      const ajustes = lerAjustes(s);
      if (ajustes) versao += `+aj-${ajustes.hash}`; // mudou o ajuste: reinstala
      const alvo = join(destino, s.nome);
      const nosso = reg.instaladas[s.nome];
      if (existsSync(alvo) && !nosso) {
        const link = lstatSync(alvo).isSymbolicLink();
        if (!(await perguntar(s.nome, link))) { res.pessoais.push(s.nome); continue; }
      }
      if (nosso && nosso.versao === versao && existsSync(join(alvo, "SKILL.md"))) { res.iguais.push(s.nome); continue; }

      const sc = scanner(origem, s.scanner_aceito || {});
      if (!sc.ok) { res.bloqueadas.push(`${s.nome} (${sc.erro || "scanner: " + sc.criticos.join("; ")})`); continue; }

      if (ajustes) { // ajusta numa pasta temporária: se falhar, a versão instalada antes continua lá
        const tmp = `${alvo}.ajuste-tmp`;
        rmSync(tmp, { recursive: true, force: true });
        cpSync(origem, tmp, { recursive: true });
        try { aplicarAjustes(tmp, ajustes.lista); } catch (e) { rmSync(tmp, { recursive: true, force: true }); throw e; }
        rmSync(alvo, { recursive: true, force: true });
        cpSync(tmp, alvo, { recursive: true });
        rmSync(tmp, { recursive: true, force: true });
      } else {
        rmSync(alvo, { recursive: true, force: true });
        cpSync(origem, alvo, { recursive: true });
      }
      if (licencaArq && !readdirSync(alvo).some((n) => /^LICEN[CS]E/i.test(n))) cpSync(licencaArq, join(alvo, "LICENSE"));
      (nosso ? res.atualizadas : res.instaladas).push(s.nome);
      reg.instaladas[s.nome] = { versao, fonte: s.fonte.tipo === "github" ? `${s.fonte.repo}@${s.fonte.commit.slice(0, 7)}` : s.fonte.tipo === "vip" ? "arkos-vip" : "arkos", licenca: s.licenca, em: new Date().toISOString(), ...(ajustes ? { ajustes: s.ajustes } : {}) };
      if (s.custo) res.custos.push(`${s.nome}: ${s.custo}`);
    } catch (e) { res.erros.push(`${s.nome}: ${e.message}`); }
  }
  if (!so) {
    // saiu do pacote: remove só o que nós instalamos (com o download VIP falho, não remove nada: falha de rede não rebaixa)
    const nomes = new Set(lista.map((s) => s.nome));
    if (plano !== "vip") rmSync(pastaVip(), { recursive: true, force: true }); // virou membro: o pacote VIP sai da máquina
    for (const n of Object.keys(reg.instaladas)) if (!nomes.has(n) && !vipFalhou) { rmSync(join(destino, n), { recursive: true, force: true }); delete reg.instaladas[n]; }
    reg.versao = pacote.versao;
    if (pacote.plugins?.length && plugins) res.plugins = plugins(pacote.plugins, log);
  }
  salvarRegistro(reg);
  return res;
}

// plugins nativos (classe NATIVA): [{ nome, id: "plugin@marketplace", marketplace?: "dono/repo" }] via `claude plugin install`
export function instalarPlugins(lista, log = console.log) {
  const claude = (a) => spawnSync("claude", a, { encoding: "utf8", windowsHide: true, shell: process.platform === "win32", timeout: 180000 });
  let tem = [];
  try { tem = JSON.parse(claude(["plugin", "list", "--json"]).stdout || "[]").map((p) => p.id); } catch {}
  const out = [];
  for (const p of lista) {
    if (tem.includes(p.id)) { out.push({ nome: p.nome, estado: "ok" }); continue; }
    if (p.marketplace) claude(["plugin", "marketplace", "add", p.marketplace]);
    const r = claude(["plugin", "install", p.id]);
    out.push({ nome: p.nome, estado: r.status === 0 ? "instalado" : "falhou", erro: r.status === 0 ? undefined : (r.stderr || r.stdout || "").trim().slice(0, 120) });
    log(`  plugin ${p.id}: ${r.status === 0 ? "instalado" : "falhou"}`);
  }
  return out;
}

// skills do pacote que faltam na máquina (nomes); com `nomes`, só entre essas
// skills que a chave pode ter: membro não conta as de acesso vip
export const doPlano = (pacote, plano = planoLocal()) => {
  const extra = plano === "vip" && !temVipNoManifesto(pacote) ? pacoteVipLocal()?.skills || [] : [];
  const nv = new Set(extra.map((s) => s.nome));
  return [...pacote.skills.filter((s) => !nv.has(s.nome)), ...extra].filter((s) => plano === "vip" || s.acesso === "todos");
};

export function faltando(nomes = null, pacote = carregarPacote(), plano = planoLocal()) {
  if (!pacote) return [];
  const doPacote = new Set(doPlano(pacote, plano).map((s) => s.nome));
  const alvo = nomes ? nomes.filter((n) => doPacote.has(n)) : [...doPacote];
  return alvo.filter((n) => !existsSync(join(pastaSkills(), n, "SKILL.md")));
}

// sync em segundo plano, sem janela, um por vez (trava de 15 min)
export function syncEmSegundoPlano(cliArq) {
  const trava = join(HOME(), "skills-sync.lock");
  try { if (Date.now() - statSync(trava).mtimeMs < 15 * 60000) return false; } catch {}
  mkdirSync(HOME(), { recursive: true });
  writeFileSync(trava, String(Date.now()));
  const log = join(HOME(), "skills-sync.log");
  const c = spawn(process.execPath, [cliArq, "skills", "sync", "--trava", trava], { detached: true, windowsHide: true, stdio: ["ignore", openSync(log, "w"), openSync(log, "a")] });
  c.unref();
  return true;
}

// desfaz: apaga só as pastas que o pacote instalou (skills pessoais ficam)
export function remover() {
  const reg = carregarRegistro();
  const nomes = Object.keys(reg.instaladas);
  for (const n of nomes) rmSync(join(pastaSkills(), n), { recursive: true, force: true });
  rmSync(registroArq(), { force: true });
  return nomes;
}

// "pacote ARKOS v0.1.0: 61/63 skills" — conta as do pacote presentes (nossas ou pessoais com o mesmo nome)
export function statusPacote(pacote = carregarPacote(), plano = planoLocal()) {
  if (!pacote) return null;
  const lista = doPlano(pacote, plano);
  const total = lista.length;
  const presentes = lista.filter((s) => existsSync(join(pastaSkills(), s.nome, "SKILL.md"))).length;
  let sincronizando = false;
  try { sincronizando = Date.now() - statSync(join(HOME(), "skills-sync.lock")).mtimeMs < 15 * 60000; } catch {}
  return { versao: pacote.versao, total, presentes, nossas: Object.keys(carregarRegistro().instaladas).length, sincronizando };
}
