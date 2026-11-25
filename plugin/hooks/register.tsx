// Mod ARKOS: só carrega quando o usuário roda `arkos` (--plugin-dir). Lê o estado que os hooks de
// comando gravam (ARKOS_ESTADO) e desenha a marca onde o terminal deixa.
import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Estado } from '../types'

const VOLT = '#C6F432'
const VERMELHO = '#FF6B6B'
const estado = atom({ plugin: 'arkos', key: 'estado' } as const, { avisos: {}, falhas: {} } as Estado)

// particípios para o fechamento do turno ("✻ Orquestrado em 3s")
// marcador do logo: só com a moldura (ela troca pelo Rotor); fora dela, nenhum desenho de 1-2 células
let MARCA = ''
const FEITO = ['Orquestrado', 'Roteado', 'Calibrado', 'Executado', 'Validado', 'Cruzado', 'Montado', 'Consultado']

function duracao(ms: number): string {
  const s = Math.max(1, Math.round(ms / 1000))
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  return `${m}m ${s % 60}s`
}

let caminho: string | undefined
let passoAtual: { done: number; total: number; current: string } | null = null

const CAUSAS: [RegExp, string][] = [
  [/file (does not exist|not found)|no such file|ENOENT|cannot find the (file|path)/i, 'arquivo não encontrado'],
  [/string to replace not found|old_string/i, 'trecho para editar não encontrado'],
  [/has not been read|read it first|must read/i, 'arquivo não foi lido antes'],
  [/permission|EACCES|EPERM|denied|not allowed/i, 'sem permissão'],
  [/timed? ?out|ETIMEDOUT/i, 'tempo esgotado'],
  [/ECONNREFUSED|ENOTFOUND|network|fetch failed/i, 'rede'],
  [/missing required|invalid|validation|required|expected/i, 'parâmetro inválido'],
  [/not found/i, 'não encontrado'],
]

function avisoDeFalha(tool: string, texto: string, p: typeof passoAtual): string {
  const causa = CAUSAS.find(([re]) => re.test(texto))?.[1] || 'erro da ferramenta'
  const nome = tool.startsWith('mcp__') ? `MCP ${tool.split('__')[1]}` : tool
  if (p && p.total) {
    const n = Math.min(p.done + 1, p.total)
    return `${MARCA}ARKOS ▲ falha no passo ${n}/${p.total} · ${nome} · causa: ${causa} · corrigindo`
  }
  return `${MARCA}ARKOS ▲ falha em ${nome} · causa: ${causa} · corrigindo`
}

async function recarregar($: any) {
  try {
    caminho ??= await $.env.get('ARKOS_ESTADO')
    if (!caminho) return
    const bruto = JSON.parse(await $.fs.read(caminho))
    await update($, estado, () => ({ avisos: bruto.avisos || {}, falhas: bruto.falhas || {} }))
  } catch {
    // estado ainda não existe (antes do primeiro pedido): nada a desenhar
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    MARCA = (await $.env.get('ARKOS_RODAPE_FIXO')) === '1' ? '▚▞ ' : ''
    const r = await next(e)
    await recarregar($)
    return r
  })

  on('prompt.submit', async ($, e, next) => {
    const r = await next(e)
    await recarregar($)
    $.clock.after(1200, () => recarregar($))
    return r
  })

  // Toda ferramenta que volta com erro (Edit, Write, MCP, validação...) ganha a linha de falha.
  // O PostToolUseFailure do Claude Code só dispara para parte dos erros; o hook de comando cobre o Bash
  // com causa mais fina e tem precedência (mesmo tool_use_id).
  on('tool.call', async ($, e, next) => {
    const r: any = await next(e)
    caminho ??= await $.env.get('ARKOS_ESTADO')
    if (!r?.isError || !e.tool_use_id) return r
    await recarregar($)
    const id = e.tool_use_id
    const texto = String(r.text ?? r.result ?? '')
    const aviso = avisoDeFalha(String(e.tool), texto, passoAtual)
    await update($, estado, (v) => (v.falhas[id] ? v : { ...v, falhas: { ...v.falhas, [id]: aviso } }))
    // grava também no arquivo de estado, para sobreviver a recargas (o hook do Bash, se vier, tem precedência)
    $.clock.after(900, async () => {
      try {
        const bruto = JSON.parse(await $.fs.read(caminho!))
        if (!bruto.falhas?.[id]) {
          bruto.falhas = { ...(bruto.falhas || {}), [id]: aviso }
          await $.fs.write(caminho!, JSON.stringify(bruto, null, 2))
        }
      } catch {}
      await recarregar($)
    })
    return r
  })

  // item 3: aviso de módulo sob o pedido, em Volt, sem "UserPromptSubmit says:"
  on('ui.render', { component: 'UserMessage' }, async ($, e, next) => {
    const linha = await next(e)
    const { avisos } = await read($, estado)
    const aviso = avisos[String(e.props.text || '').trim().slice(0, 500)]
    if (!aviso) return linha
    const { Box, Text } = $.ui.resolve(e)
    return (
      <Box flexDirection="column">
        {linha}
        <Text color={VOLT}>{aviso}</Text>
      </Box>
    )
  })

  // item 5: falha de passo sob a ferramenta que falhou, em vermelho
  on('ui.render', { component: 'ToolUse' }, async ($, e, next) => {
    const linha = await next(e)
    const { falhas } = await read($, estado)
    if (!e.props.isErrored && !falhas[e.props.tool_use_id]) return linha
    const aviso = falhas[e.props.tool_use_id]
    if (!aviso) return linha
    const { Box, Text } = $.ui.resolve(e)
    return (
      <Box flexDirection="column">
        {linha}
        <Text color={VERMELHO}>{'  '}{aviso}</Text>
      </Box>
    )
  })

  // grupo recolhido ("Called mempalace · 1 failed"): a linha de falha vai embaixo do grupo
  on('ui.render', { component: 'ToolGroup' }, async ($, e, next) => {
    const linha = await next(e)
    if (e.props.isExpanded) return linha
    const { falhas } = await read($, estado)
    const avisos = e.props.calls.filter((c) => c.isErrored && c.tool_use_id && falhas[c.tool_use_id]).map((c) => falhas[c.tool_use_id!])
    if (!avisos.length) return linha
    const { Box, Text } = $.ui.resolve(e)
    return (
      <Box flexDirection="column">
        {linha}
        {avisos.map((a, i) => <Text key={String(i)} color={VERMELHO}>{'  '}{a}</Text>)}
      </Box>
    )
  })

  // fechamento do turno: "✻ Orquestrado em 3s" no lugar de "Sautéed for 3s"
  on('ui.render', { component: 'TurnDuration' }, async ($, e, next) => {
    const { Text } = $.ui.resolve(e)
    const palavra = FEITO[Math.abs(Math.floor(e.props.durationMs / 997)) % FEITO.length]
    return <Text color={VOLT}>{MARCA}{palavra} em {duracao(e.props.durationMs)}</Text>
  })
}
