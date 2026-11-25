// Hook PostToolUseFailure: falha no padrão ARKOS (item 5). O erro bruto do Claude fica logo acima.
import { loadState, saveState } from "../lib/core.mjs";
import { readStdin, emit } from "./io.mjs";
// marcador do logo: só com a moldura ativa (ela troca "▚▞" pelo Rotor); fora dela, só "ARKOS", sem desenho
const MARCA_TXT = process.env.ARKOS_RODAPE_FIXO === "1" ? "▚▞ " : "";

const CAUSES = [
  [/cannot find module|module not found|no module named|failed to resolve import|cannot resolve/i, "import quebrado"],
  [/command not found|is not recognized as|nao e reconhecido|não é reconhecido|enoent/i, "comando ou arquivo inexistente"],
  [/permission denied|eacces|eperm|acesso negado|access is denied/i, "sem permissão"],
  [/syntaxerror|unexpected token|parse error/i, "erro de sintaxe"],
  [/type ?error|ts\d{4}|is not assignable|type '.*' is not/i, "erro de tipo"],
  [/eaddrinuse|address already in use/i, "porta ocupada"],
  [/timed? ?out|timeout|etimedout/i, "tempo esgotado"],
  [/econnrefused|network|fetch failed|enotfound|getaddrinfo/i, "rede ou serviço fora do ar"],
  [/\d+ (failing|failed)|tests? failed|assertion/i, "teste falhando"],
  [/no such file|file not found|does not exist|nao existe|não existe/i, "arquivo não encontrado"],
  [/old_string|not found in file|string to replace/i, "trecho para editar não encontrado"],
  [/denied|rejected|user doesn't want|blocked/i, "bloqueado por permissão ou hook"],
  [/missing required|required parameter|invalid (argument|param)|validation/i, "parâmetro inválido"],
];

const input = await readStdin();
if (input.is_interrupt) process.exit(0);
const sid = input.session_id;
const st = loadState(sid);
const err = String(input.error ?? input.tool_response?.error ?? input.tool_response ?? "");
const cause = (CAUSES.find(([re]) => re.test(err)) || [null, "erro da ferramenta"])[1];

const bruto = input.tool_name || "ferramenta";
// mcp__servidor__ferramenta -> "MCP servidor"
const tool = bruto.startsWith("mcp__") ? `MCP ${bruto.split("__")[1]}` : bruto;
const ti = input.tool_input || {};
const what = st.current || (tool === "Bash" ? `Bash ${String(ti.description || ti.command || "").slice(0, 40)}` : tool);

const passo = st.total ? `falha no passo ${Math.min((st.done || 0) + 1, st.total)}/${st.total}` : `falha em ${tool}`;

const aviso = st.total ? `${MARCA_TXT}ARKOS ▲ ${passo} · ${what} · causa: ${cause} · corrigindo` : `${MARCA_TXT}ARKOS ▲ ${passo} · causa: ${cause} · corrigindo`;
st.lastFailure = { at: new Date().toISOString(), tool, cause, aviso, id: input.tool_use_id || null };
st.falhas = { ...(st.falhas || {}) };
if (input.tool_use_id) st.falhas[input.tool_use_id] = aviso;
saveState(sid, st);
// com o mod ARKOS ativo (ARKOS_MOD=1) a linha é desenhada sob a ferramenta, sem o prefixo "says:"
if (process.env.ARKOS_MOD !== "1") emit({ systemMessage: aviso });
